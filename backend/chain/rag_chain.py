import os
from dotenv import load_dotenv

from langchain_ollama import OllamaEmbeddings, OllamaLLM
from langchain_chroma import Chroma

# --- FIX: Route these explicitly through the classic library ---
from langchain_classic.chains import (
    create_history_aware_retriever, 
    create_retrieval_chain
)
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
# ---------------------------------------------------------------

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

load_dotenv()

CHROMA_PATH = os.getenv("CHROMA_PATH",     "./backend/chroma_db")
EMBED_MODEL = os.getenv("EMBED_MODEL",     "nomic-embed-text")
LLM_MODEL   = os.getenv("LLM_MODEL",       "llama3.2")
OLLAMA_URL  = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# In-memory store keyed by session_id
# Each session gets its own independent chat history
session_store: dict[str, InMemoryChatMessageHistory] = {}


def get_session_history(session_id: str) -> InMemoryChatMessageHistory:
    """Return existing history for this session, or create a new one."""
    if session_id not in session_store:
        session_store[session_id] = InMemoryChatMessageHistory()
    return session_store[session_id]


def build_chain():
    """
    Builds and returns the full RAG chain using modern LCEL patterns.
    """

    # 1. Embeddings — must match what was used during ingestion
    embeddings = OllamaEmbeddings(
        model=EMBED_MODEL,
        base_url=OLLAMA_URL,
    )

    # 2. Load ChromaDB from disk
    vectorstore = Chroma(
        persist_directory=CHROMA_PATH,
        embedding_function=embeddings,
    )

    # 3. Retriever with MMR for diverse, relevant chunks
    retriever = vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={"k": 4, "fetch_k": 10},
    )

    # 4. LLM
    llm = OllamaLLM(
        model=LLM_MODEL,
        base_url=OLLAMA_URL,
        temperature=0.2,
    )

    # 5. Prompt to rewrite follow-up questions into standalone questions
    condense_prompt = ChatPromptTemplate.from_messages([
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
        ("human", (
            "Given the conversation above, rewrite the follow-up question "
            "into a standalone question that can be understood without the "
            "chat history. Only return the rewritten question, nothing else."
        )),
    ])

    # 6. History-aware retriever combination
    history_aware_retriever = create_history_aware_retriever(
        llm, retriever, condense_prompt
    )

    # 7. Prompt for the final answer generation
    answer_prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "You are an expert on the Indian Constitution. "
            "Answer the user's question using ONLY the context below. "
            "If the answer is not in the context, say "
            "'I couldn't find that in the Constitution.' "
            "Do not make up information.\n\n"
            "Context:\n{context}"
        )),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ])

    # 8. Stuff chain — stuffs retrieved docs into the answer prompt
    answer_chain = create_stuff_documents_chain(llm, answer_prompt)

    # 9. Full retrieval chain: retrieve → answer
    rag_chain = create_retrieval_chain(history_aware_retriever, answer_chain)

    # 10. Wrap with message history management
    chain_with_history = RunnableWithMessageHistory(
        rag_chain,
        get_session_history,
        input_messages_key="input",
        history_messages_key="chat_history",
        output_messages_key="answer",
    )

    print("✅ RAG chain ready.")
    return chain_with_history