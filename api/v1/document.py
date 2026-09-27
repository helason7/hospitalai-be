from fastapi import APIRouter, HTTPException, File, UploadFile, Form, Depends
from typing import List, Optional
from sqlalchemy.orm import Session
import tempfile
import shutil
import os
from datetime import datetime

from database import get_db, DocumentMetadata
from schemas import DocumentOutput, DocumentUpdate
from services import get_vectorstore
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

router = APIRouter()

@router.post("/upload-document")
async def upload_document(
    file: UploadFile = File(...),
    name: str = Form(...),
    url: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Upload dokumen pedoman medis (PDF) untuk disimpan ke Vector Database (ChromaDB),
    dan simpan metadata (nama, url) ke SQLite. File PDF tidak disimpan di server.
    """
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Hanya mendukung file PDF")
    
    temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    try:
        # Simpan file sementara
        with temp_pdf as f:
            shutil.copyfileobj(file.file, f)
        
        # 1. Document Loader
        loader = PyPDFLoader(temp_pdf.name)
        documents = loader.load()
        
        # Tambahkan metadata nama dokumen dan url agar tersimpan permanen di vektor
        for doc in documents:
            doc.metadata["document_name"] = name
            doc.metadata["document_url"] = url if url else ""
            # PyPDFLoader sudah otomatis mengisi doc.metadata["page"] (dimulai dari indeks 0)
        
        # 2. Text Splitter (Membagi teks jadi potongan kecil)
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, 
            chunk_overlap=200,
            separators=["\n\n", "\n", " ", ""]
        )
        chunks = text_splitter.split_documents(documents)
        
        # 3 & 4. Embedding Model & Vector Database (ChromaDB)
        vectorstore = get_vectorstore()
        vectorstore.add_documents(chunks)
        
        # 5. Simpan metadata ke SQLite
        new_doc = DocumentMetadata(name=name, url=url)
        db.add(new_doc)
        db.commit()
        db.refresh(new_doc)
        
        return {
            "message": f"Berhasil memproses dokumen.",
            "document_id": new_doc.id,
            "chunks_added": len(chunks)
        }
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error saat memproses dokumen: {str(e)}")
    finally:
        # Hapus file temporary agar tidak memakan storage
        if os.path.exists(temp_pdf.name):
            os.remove(temp_pdf.name)

@router.put("/documents/{doc_id}")
def update_document(doc_id: int, doc_update: DocumentUpdate, db: Session = Depends(get_db)):
    """
    Mengedit metadata dokumen di SQLite dan juga di Vector DB (ChromaDB)
    """
    doc = db.query(DocumentMetadata).filter(DocumentMetadata.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Dokumen tidak ditemukan")
        
    old_name = doc.name
    new_name = doc_update.name
    new_url = doc_update.url if doc_update.url else ""
    
    # 1. Update SQLite
    doc.name = new_name
    doc.url = new_url
    doc.updated_at = datetime.utcnow()
    db.commit()
    
    # 2. Update Vector DB (ChromaDB)
    try:
        vectorstore = get_vectorstore()
        collection = vectorstore._collection
        
        # Cari semua teks yang memiliki nama dokumen lama
        results = collection.get(where={"document_name": old_name})
        
        if results and results["ids"]:
            ids = results["ids"]
            metadatas = results["metadatas"]
            
            # Ubah metadatanya
            for meta in metadatas:
                meta["document_name"] = new_name
                meta["document_url"] = new_url
                
            # Simpan kembali
            collection.update(ids=ids, metadatas=metadatas)
    except Exception as e:
        print(f"Gagal update ChromaDB: {e}")
        
    return {"message": "Data berhasil diperbarui"}

@router.delete("/documents/{doc_id}")
def delete_document(doc_id: int, db: Session = Depends(get_db)):
    """
    Menghapus dokumen dari SQLite dan menghapus vektornya dari ChromaDB
    """
    doc = db.query(DocumentMetadata).filter(DocumentMetadata.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Dokumen tidak ditemukan")
        
    doc_name = doc.name
    
    # 1. Hapus dari ChromaDB
    try:
        vectorstore = get_vectorstore()
        collection = vectorstore._collection
        collection.delete(where={"document_name": doc_name})
    except Exception as e:
        print(f"Gagal menghapus ChromaDB (mungkin sudah kosong): {e}")
        
    # 2. Hapus dari SQLite
    db.delete(doc)
    db.commit()
    
    return {"message": "Dokumen berhasil dihapus"}

@router.get("/documents", response_model=List[DocumentOutput])
def get_documents(db: Session = Depends(get_db)):
    """
    Mengambil daftar dokumen pedoman medis yang telah menjadi acuan sistem.
    """
    documents = db.query(DocumentMetadata).order_by(DocumentMetadata.created_at.desc()).all()
    return documents
