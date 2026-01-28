from pydantic import BaseModel, Field
from typing import List, Optional


class IndexRequest(BaseModel):
    """
    Request model for document ingestion.
    """
    session_id: Optional[str] = Field(
        default=None,
        description="Optional session ID for document indexing"
    )


class IndexResponse(BaseModel):
    session_id: str
    total_chunks: int
    message: str


class QueryRequest(BaseModel):
    """
    Request model for querying indexed documents.
    """
    question: str = Field(..., min_length=3)
    session_id: str = Field(..., description="Session ID returned from indexing")
    top_k: int = Field(default=5, ge=1, le=20)


class QueryResponse(BaseModel):
    question: str
    answer: str
    session_id: str
    top_k: int
