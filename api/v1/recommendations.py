from fastapi import APIRouter, HTTPException, Depends
from langchain_core.messages import HumanMessage
import asyncio
import json
from sqlalchemy.orm import Session
from typing import List

from database import get_db, PatientHistory
from schemas import PatientInput, RecommendationOutput
from services import get_vectorstore, get_llm

router = APIRouter()

@router.post("/recommend", response_model=RecommendationOutput)
async def get_recommendations(patient: PatientInput, db: Session = Depends(get_db)):
    vectorstore = get_vectorstore()
    llm = get_llm()
    
    # 1. Similarity Search (Pencarian dokumen relevan)
    query_str = f"Gejala pasien: {', '.join(patient.symptoms)}. Usia: {patient.age}. Jenis Kelamin: {patient.gender}."
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
    relevant_docs = retriever.invoke(query_str)
    
    # Kumpulkan daftar referensi dokumen untuk dikembalikan ke Frontend
    sources_list = []
    seen_sources = set()
    context_chunks = []
    
    for doc in relevant_docs:
        doc_name = doc.metadata.get("document_name", "Dokumen Tidak Diketahui")
        doc_url = doc.metadata.get("document_url", "")
        
        if doc_name not in seen_sources:
            sources_list.append({
                "document_name": doc_name, 
                "document_url": doc_url if doc_url else None
            })
            seen_sources.add(doc_name)
            
        context_chunks.append(f"[Sumber: {doc_name}]\n{doc.page_content}")
    
    context = "\n\n".join(context_chunks)
    context_text = f"Panduan Medis Referensi:\n{context}\n\n" if context else ""
    
    prompt = (
        f"Anda adalah asisten triase rumah sakit. Berdasarkan informasi pasien dan panduan medis berikut, "
        f"berikan rekomendasi poliklinik spesialis, kemungkinan penyakit, dan langkah penanganan awal.\n\n"
        f"{context_text}"
        f"Data Pasien:\n"
        f"- Jenis Kelamin: {patient.gender}\n"
        f"- Usia: {patient.age}\n"
        f"- Gejala: {', '.join(patient.symptoms)}\n\n"
        f"ATURAN PENTING: Jawab HANYA dalam format JSON berikut dalam Bahasa Indonesia, tanpa teks tambahan apapun di luar JSON:\n"
        f"{{\n"
        f'  "department": ["Poli Syaraf", "Poli Jantung"],  // max 3 poli\n'
        f'  "initial_handling": ["Istirahat cukup", "Cek tekanan darah"], // max 3 langkah penanganan\n'
        f'  "possibility_of_illness": ["Hipertensi", "Vertigo"] // max 3 kemungkinan penyakit\n'
        f"}}"
    )

    try:
        response = await asyncio.wait_for(
            llm.ainvoke([HumanMessage(content=prompt)]),
            timeout=300
        )
        content_data = response.content
        if isinstance(content_data, list):
            text = "".join(
                c.get("text", "") if isinstance(c, dict) else str(c)
                for c in content_data
            )
        else:
            text = str(content_data)
        text = text.strip()
        
        start = text.find("{")
        end = text.rfind("}") + 1
        if start == -1 or end == 0:
             raise ValueError("LLM tidak mengembalikan format JSON yang valid.")
             
        json_str = text[start:end]
        data = json.loads(json_str)
        
        recommended_dept = data.get("department", [])
        illness = data.get("possibility_of_illness", [])
        handling = data.get("initial_handling", [])
        
        # Simpan ke riwayat pasien di database
        history_entry = PatientHistory(
            gender=patient.gender,
            age=patient.age,
            symptoms=", ".join(patient.symptoms),
            recommended_department=json.dumps(recommended_dept),
            possibility_of_illness=json.dumps(illness),
            initial_handling=json.dumps(handling)
        )
        db.add(history_entry)
        db.commit()
        
        return {
            "recommended_department": recommended_dept,
            "possibility_of_illness": illness,
            "initial_handling": handling,
            "sources": sources_list
        }

    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Request ke LLM timeout")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Gagal mem-parsing output JSON dari LLM")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


