import os
import sys
import shutil
from dotenv import load_dotenv

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma

load_dotenv()

PDF_PATH    = os.getenv("PDF_PATH",        "./backend/constitution.pdf")
CHROMA_PATH = os.getenv("CHROMA_PATH",     "./backend/chroma_db")
EMBED_MODEL = os.getenv("EMBED_MODEL",     "nomic-embed-text")
OLLAMA_URL  = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

BATCH_SIZE  = 50  # embed 50 chunks at a time — safe for local Ollama


def load_pdf(path: str):
    print(f"📄 Loading PDF from: {path}")
    loader = PyPDFLoader(path)
    pages = loader.load()
    print(f"   Loaded {len(pages)} pages.")
    return pages


def split_documents(pages):
    print("✂️  Splitting into chunks...")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100,
        separators=["\n\n", "\n", ".", " ", ""],
    )
    chunks = splitter.split_documents(pages)
    print(f"   Created {len(chunks)} chunks.")
    return chunks


def embed_and_store(chunks):
    print(f"🔢 Embedding with '{EMBED_MODEL}' in batches of {BATCH_SIZE}...")

    embeddings = OllamaEmbeddings(
        model=EMBED_MODEL,
        base_url=OLLAMA_URL,
    )

    # Test connection first
    test = embeddings.embed_query("test")
    print(f"   ✓ Connected — embedding dimension: {len(test)}")

    # ── Batch ingestion ───────────────────────────────────────────
    # We create the Chroma DB with the first batch, then ADD
    # subsequent batches — avoids one giant call that times out.
    total   = len(chunks)
    batches = range(0, total, BATCH_SIZE)

    vectorstore = None

    for i, start in enumerate(batches):
        batch = chunks[start : start + BATCH_SIZE]
        end   = min(start + BATCH_SIZE, total)

        print(f"   Batch {i+1}/{len(batches)}  ({start+1}–{end} of {total})", end="\r")

        if vectorstore is None:
            # First batch — create the DB
            vectorstore = Chroma.from_documents(
                documents=batch,
                embedding=embeddings,
                persist_directory=CHROMA_PATH,
            )
        else:
            # Subsequent batches — add to existing DB
            vectorstore.add_documents(batch)

    print(f"\n✅ Done! Stored {vectorstore._collection.count()} vectors → {CHROMA_PATH}")
    return vectorstore


def main():
    if os.path.exists(CHROMA_PATH) and os.listdir(CHROMA_PATH):
        print("⚠️  ChromaDB already exists at", CHROMA_PATH)
        answer = input("   Re-ingest and overwrite? (y/n): ").strip().lower()
        if answer != "y":
            print("   Skipping ingestion.")
            sys.exit(0)
        shutil.rmtree(CHROMA_PATH)
        print("   Old DB removed.")

    pages  = load_pdf(PDF_PATH)
    chunks = split_documents(pages)
    embed_and_store(chunks)


if __name__ == "__main__":
    main()