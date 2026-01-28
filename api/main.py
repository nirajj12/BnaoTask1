import os
import time
from datetime import datetime, timezone
import uuid
from typing import List, Optional, Dict

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    Form,
    HTTPException,
    BackgroundTasks,
    Request,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from utils.document_ops import IngestionFile
from src.DocumentChat.ingestion import DocumentIngestor
from src.DocumentChat.retrieval import RetrievalEngine
from models.models import IndexResponse, QueryResponse
from logger.custom_logger import CustomLogger

import os
import logging

# -------------------- LOG NOISE REDUCTION --------------------

# HuggingFace / Transformers
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)

# HuggingFace Hub HTTP calls
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)

# Torch noise
logging.getLogger("torch").setLevel(logging.ERROR)

# Optional: FAISS internal logs (if any)
logging.getLogger("faiss").setLevel(logging.ERROR)


# -------------------- CONFIG --------------------

FAISS_BASE = os.getenv("FAISS_BASE", "faiss_index")
UPLOAD_BASE = os.getenv("UPLOAD_BASE", "data")

log = CustomLogger().get_logger(__name__)

# -------------------- RATE LIMITER --------------------

limiter = Limiter(key_func=get_remote_address)

# -------------------- APP INIT --------------------

app = FastAPI(
    title="RAG-Based Multi-Document Chat API",
    version="1.0",
)

app.state.limiter = limiter

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------- STATIC + TEMPLATES --------------------

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# -------------------- RATE LIMIT HANDLER --------------------

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Please try again later."},
    )

# -------------------- UI --------------------

@app.get("/", response_class=HTMLResponse)
async def serve_ui(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# -------------------- HEALTH --------------------

@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "service": "rag-multi-doc-chat"}

# -------------------- BACKGROUND INGESTION --------------------

def run_ingestion(
    files: List[IngestionFile],
    session_id: Optional[str],
):
    """
    Runs in background thread.
    Files are already memory-safe (bytes copied).
    """
    ingestor = DocumentIngestor(
        temp_dir=UPLOAD_BASE,
        faiss_dir=FAISS_BASE,
        session_id=session_id,
    )
    ingestor.ingest_files(files)

# -------------------- BUILD INDEX --------------------

@app.post("/chat/index", response_model=IndexResponse)
async def build_index(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    session_id: Optional[str] = Form(None),
):
    try:
        if not files:
            raise HTTPException(
                status_code=400,
                detail="No files provided for ingestion",
            )

        # Convert UploadFile  memory-safe IngestionFile
        prepared_files: List[IngestionFile] = []
        for f in files:
            data = await f.read()  # IMPORTANT: read before background task
            prepared_files.append(
                IngestionFile(
                    name=f.filename,
                    data=data,
                )
            )

        # Ensure we always have a concrete session_id
        if not session_id:
            session_id = f"session_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"

        background_tasks.add_task(
            run_ingestion,
            prepared_files,
            session_id,
        )

        log.info(
            "ingestion_started",
            session_id=session_id,
            file_count=len(prepared_files),
        )

        return IndexResponse(
            message="Document ingestion started in background",
            session_id=session_id,
            total_chunks=0,
        )

    except HTTPException:
        raise
    except Exception as e:
        log.error("indexing_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# -------------------- QUERY (POST ONLY) --------------------

@app.post("/chat/query", response_model=QueryResponse)
@limiter.limit("5/minute")
async def query_rag(
    request: Request,
    question: str = Form(...),
    session_id: str = Form(...),
    top_k: int = Form(5),
):
    try:
        index_dir = os.path.join(FAISS_BASE, session_id)

        if not os.path.isdir(index_dir):
            raise HTTPException(
                status_code=404,
                detail=f"No FAISS index found for session_id={session_id}",
            )

        rag = RetrievalEngine(
            session_id=session_id,
            faiss_dir=index_dir,
        )

        start = time.time()
        answer = rag.answer(question, top_k=top_k)
        latency_ms = round((time.time() - start) * 1000, 2)

        log.info(
            "query_processed",
            session_id=session_id,
            latency_ms=latency_ms,
            top_k=top_k,
        )

        return QueryResponse(
            question=question,
            answer=answer,
            session_id=session_id,
            top_k=top_k,
        )

    except HTTPException:
        raise
    except Exception as e:
        log.error("query_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# -------------------- GET GUARD (IMPORTANT FIX) --------------------

@app.get("/chat/query")
def query_guard():
    """
    Prevents confusion when opening /chat/query in browser.
    """
    return {
        "message": "This endpoint only supports POST requests via the UI."
    }
