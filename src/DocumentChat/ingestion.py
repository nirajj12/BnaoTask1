import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import List

import faiss
from pypdf import PdfReader
from docx import Document as DocxDocument
import numpy as np
from logger.custom_logger import CustomLogger
from exception.custom_exception import DocumentPortalException
from utils.model_loader import ModelLoader


class DocumentIngestor:
    SUPPORTED_FILE_TYPES = {".pdf", ".docx", ".txt", ".md"}

    def __init__(
        self,
        temp_dir: str = "data/document_chat",
        faiss_dir: str = "faiss_index",
        session_id: str | None = None,
    ):
        try:
            self.log = CustomLogger().get_logger(__name__)

            self.temp_dir = Path(temp_dir)
            self.temp_dir.mkdir(parents=True, exist_ok=True)

            self.faiss_dir = Path(faiss_dir)
            self.faiss_dir.mkdir(parents=True, exist_ok=True)

            self.session_id = (
                session_id
                if session_id
                else f"session_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
            )

            self.session_temp_dir = self.temp_dir / self.session_id
            self.session_temp_dir.mkdir(parents=True, exist_ok=True)

            self.session_faiss_dir = self.faiss_dir / self.session_id
            self.session_faiss_dir.mkdir(parents=True, exist_ok=True)

            self.model_loader = ModelLoader()
            self.embedding_model = self.model_loader.load_embeddings()
            self.config = self.model_loader.config

            self.log.info(
                "document_ingestor_initialized",
                session_id=self.session_id,
                temp_path=str(self.session_temp_dir),
                faiss_path=str(self.session_faiss_dir),
            )

        except Exception as e:
            raise DocumentPortalException(
                "Failed to initialize DocumentIngestor", e
            ) from e

    # -------------------- FILE LOADING --------------------

    def _read_file(self, file_path: Path) -> str:
        try:
            ext = file_path.suffix.lower()

            if ext == ".pdf":
                reader = PdfReader(str(file_path))
                return "\n".join(page.extract_text() or "" for page in reader.pages)

            elif ext == ".docx":
                doc = DocxDocument(str(file_path))
                return "\n".join(p.text for p in doc.paragraphs)

            elif ext in {".txt", ".md"}:
                return file_path.read_text(encoding="utf-8", errors="ignore")

            else:
                raise ValueError(f"Unsupported file type: {ext}")

        except Exception as e:
            raise DocumentPortalException(
                f"Failed to read file {file_path.name}", e
            ) from e

    # -------------------- CHUNKING --------------------

    def _chunk_text(self, text: str) -> List[str]:
        cfg = self.config["chunking"]
        chunk_size = cfg["chunk_size"]
        chunk_overlap = cfg["chunk_overlap"]

        chunks = []
        start = 0
        length = len(text)

        while start < length:
            end = start + chunk_size
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            start = end - chunk_overlap

        return chunks

    # -------------------- INGESTION --------------------

    def ingest_files(self, uploaded_files):
        """
        uploaded_files MUST be adapter objects with:
        - .name
        - .getbuffer()
        """
        try:
            if not uploaded_files:
                raise ValueError("No files provided for ingestion")

            # 🔐 fail-fast safety
            if not hasattr(uploaded_files[0], "getbuffer"):
                raise RuntimeError("Ingestor received non-adapted file object")

            all_chunks: List[str] = []

            for uploaded_file in uploaded_files:
                ext = Path(uploaded_file.name).suffix.lower()

                if ext not in self.SUPPORTED_FILE_TYPES:
                    self.log.warning(
                        "unsupported_file_type",
                        file_name=uploaded_file.name,
                        session_id=self.session_id,
                    )
                    continue

                temp_name = f"{uuid.uuid4().hex[:8]}{ext}"
                temp_path = self.session_temp_dir / temp_name

                # ✅ Adapter-only file write
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                self.log.info(
                    "file_saved",
                    original_name=uploaded_file.name,
                    saved_as=str(temp_path),
                    session_id=self.session_id,
                )

                raw_text = self._read_file(temp_path)
                chunks = self._chunk_text(raw_text)
                all_chunks.extend(chunks)

            if not all_chunks:
                raise ValueError("No valid content extracted from documents")

            self.log.info(
                "documents_chunked",
                total_chunks=len(all_chunks),
                session_id=self.session_id,
            )

            return self._build_faiss_index(all_chunks)

        except Exception as e:
            self.log.error(
                "file_ingestion_failed",
                error=str(e),
                session_id=self.session_id,
            )
            raise DocumentPortalException(
                "Error during document ingestion", e
            ) from e

    # -------------------- FAISS --------------------

    def _build_faiss_index(self, chunks: List[str]):
        try:
            embeddings = self.embedding_model.embed_documents(chunks)

            if not embeddings:
                raise ValueError("No embeddings generated")

            vectors = np.array(embeddings, dtype="float32")
            dimension = vectors.shape[1]

            index = faiss.IndexFlatL2(dimension)
            index.add(vectors)

            faiss.write_index(
                index,
                str(self.session_faiss_dir / "index.faiss"),
            )

            (self.session_faiss_dir / "chunks.txt").write_text(
                "\n\n---\n\n".join(chunks),
                encoding="utf-8",
            )

            self.log.info(
                "faiss_index_created",
                session_id=self.session_id,
                total_vectors=len(chunks),
                dimension=dimension,
            )

            return {
                "session_id": self.session_id,
                "faiss_path": str(self.session_faiss_dir),
                "total_chunks": len(chunks),
            }

        except Exception as e:
            self.log.error(
                "faiss_index_creation_failed",
                error=str(e),
                session_id=self.session_id,
            )
            raise DocumentPortalException(
                "Failed to build FAISS index", e
            ) from e
