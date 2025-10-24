# 🏥 Hospital Department Recommender API

A minimal FastAPI service that recommends the most relevant specialist department based on patient information using a mock LLM.

## 🚀 How to Run

### Recommend (Optional)
Buat environment baru
```bash
conda create -n nama-environment python=versi-python
```
lalu aktifkan environment tersebut
```bash
conda activate nama-environment
```
gunakan python 3.10 (reccomend)

### Tambahkan file .env ke dalam folder

### 1️⃣ Install dependencies
```bash
pip install -r requirements.txt
```

### 2️⃣ Run the FastAPI app
```bash
uvicorn app:app --reload
```

### 3️⃣ Test with POST request
buka URL berikut dengan postman atau tools untuk test API lain 
POST http://127.0.0.1:8000/recommend

```
request body: {
  "llm": "gemini",
  "gender": "female",
  "age": 62,
  "symptoms": ["pusing", "mual", "sulit berjalan"]
}
```
response: {
  "recommended_department": "Neurology"
}