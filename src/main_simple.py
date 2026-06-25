"""Simple backend server for testing frontend connection."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime
import random

app = FastAPI()

# Simulate job progress storage
job_progress = {}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/api/upload/")
async def upload_document():
    try:
        job_id = f"job-{random.randint(1000, 9999)}"
        job_progress[job_id] = {
            "status": "Checking",
            "progress": 0,
            "document_id": random.randint(1, 100),
            "filename": "test.pdf"
        }
        return JSONResponse({
            "job_id": job_id,
            "document_id": job_progress[job_id]["document_id"],
            "filename": job_progress[job_id]["filename"],
            "status": "Checking",
            "message": "Document uploaded successfully. Processing will begin shortly."
        })
    except Exception as e:
        return JSONResponse({
            "error": "Upload failed",
            "detail": str(e)
        }, status_code=500)

@app.get("/api/upload/status/{job_id}")
async def get_upload_status(job_id: str):
    if job_id not in job_progress:
        # Initialize new job
        job_progress[job_id] = {
            "status": "Checking",
            "progress": 0,
            "document_id": 1,
            "filename": "test.pdf"
        }
    
    job = job_progress[job_id]
    
    # Simulate progress
    if job["progress"] < 100:
        # Increment by 10% each poll for smooth progress
        job["progress"] = min(job["progress"] + 10, 100)
        if job["progress"] >= 100:
            job["progress"] = 100
            job["status"] = "Approved"  # Always approve for testing
        elif job["progress"] >= 50:
            job["status"] = "Processing"
        else:
            job["status"] = "Checking"
    
    return JSONResponse({
        "job_id": job_id,
        "document_id": job["document_id"],
        "status": job["status"],
        "progress": job["progress"],
        "message": None,
        "rejection_note": None,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    })

@app.post("/api/search")
async def search_documents():
    return JSONResponse({
        "query": "test",
        "results": [],
        "total": 0
    })

@app.post("/api/ask")
async def ask_question():
    return JSONResponse({
        "answer": "This is a test answer.",
        "confidence": "High",
        "citations": [],
        "query": "test",
        "context_chunks_used": 0
    })

@app.get("/api/documents")
async def get_documents():
    return JSONResponse({
        "documents": [],
        "total": 0,
        "page": 1,
        "page_size": 20
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)