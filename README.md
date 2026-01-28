# 📄 DocuChat — RAG-Based Question Answering System

A **production-grade Retrieval-Augmented Generation (RAG) system** that allows users to upload documents and ask contextual questions using embeddings, FAISS similarity search, background ingestion, and an LLM-powered answer generator.

This project is built to **demonstrate applied AI system design**, not just prompt usage.

---

## 🚀 Objective

Build an API-driven system that:
- Accepts documents
- Indexes them using embeddings
- Retrieves relevant content via similarity search
- Generates accurate answers using an LLM
- Handles ingestion asynchronously
- Applies basic rate limiting
- Tracks meaningful metrics

---

## 🧠 Key Features

- 📁 Upload documents (`PDF`, `TXT`)
- ✂️ Intelligent chunking strategy
- 🔢 Embedding generation using SentenceTransformers
- 📦 Vector storage using **FAISS**
- 🔍 Similarity-based retrieval
- 🤖 LLM-powered answer generation (Groq / OpenAI-compatible)
- 🧵 Background ingestion jobs
- 🚦 API rate limiting
- 📊 Metric logging (latency, similarity distance)
- 🌐 Simple web UI (HTML + CSS)

---

## 🛠️ Tech Stack

| Layer | Technology |
|------|------------|
| API | FastAPI |
| Embeddings | sentence-transformers (MiniLM-L6-v2) |
| Vector Store | FAISS (local) |
| LLM | Groq / OpenAI-compatible |
| Background Jobs | FastAPI BackgroundTasks |
| Validation | Pydantic |
| Rate Limiting | SlowAPI |
| UI | HTML + CSS |
| Logging | Custom structured logger |

---

## 📁 Project Structure

```text
.
├── api/
│   └── main.py                  # FastAPI application
├── src/
│   └── DocumentChat/
│       ├── ingestion.py         # Document ingestion & FAISS indexing
│       └── retrieval.py         # Retrieval + answer generation
├── utils/
│   ├── document_ops.py          # File abstraction & parsing
│   ├── model_loader.py          # Embeddings + LLM loader
│   └── config_loader.py         # YAML config loader
├── prompt/
│   └── prompt_library.py        # Centralized prompt templates
├── models/
│   └── models.py                # Pydantic request/response models
├── exception/
│   └── custom_exception.py      # Custom exception handling
├── logger/
│   └── custom_logger.py         # Structured logging
├── config/
│   └── config.yaml              # Chunking, model, retrieval configs
├── templates/
│   └── index.html               # Web UI
├── static/
│   └── style.css                # UI styling
├── faiss_index/                 # Generated FAISS indexes (runtime)
├── data/                        # Uploaded files (runtime)
├── requirements.txt
├── setup.py
├── README.md
