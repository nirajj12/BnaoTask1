import sys
from pathlib import Path
from typing import List

import faiss
import numpy as np

from utils.model_loader import ModelLoader
from logger.custom_logger import CustomLogger
from exception.custom_exception import DocumentPortalException
from prompt.prompt_library import PROMPT_REGISTRY



class RetrievalEngine:
    """
    Pure FAISS-based retrieval + manual prompt RAG.
    """

    def __init__(self, session_id: str, faiss_dir: str):
        try:
            self.log = CustomLogger().get_logger(__name__)
            self.session_id = session_id
            self.faiss_dir = Path(faiss_dir)

            if not self.faiss_dir.exists():
                raise FileNotFoundError(f"FAISS directory not found: {faiss_dir}")

            self.model_loader = ModelLoader()
            self.embedding_model = self.model_loader.load_embeddings()
            self.llm = self.model_loader.load_llm()

            self._load_faiss()
            self.prompt_template = PROMPT_REGISTRY["context_qa"]

            self.log.info(
                "retrieval_engine_initialized",
                session_id=self.session_id,
                faiss_path=str(self.faiss_dir),
            )

        except Exception as e:
            raise DocumentPortalException(
                "Failed to initialize RetrievalEngine", e
            ) from e

    # -------------------- LOAD INDEX --------------------

    def _load_faiss(self):
        try:
            index_path = self.faiss_dir / "index.faiss"
            chunks_path = self.faiss_dir / "chunks.txt"

            if not index_path.exists() or not chunks_path.exists():
                raise FileNotFoundError("FAISS index or chunks file missing")

            self.index = faiss.read_index(str(index_path))
            self.chunks = chunks_path.read_text(encoding="utf-8").split("\n\n---\n\n")

            self.log.info(
                "faiss_index_loaded",
                total_chunks=len(self.chunks),
                session_id=self.session_id,
            )

        except Exception as e:
            raise DocumentPortalException(
                "Failed to load FAISS index", e
            ) from e

    # -------------------- RETRIEVAL --------------------

    def _retrieve(self, query: str, top_k: int = 5) -> List[str]:
        try:
            query_embedding = self.embedding_model.embed_query(query)
            query_vector = np.array([query_embedding]).astype("float32")

            distances, indices = self.index.search(query_vector, top_k)

            retrieved_chunks = []
            for rank, idx in enumerate(indices[0]):
                if idx < len(self.chunks):
                    retrieved_chunks.append(self.chunks[idx])
                    self.log.info(
                        "retrieval_hit",
                        rank=rank + 1,
                        similarity_distance=float(distances[0][rank]),
                        session_id=self.session_id,
                    )

            if not retrieved_chunks:
                self.log.warning(
                    "no_relevant_chunks_found",
                    session_id=self.session_id,
                )

            return retrieved_chunks

        except Exception as e:
            raise DocumentPortalException(
                "Error during FAISS retrieval", e
            ) from e

    # -------------------- GENERATION --------------------

    def answer(self, question: str, top_k: int = 5) -> str:
        try:
            retrieved_chunks = self._retrieve(question, top_k=top_k)

            context = "\n\n".join(retrieved_chunks)

            prompt = self.prompt_template.format(
                context=context,
                question=question,
            )

            self.log.info(
                "prompt_constructed",
                context_length=len(context),
                question_preview=question[:100],
                session_id=self.session_id,
            )

            response = self.llm.invoke(prompt)

            answer_text = getattr(response, "content", str(response))

            if not answer_text.strip():
                self.log.warning(
                    "empty_llm_response",
                    session_id=self.session_id,
                )
                return "No answer could be generated from the provided documents."

            self.log.info(
                "answer_generated",
                answer_preview=answer_text[:150],
                session_id=self.session_id,
            )

            return answer_text

        except Exception as e:
            raise DocumentPortalException(
                "Failed to generate answer", e
            ) from e
