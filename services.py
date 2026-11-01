import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

from pathlib import Path

# Load .env (prioritas) atau file env jika tanpa titik
BASE_DIR = Path(__file__).resolve().parent
if (BASE_DIR / ".env").exists():
    load_dotenv(BASE_DIR / ".env")
elif (BASE_DIR / "env").exists():
    load_dotenv(BASE_DIR / "env")
else:
    load_dotenv()

CHROMA_DB_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")

def get_vectorstore():
    # Menggunakan model embedding multilingual yang mendukung Bahasa Indonesia
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    vectorstore = Chroma(persist_directory=CHROMA_DB_DIR, embedding_function=embeddings)
    return vectorstore

def get_llm():
    """Menggunakan Google Gemini API sebagai satu-satunya model."""
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "API key tidak ditemukan. Pastikan file .env ada dan berisi GOOGLE_API_KEY=... "
            "atau set environment variable GOOGLE_API_KEY."
        )
    return ChatGoogleGenerativeAI(
        model="gemini-3.5-flash-lite",
        api_key=api_key,
        temperature=0.2, # Temperature rendah agar jawaban konsisten dan tidak halusinasi
        timeout=100
    )
