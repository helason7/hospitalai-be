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
    
    # Kumpulkan daftar referensi dokumen dan simpan metadata-nya
    sources_dict = {}
    context_chunks = []
    
    for doc in relevant_docs:
        doc_name = doc.metadata.get("document_name", "Dokumen Tidak Diketahui")
        doc_url = doc.metadata.get("document_url", "")
        
        if doc_name not in sources_dict:
            sources_dict[doc_name] = doc_url if doc_url else None
            
        context_chunks.append(f"[Dokumen: {doc_name}]\n{doc.page_content}")
    
    context = "\n\n".join(context_chunks)
    context_text = f"Dokumen Panduan Klinis Tersedia:\n---\n{context}\n---\n\n" if context else ""
    
    prompt = (
        f"Anda adalah asisten triase rumah sakit berbasis Strict RAG.\n"
        f"Berdasarkan informasi pasien dan dokumen panduan klinis berikut, "
        f"berikan rekomendasi poliklinik spesialis, kemungkinan penyakit, dan langkah penanganan awal.\n\n"
        f"{context_text}"
        f"Data Pasien:\n"
        f"- Jenis Kelamin: {patient.gender}\n"
        f"- Usia: {patient.age}\n"
        f"- Gejala: {', '.join(patient.symptoms)}\n\n"
        f"ATURAN STRICT RAG SANGAT KETAT:\n"
        f"1. Evaluasi secara kritis apakah isi dokumen panduan klinis di atas BENAR-BENAR relevan dan secara langsung membahas kondisi/gejala/penyakit yang dialami pasien.\n"
        f"2. Jika dokumen TIDAK relevan (contoh: gejala pasien berkaitan dengan psikologis/kejiwaan, luka luar/trauma, atau penyakit lain yang TIDAK dibahas secara spesifik dalam dokumen panduan klinis di atas), "
        f"maka field 'used_sources' WAJIB bernilai list kosong []. JANGAN PERNAH menyertakan atau merekomendasikan dokumen yang tidak sesuai!\n"
        f"3. Hanya jika dokumen tersebut memang relevan dan menjadi dasar rujukan diagnosis/tindakan, cantumkan nama dokumen persis seperti di header [Dokumen: ...] ke dalam list 'used_sources'.\n"
        f"4. Anda tetap wajib memberikan rekomendasi poliklinik, kemungkinan penyakit, dan penanganan awal berdasarkan pengetahuan medis umum Anda meskipun dokumen referensi tidak tersedia.\n\n"
        f"Jawab HANYA dalam format JSON berikut dalam Bahasa Indonesia, tanpa teks tambahan apapun di luar JSON:\n"
        f"{{\n"
        f'  "department": ["Poli Jiwa", "Poli Penyakit Dalam"],  // max 3 poli\n'
        f'  "initial_handling": ["Konseling awal", "Latihan pernapasan"], // max 3 langkah penanganan\n'
        f'  "possibility_of_illness": ["Gangguan Kecemasan"], // max 3 kemungkinan penyakit\n'
        f'  "used_sources": ["Nama Dokumen Relevan"] // WAJIB kosong [] jika gejala/penyakit tidak memiliki dokumen referensi yang cocok\n'
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
        used_sources = data.get("used_sources", [])
        
        # Strict RAG Filter: Hanya sertakan dokumen yang dikonfirmasi relevan oleh LLM
        final_sources = []
        if isinstance(used_sources, list) and used_sources:
            for doc_name, doc_url in sources_dict.items():
                doc_name_lower = doc_name.strip().lower()
                for used in used_sources:
                    used_lower = str(used).strip().lower()
                    if used_lower and (used_lower == doc_name_lower or used_lower in doc_name_lower or doc_name_lower in used_lower):
                        final_sources.append({
                            "document_name": doc_name,
                            "document_url": doc_url
                        })
                        break
        
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
            "sources": final_sources
        }

    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Request ke LLM timeout")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Gagal mem-parsing output JSON dari LLM")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


