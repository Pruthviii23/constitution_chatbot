import os
import sys
import uuid
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Make sure backend package is importable
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.chain.rag_chain import build_chain, session_store

load_dotenv()

app = FastAPI(title="Indian Constitution Chatbot API")

# ── CORS ──────────────────────────────────────────────────────────
# Allows the Next.js frontend (localhost:3000) to call this API.
# In production, replace "*" with your actual Vercel domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Build the chain once at startup ───────────────────────────────
# This loads ChromaDB and the LLM into memory.
# All requests share the same chain instance.
print("🔧 Loading RAG chain...")
chain = build_chain()
print("🚀 API ready.")


# ── Request / Response models ─────────────────────────────────────
class ChatRequest(BaseModel):
    question: str
    session_id: str | None = None   # optional — we generate one if missing


class SourcePage(BaseModel):
    page: int


class ChatResponse(BaseModel):
    answer: str
    session_id: str
    sources: list[int]


# ── Routes ────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {"status": "ok", "message": "Constitution Chatbot API is running."}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """
    Main chat endpoint.
    
    - If session_id is provided, continues that conversation.
    - If not, creates a new session and returns the new session_id
      so the frontend can include it in follow-up requests.
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    # Generate session_id for new conversations
    session_id = request.session_id or str(uuid.uuid4())
    config    = {"configurable": {"session_id": session_id}}

    try:
        result = chain.invoke({"input": request.question}, config=config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chain error: {str(e)}")

    # Extract unique source page numbers from retrieved chunks
    sources = sorted(set(
        doc.metadata.get("page", 0)
        for doc in result.get("context", [])
    ))

    return ChatResponse(
        answer=result["answer"],
        session_id=session_id,
        sources=sources,
    )


@app.delete("/session/{session_id}")
def clear_session(session_id: str):
    """Clear chat history for a session (e.g. when user clicks 'New Chat')."""
    if session_id in session_store:
        del session_store[session_id]
        return {"status": "cleared", "session_id": session_id}
    return {"status": "not_found", "session_id": session_id}