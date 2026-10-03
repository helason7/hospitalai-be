import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

load_dotenv()

CHROMA_DB_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")

def get_vectorstore():
    # Menggunakan model embedding lokal yang gratis dan tanpa limit
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    vectorstore = Chroma(persist_directory=CHROMA_DB_DIR, embedding_function=embeddings)
    return vectorstore

def get_llm():
    """Menggunakan Google Gemini API sebagai satu-satunya model."""
    return ChatGoogleGenerativeAI(
        model="gemini-3.8-flash",
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        temperature=0.2, # Temperature rendah agar jawaban konsisten dan tidak halusinasi
        timeout=100
    )
