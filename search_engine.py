import re

# 1. Database Sederhana (Dokumen dari gambar proyekmu)
documents = {
    "doc1": "Introduction to P&ID diagrams and electrical engineering workflows.",
    "doc2": "How to build a free search engine web application using Python.",
    "doc3": "Quality Control Plans (QC Plan) and FMEA analysis in project management."
}

# 2. Fungsi Mesin Pencari
def cari_kata(kata_kunci):
    kata_kunci = kata_kunci.lower()
    hasil = []
    for doc_id, isi_teks in documents.items():
        if re.search(kata_kunci, isi_teks.lower()):
            hasil.append(doc_id)
    return hasil

# 3. Uji Coba Pencarian
print("Hasil pencarian untuk 'QC Plan':", cari_kata("QC Plan"))
print("Hasil pencarian untuk 'Python':", cari_kata("Python"))
