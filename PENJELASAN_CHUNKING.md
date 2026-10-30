# 📄 Panduan Konsep & Mekanisme Chunking Dokumen pada HospitalAI

Dokumen ini menjelaskan secara mendalam mengenai konsep **Chunking Dokumen** dan **Chunk Overlap** yang diimplementasikan pada backend sistem triase medis **HospitalAI (DiagnoX)**.

---

## 1. Tujuan Dokumen di-Chunking

Dalam sistem *Retrieval-Augmented Generation* (RAG), dokumen panduan medis berformat PDF (seperti Panduan Praktik Klinis / SOP Rumah Sakit) tidak dimasukkan utuh ke database vektor atau LLM, melainkan dipecah menjadi potongan-potongan teks (*chunks*).

Tujuan utamanya adalah:

1. **Menyesuaikan Batasan Model Embedding (*Context Window*)**
   * Model embedding yang digunakan proyek ini adalah [`all-MiniLM-L6-v2`](file:///run/media/helas/WD BLUE/Project/skripsi/hospitalai-be/services.py#L22) (via HuggingFace Sentence Transformers), yang memiliki batas input maksimal token (biasanya 256–512 token).
   * PDF pedoman medis yang tebalnya puluhan hingga ratusan halaman tidak mungkin diproses sekaligus menjadi satu vektor tanpa mengalami *truncation* (terpotong paksa).

2. **Mempertahankan Presisi Semantik (*Semantic Granularity*)**
   * Jika satu buku tebal dipadatkan menjadi hanya satu nilai vektor, representasi maknanya akan kabur (*diluted*). Vektor rata-rata dari seluruh isi buku tidak akan akurat mencocokkan keluhan spesifik pasien seperti `"nyeri dada kiri dan sesak"`.
   * Melalui pemotongan teks (*chunking*), tiap sub-topik atau bab (misal: penanganan darurat infark miokard) memiliki representasi vektor yang tajam dan spesifik.

3. **Efisiensi Token dan Pengurangan Gangguan (*Noise*) pada LLM**
   * Saat inferensi di [`api/v1/recommendations.py`](file:///run/media/helas/WD BLUE/Project/skripsi/hospitalai-be/api/v1/recommendations.py#L21), sistem hanya perlu mengambil $k=3$ chunk paling relevan untuk diberikan ke Google Gemini (`gemini-3.5-flash-lite`).
   * Ini menghemat token API, mempercepat respon (*low latency*), serta meminimalkan fenomena *Lost-in-the-Middle* (model bingung karena teks terlalu panjang).

4. **Keterlacakan Sumber Rujukan (*Traceability & Citation*)**
   * Setiap potongan dokumen tetap menyimpan metadata asal, termasuk nomor halaman (`page`), nama dokumen (`document_name`), dan URL dokumen (`document_url`), sehingga rekomendasi medis dapat diverifikasi sumber aslinya.

---

## 2. Mekanisme Chunking pada Proyek Ini

Implementasi chunking berada pada file [`api/v1/document.py`](file:///run/media/helas/WD BLUE/Project/skripsi/hospitalai-be/api/v1/document.py) dalam endpoint `POST /api/v1/upload-document`:

### A. Ekstraksi Dokumen & Metadata
```python
# 1. Document Loader
loader = PyPDFLoader(temp_pdf.name)
documents = loader.load()

# Menambahkan metadata ke setiap halaman
for doc in documents:
    doc.metadata["document_name"] = name
    doc.metadata["document_url"] = url if url else ""
    # doc.metadata["page"] otomatis terisi oleh PyPDFLoader
```

### B. Konfigurasi Pemotongan Teks (*RecursiveCharacterTextSplitter*)
```python
# 2. Text Splitter
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000, 
    chunk_overlap=200,
    separators=["\n\n", "\n", " ", ""]
)
chunks = text_splitter.split_documents(documents)
```

**Penjelasan Parameter:**
* **`chunk_size=1000`**: Panjang maksimal setiap potongan adalah 1.000 karakter (~150–200 kata), ukuran ideal untuk memuat 1–2 paragraf klinis berisi deskripsi gejala dan instruksi penanganan.
* **`chunk_overlap=200`**: Tumpang tindih sebesar 200 karakter antara chunk yang berurutan.
* **`separators=["\n\n", "\n", " ", ""]`**: Pemisahan bertingkat secara cerdas. Splitter akan mencari batas pemisah paling alami terlebih dahulu:
  1. Paragraf baru (`\n\n`)
  2. Baris baru (`\n`)
  3. Spasi kata (` `)
  4. Karakter demi karakter (`""`, opsi terakhir jika kata terlalu panjang)

### C. Penyimpanan ke Database Vektor
Setiap chunk yang mewarisi metadata halaman dikonversi menjadi vektor dan disimpan di ChromaDB:
```python
# 3. Vector Store
vectorstore = get_vectorstore()
vectorstore.add_documents(chunks)
```

---

## 3. Konsep dan Fungsi Chunk Overlap

### Apa itu Chunk Overlap?
**Chunk Overlap** adalah mekanisme duplikasi sebagian teks di bagian akhir potongan sebelumnya ke bagian awal potongan berikutnya. Tujuannya adalah berfungsi sebagai **"jembatan konteks"** agar informasi tidak terbelah di tengah kalimat atau penjelasan penting.

### Ilustrasi Alur Overlap
```text
Teks Dokumen Asli:
[ Kalimat A ] ------- [ Kalimat B ] ------- [ Kalimat C ] ------- [ Kalimat D ]

Hasil Pemotongan DENGAN OVERLAP:
Chunk 1: [ Kalimat A ] ------- [ Kalimat B ]
                                     |
                       (Tumpang Tindih / Overlap)
                                     |
Chunk 2:                      [ Kalimat B ] ------- [ Kalimat C ]
                                                          |
                                            (Tumpang Tindih / Overlap)
                                                          |
Chunk 3:                                           [ Kalimat C ] ------- [ Kalimat D ]
```

---

### Perbandingan Kasus Nyata (Dunia Medis)

Misalkan di dalam SOP klinis rumah sakit tertulis kalimat:
> *"Pasien dengan nyeri dada mendadak berisiko terkena serangan jantung. **Namun, jika nyeri dada disertai batuk berdahak dan demam tinggi, kemungkinan besar merupakan infeksi paru-paru (pneumonia)** dan harus dirujuk ke Poli Paru."*

#### ❌ Skenario 1: TANPA Overlap (`chunk_overlap = 0`)
Teks terpotong kaku pas di batas karakter:
* **Chunk 1**:
  > *"Pasien dengan nyeri dada mendadak berisiko terkena serangan jantung. Namun, jika nyeri dada disertai"*
* **Chunk 2**:
  > *"batuk berdahak dan demam tinggi, kemungkinan besar merupakan infeksi paru-paru (pneumonia) dan harus dirujuk ke Poli Paru."*

**Dampak Risiko Klinis:**
* Jika pasien mengeluhkan `"nyeri dada"`, sistem mengambil **Chunk 1**. LLM hanya membaca risiko serangan jantung tanpa mengetahui kondisi diferensial batuk/demam.
* Jika sistem mengambil **Chunk 2**, kalimat terpenggal diawali *"batuk berdahak..."* tanpa tahu konteks awalnya terkait diferensiasi dari *"nyeri dada"*.

#### ✅ Skenario 2: DENGAN Overlap (`chunk_overlap = 200`)
Sebanyak 200 karakter terakhir dari Chunk 1 diikutsertakan kembali di awal Chunk 2:
* **Chunk 1**:
  > *"... Pasien dengan nyeri dada mendadak berisiko terkena serangan jantung. **Namun, jika nyeri dada disertai batuk berdahak dan demam tinggi, kemungkinan besar merupakan infeksi paru-paru** ..."*
* **Chunk 2**:
  > *"... **Namun, jika nyeri dada disertai batuk berdahak dan demam tinggi, kemungkinan besar merupakan infeksi paru-paru** (pneumonia) dan harus dirujuk ke Poli Paru. Tindakan awal meliputi pemberian terapi oksigen dan rontgen thorax ..."*

**Keuntungan:**
Konteks klinis tetap utuh pada chunk manapun yang terpilih oleh sistem ChromaDB, sehingga AI tidak salah menarik kesimpulan diagnosis atau rekomendasi poliklinik.

---

## 4. Ringkasan Parameter Proyek

| Komponen | Nilai / Implementasi | Lokasi Kode | Fungsi |
| :--- | :--- | :--- | :--- |
| **Loader** | `PyPDFLoader` | [`api/v1/document.py`](file:///run/media/helas/WD BLUE/Project/skripsi/hospitalai-be/api/v1/document.py#L38) | Ekstrak teks PDF per lembar halaman beserta nomor halaman |
| **Text Splitter** | `RecursiveCharacterTextSplitter` | [`api/v1/document.py`](file:///run/media/helas/WD BLUE/Project/skripsi/hospitalai-be/api/v1/document.py#L48) | Algoritma pemecah teks rekursif |
| **Chunk Size** | `1000` karakter | [`api/v1/document.py`](file:///run/media/helas/WD BLUE/Project/skripsi/hospitalai-be/api/v1/document.py#L49) | Batas maksimal panjang per potongan teks |
| **Chunk Overlap** | `200` karakter | [`api/v1/document.py`](file:///run/media/helas/WD BLUE/Project/skripsi/hospitalai-be/api/v1/document.py#L50) | Jembatan redundansi teks antar potongan agar konteks tidak putus |
| **Embedding** | `all-MiniLM-L6-v2` | [`services.py`](file:///run/media/helas/WD BLUE/Project/skripsi/hospitalai-be/services.py#L22) | Mengubah teks chunk menjadi representasi vektor numerik |
| **Vector Store** | ChromaDB (`k=3`) | [`api/v1/recommendations.py`](file:///run/media/helas/WD BLUE/Project/skripsi/hospitalai-be/api/v1/recommendations.py#L21) | Mencari 3 chunk terdekat yang relevan dengan keluhan pasien |
