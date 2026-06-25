"""Verify ingested documents in SQLite database."""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "engineering_docs.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Count documents
cursor.execute('SELECT COUNT(*) FROM reference_documents')
total = cursor.fetchone()[0]
print(f"Total documents in database: {total}")
print()

# List all documents
cursor.execute('SELECT id, document_number, title, discipline, page_count, status FROM reference_documents ORDER BY id')
print("Document Details:")
print("-" * 100)
print(f"{'ID':<5} {'Doc Number':<25} {'Title':<40} {'Disc':<5} {'Pages':<6} {'Status'}")
print("-" * 100)

for row in cursor.fetchall():
    doc_id, doc_num, title, disc, pages, status = row
    doc_num = doc_num or "N/A"
    title = (title or "N/A")[:38]
    pages = pages or 0
    print(f"{doc_id:<5} {doc_num:<25} {title:<40} {disc:<5} {pages:<6} {status}")

print("-" * 100)
print()

# Count related records
cursor.execute('SELECT COUNT(*) FROM revision_history')
rev_count = cursor.fetchone()[0]

cursor.execute('SELECT COUNT(*) FROM comments_response')
comm_count = cursor.fetchone()[0]

cursor.execute('SELECT COUNT(*) FROM equipment_ratings')
equip_count = cursor.fetchone()[0]

cursor.execute('SELECT COUNT(*) FROM drawing_index')
draw_count = cursor.fetchone()[0]

cursor.execute('SELECT COUNT(*) FROM low_confidence_regions')
low_conf_count = cursor.fetchone()[0]

print("Related Records:")
print(f"  Revision history entries: {rev_count}")
print(f"  Comment/response entries: {comm_count}")
print(f"  Equipment ratings: {equip_count}")
print(f"  Drawing index entries: {draw_count}")
print(f"  Low confidence regions: {low_conf_count}")

conn.close()