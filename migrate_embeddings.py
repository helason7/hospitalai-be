import os
import shutil
import time
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKUP_DIR = os.path.join(BASE_DIR, "chroma_db_backup")
TARGET_DIR = os.path.join(BASE_DIR, "chroma_db")

print("1. Loading all items from backup ChromaDB...")
backup_vs = Chroma(persist_directory=BACKUP_DIR)
backup_col = backup_vs._collection
total_count = backup_col.count()
print(f"Total items to migrate: {total_count}")

all_ids = []
all_docs = []
all_metas = []

limit = 2000
offset = 0
while offset < total_count:
    data = backup_col.get(limit=limit, offset=offset, include=["documents", "metadatas"])
    if not data["ids"]:
        break
    all_ids.extend(data["ids"])
    all_docs.extend(data["documents"])
    all_metas.extend(data["metadatas"])
    offset += len(data["ids"])
    print(f"Fetched {len(all_ids)}/{total_count} items...")

print("2. Initializing new multilingual embedding model...")
model_name = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
embeddings = HuggingFaceEmbeddings(model_name=model_name)

print("3. Resetting target directory...")
if os.path.exists(TARGET_DIR):
    shutil.rmtree(TARGET_DIR)

new_vs = Chroma(persist_directory=TARGET_DIR, embedding_function=embeddings)

print("4. Re-embedding and inserting items into new ChromaDB...")
batch_size = 200
start_time = time.time()

for i in range(0, len(all_docs), batch_size):
    batch_docs = all_docs[i : i + batch_size]
    batch_metas = all_metas[i : i + batch_size]
    batch_ids = all_ids[i : i + batch_size]
    
    clean_metas = []
    for meta in batch_metas:
        clean_meta = {}
        for k, v in meta.items():
            if v is not None:
                clean_meta[k] = v
            else:
                clean_meta[k] = ""
        clean_metas.append(clean_meta)
        
    new_vs.add_texts(texts=batch_docs, metadatas=clean_metas, ids=batch_ids)
    processed = min(i + batch_size, len(all_docs))
    elapsed = time.time() - start_time
    rate = processed / elapsed if elapsed > 0 else 0
    remaining = (len(all_docs) - processed) / rate if rate > 0 else 0
    print(f"[{processed}/{len(all_docs)}] ({processed/len(all_docs)*100:.1f}%) - Rate: {rate:.1f} docs/s - ETA: ~{remaining:.0f}s")

print("Migration completed successfully!")
