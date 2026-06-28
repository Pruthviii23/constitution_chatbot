import os
import sys
import uuid
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.chain.rag_chain import build_chain, session_store

load_dotenv()

app = FastAPI(title="ConstiBot — Indian Constitution Chatbot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("🔧 Loading RAG chain...")
chain = build_chain()
print("🚀 API ready.")


# ── Request / Response models ─────────────────────────────────────

class ChatRequest(BaseModel):
    question: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    answer: str
    session_id: str
    sources: list[int]          # page numbers
    articles: list[str] = []   # article numbers e.g. ["21", "14"]


# ── Routes ────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "ok", "message": "ConstiBot API is running."}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    session_id = request.session_id or str(uuid.uuid4())
    config     = {"configurable": {"session_id": session_id}}

    try:
        result = chain.invoke({"input": request.question}, config=config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chain error: {str(e)}")

    context_docs = result.get("context", [])

    # Deduplicated page numbers from retrieved chunks
    sources = sorted(set(
        doc.metadata.get("page", 0)
        for doc in context_docs
    ))

    # Article numbers from chunk metadata — e.g. ["14", "19", "21"]
    articles = sorted(set(
        doc.metadata["article"]
        for doc in context_docs
        if doc.metadata.get("article")
    ), key=lambda x: (len(x), x))   # sort numerically-ish: 14, 19, 21, 21A

    answer = result.get("answer", "").strip()

    # Safety net — if answer is empty, return a clear fallback
    if not answer:
        answer = (
            "I wasn't able to generate a response. "
            "Please try rephrasing your question."
        )

    return ChatResponse(
        answer=answer,
        session_id=session_id,
        sources=sources,
        articles=articles,
    )


@app.delete("/session/{session_id}")
def clear_session(session_id: str):
    """Called when user clicks 'New Chat' — clears conversation memory."""
    if session_id in session_store:
        del session_store[session_id]
        return {"status": "cleared", "session_id": session_id}
    return {"status": "not_found", "session_id": session_id}