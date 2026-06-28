import os
from dotenv import load_dotenv

from langchain_chroma import Chroma
from langchain_classic.chains import create_history_aware_retriever, create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

CHROMA_PATH   = os.getenv("CHROMA_PATH",     "./backend/chroma_db")
EMBED_MODEL   = os.getenv("EMBED_MODEL",     "nomic-embed-text")
LLM_MODEL     = os.getenv("LLM_MODEL",       "llama3.2")
OLLAMA_URL    = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
USE_GROQ      = os.getenv("USE_GROQ",        "false").lower() == "true"
GROQ_API_KEY  = os.getenv("GROQ_API_KEY",    "")
NOMIC_API_KEY = os.getenv("NOMIC_API_KEY",   "")

# Session store — keyed by session_id, cleared on "New Chat"
session_store: dict[str, InMemoryChatMessageHistory] = {}


def get_session_history(session_id: str) -> InMemoryChatMessageHistory:
    if session_id not in session_store:
        session_store[session_id] = InMemoryChatMessageHistory()
    history = session_store[session_id]
    # Keep only last 3 turns (6 messages) to avoid context pollution
    if len(history.messages) > 6:
        history.messages = history.messages[-6:]
    return history


def get_embeddings():
    if NOMIC_API_KEY:
        from langchain_nomic import NomicEmbeddings
        print("   Using Nomic API embeddings")
        return NomicEmbeddings(
            model="nomic-embed-text-v1",
            nomic_api_key=NOMIC_API_KEY,
        )
    from langchain_ollama import OllamaEmbeddings
    print("   Using Ollama embeddings (local)")
    return OllamaEmbeddings(model=EMBED_MODEL, base_url=OLLAMA_URL)


def get_llm():
    if USE_GROQ:
        from langchain_groq import ChatGroq
        print("   Using Groq LLM")
        return ChatGroq(
            model="openai/gpt-oss-20b",
            api_key=GROQ_API_KEY,
            temperature=0.1,
        )
    from langchain_ollama import OllamaLLM
    print(f"   Using Ollama LLM ({LLM_MODEL})")
    return OllamaLLM(model=LLM_MODEL, base_url=OLLAMA_URL, temperature=0.1)


def build_chain():
    # ── 1. Embeddings + Vector store ──────────────────────────────
    embeddings  = get_embeddings()
    vectorstore = Chroma(
        persist_directory=CHROMA_PATH,
        embedding_function=embeddings,
    )

    # ── 2. Retriever ──────────────────────────────────────────────
    # fetch_k=20 gives MMR a wide pool; k=6 returns diverse top results
    retriever = vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={"k": 6, "fetch_k": 20, "lambda_mult": 0.7},
    )

    # ── 3. LLM ────────────────────────────────────────────────────
    llm = get_llm()

    # ── 4. Condense prompt ────────────────────────────────────────
    # Rewrites follow-up questions into standalone questions.
    # Key rule: if the question already contains an article number
    # or is self-contained, return it AS-IS — do not rephrase away
    # the specific terms that ChromaDB needs to retrieve correctly.
    condense_prompt = ChatPromptTemplate.from_messages([
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
        ("human", (
            "Given the chat history above, rewrite the follow-up question "
            "into a complete standalone question about the Indian Constitution. "
            "IMPORTANT RULES:\n"
            "- If the question already contains an Article number (e.g. Article 21), "
            "  keep that number in the rewritten question.\n"
            "- If the question is already standalone (no pronouns like 'that', 'it', "
            "  'this' referring to earlier messages), return it EXACTLY as written.\n"
            "- Never remove specific article numbers, amendment names, or legal terms.\n"
            "Return ONLY the rewritten question, nothing else."
        )),
    ])

    history_aware_retriever = create_history_aware_retriever(
        llm, retriever, condense_prompt
    )

    # ── 5. Answer prompt ──────────────────────────────────────────
    answer_prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "You are ConstiBot, an expert on the Indian Constitution.\n\n"
            "RULES:\n"
            "1. Answer using ONLY the context chunks provided below.\n"
            "2. Each chunk starts with 'Article N:' — use the article number "
            "   when referencing provisions.\n"
            "3. If the context contains PARTIAL information, share what is "
            "   there and clearly note what is missing.\n"
            "4. ONLY say 'I couldn't find that in the Constitution' if ALL "
            "   context chunks are completely irrelevant to the question.\n"
            "5. Never produce an empty response.\n"
            "6. Structure longer answers with clear headings.\n\n"
            "Context chunks:\n"
            "----------------\n"
            "{context}\n"
            "----------------"
        )),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ])

    # ── 6. Assemble chain ─────────────────────────────────────────
    answer_chain = create_stuff_documents_chain(
        llm,
        answer_prompt,
        output_parser=StrOutputParser(),
    )

    rag_chain = create_retrieval_chain(history_aware_retriever, answer_chain)

    chain_with_history = RunnableWithMessageHistory(
        rag_chain,
        get_session_history,
        input_messages_key="input",
        history_messages_key="chat_history",
        output_messages_key="answer",
    )

    print("✅ RAG chain ready.")
    return chain_with_history