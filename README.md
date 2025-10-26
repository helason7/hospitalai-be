# 🏥 DiagnoX (Hospital Assistant) API

Aplikasi back-end yg dibuat dengan fastAPI + LLM Gemini, Groq, dan OpenAI. 
Digunakan untuk memberikan rekomendasi departement kesehatan, kemungkinan penyakit, dan penanganan awal yg terkait dengan data gender, umur, dan gejala pasien.

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

### rename file .env.example menjadi .env
- buat goole api-key di link ini: https://aistudio.google.com/api-keys
- tambahkan ke dalam variable GOOGLE_API_KEY yg ada di file .env seperti ini:
```
GOOGLE_API_KEY=contoh-apikey
```
- lakukan hal yg sama untuk variable GROQ_API_KEY dan OPENAI_API_KEY
- Groq: https://console.groq.com/keys
- OpenAI: https://platform.openai.com/api-keys

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
  "llm": "grok", // dapat diganti dengan "gemini" atau "openai"
  "gender": "female",
  "age": 62,
  "symptoms": ["pusing", "mual", "sulit berjalan"]
}
```

```
{
    "recommended_department": [
        "Neurologi",
        "Kardiologi",
        "Geriatri"
    ],
    "possibility_of_illness": [
        "Migrain vestibular",
        "Stroke atau penyakit serebrovaskular",
        "Gangguan neurologis (misalnya penyakit Parkinson, sklerosis multipel)"
    ],
    "initial_handling": [
        "Periksa tanda vital (tekanan darah, denyut jantung, gula darah) untuk menyingkirkan kondisi yang mengancam jiwa secara langsung.",
        "Lakukan pemeriksaan neurologis untuk menilai keseimbangan, koordinasi, dan fungsi kognitif.",
        "Pertimbangkan studi pencitraan (misalnya MRI, CT scan) untuk mengevaluasi kemungkinan stroke atau kelainan struktural lainnya."
    ]
}
```

apps link: https://diagnox-dist.vercel.app/