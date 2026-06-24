import os
from dotenv import load_dotenv

from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_classic.chains import create_history_aware_retriever, create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

load_dotenv()

CHROMA_PATH  = os.getenv("CHROMA_PATH",     "./backend/chroma_db")
EMBED_MODEL  = os.getenv("EMBED_MODEL",     "nomic-embed-text")
LLM_MODEL    = os.getenv("LLM_MODEL",       "llama3.2")
OLLAMA_URL   = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
USE_GROQ     = os.getenv("USE_GROQ",        "false").lower() == "true"
GROQ_API_KEY = os.getenv("GROQ_API_KEY",    "")

session_store: dict[str, InMemoryChatMessageHistory] = {}


def get_session_history(session_id: str) -> InMemoryChatMessageHistory:
    if session_id not in session_store:
        session_store[session_id] = InMemoryChatMessageHistory()
    return session_store[session_id]


def get_llm():
    """Return Groq in production, Ollama locally."""
    if USE_GROQ:
        from langchain_groq import ChatGroq
        print("   Using Groq (llama-3.2-3b-preview)")
        return ChatGroq(
            model="llama-3.2-3b-preview",
            api_key=GROQ_API_KEY,
            temperature=0.2,
        )
    else:
        from langchain_ollama import OllamaLLM
        print(f"   Using Ollama ({LLM_MODEL})")
        return OllamaLLM(
            model=LLM_MODEL,
            base_url=OLLAMA_URL,
            temperature=0.2,
        )


def build_chain():
    embeddings = OllamaEmbeddings(
        model=EMBED_MODEL,
        base_url=OLLAMA_URL,
    )

    vectorstore = Chroma(
        persist_directory=CHROMA_PATH,
        embedding_function=embeddings,
    )

    retriever = vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={"k": 4, "fetch_k": 10},
    )

    llm = get_llm()

    condense_prompt = ChatPromptTemplate.from_messages([
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
        ("human", (
            "Given the conversation above, rewrite the follow-up question "
            "into a standalone question. Only return the rewritten question."
        )),
    ])

    history_aware_retriever = create_history_aware_retriever(
        llm, retriever, condense_prompt
    )

    answer_prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "You are an expert on the Indian Constitution. "
            "Answer using ONLY the context below. "
            "If the answer is not in the context, say "
            "'I couldn't find that in the Constitution.' "
            "Do not make up information.\n\n"
            "Context:\n{context}"
        )),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ])

    answer_chain = create_stuff_documents_chain(llm, answer_prompt)
    rag_chain    = create_retrieval_chain(history_aware_retriever, answer_chain)

    chain_with_history = RunnableWithMessageHistory(
        rag_chain,
        get_session_history,
        input_messages_key="input",
        history_messages_key="chat_history",
        output_messages_key="answer",
    )

    print("✅ RAG chain ready.")
    return chain_with_history