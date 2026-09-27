from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routers dari modul api/v1
from api.v1 import document, recommendations, history, survey

app = FastAPI(title="Hospital Department Recommender with RAG (Modular)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Daftarkan Router
# Menambahkan prefix /api/v1 agar endpoint menjadi /api/v1/upload-document, dll
app.include_router(document.router, prefix="/api/v1", tags=["Documents"])
app.include_router(recommendations.router, prefix="/api/v1", tags=["Recommendations"])
app.include_router(history.router, prefix="/api/v1", tags=["History"])
app.include_router(survey.router, prefix="/api/v1", tags=["Survey"])
