import os
import sys
import re
import shutil
from dotenv import load_dotenv

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma

load_dotenv()

PDF_PATH    = os.getenv("PDF_PATH",        "./backend/constitution.pdf")
CHROMA_PATH = os.getenv("CHROMA_PATH",     "./backend/chroma_db")
EMBED_MODEL = os.getenv("EMBED_MODEL",     "nomic-embed-text")
OLLAMA_URL  = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
BATCH_SIZE  = 50

# Pages 0–30  : Table of Contents  → skip (no article body text)
# Pages 31–284: Main constitutional body → index these
# Pages 285+  : Schedules (lists, tables) → skip
#               (they contain "21. Fisheries", "21. Cultural activities" etc.
#                which create false matches for Article 21 queries)
BODY_START = 31
BODY_END   = 284   # inclusive


def load_pdf(path: str):
    print(f"📄 Loading PDF: {path}")
    loader = PyPDFLoader(path)
    pages = loader.load()
    print(f"   Total pages in PDF: {len(pages)}")
    body = [p for p in pages
            if BODY_START <= p.metadata.get("page", 0) <= BODY_END]
    print(f"   Body pages indexed: {len(body)}  (pages {BODY_START}–{BODY_END})")
    return body


def chunk_body(pages) -> list[Document]:
    """
    1. Merge body pages into one string with page-offset tracking.
    2. Split on article boundaries using a pattern that matches the
       actual PDF format: '21. Protection of life.—...'
    3. Prefix every chunk with 'Article N:' so the article number
       is always present in the embedded text.
    """
    print("✂️  Chunking by article boundaries...")

    # ── merge ────────────────────────────────────────────────────
    full_text = ""
    page_map  = {}   # char_offset → page_number

    for page in pages:
        page_map[len(full_text)] = page.metadata.get("page", 0)
        full_text += page.page_content + " "

    def get_page(offset: int) -> int:
        result = BODY_START
        for pos, pg in sorted(page_map.items()):
            if offset >= pos:
                result = pg
            else:
                break
        return result

    # ── find article boundaries ───────────────────────────────────
    # Matches: "21. Protection" or "21A. Right" or "243ZI. Incorporation"
    # Requires a capital letter after the title to avoid matching
    # footnote numbers, list entries, or sub-clauses like "(1)"
    article_re = re.compile(
        r'(?<!\()(?<!\d)'        # not preceded by ( or digit
        r'(\d{1,3}[A-Z]{0,3})'  # article number: 21, 21A, 243ZI …
        r'\. '                   # literal ". " (dot + space)
        r'([A-Z][a-z])'         # title starts with Capital + lowercase
    )

    matches = list(article_re.finditer(full_text))
    print(f"   Found {len(matches)} article boundaries in body.")

    # ── build chunks ──────────────────────────────────────────────
    MAX_CHARS = 1200
    chunks    = []

    for i, match in enumerate(matches):
        art_num   = match.group(1)
        start     = match.start()
        end       = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        body_text = full_text[start:end].strip()
        page      = get_page(start)

        # Prefix with explicit article label — survives any chunk split
        labelled = f"Article {art_num}: {body_text}"

        if len(labelled) <= MAX_CHARS:
            chunks.append(Document(
                page_content=labelled,
                metadata={"page": page, "article": art_num}
            ))
        else:
            # Long article — split into sub-chunks, each carrying the label
            header = f"Article {art_num}: "
            words  = labelled.split()
            sub    = ""

            for word in words:
                if len(sub) + len(word) + 1 > MAX_CHARS:
                    if sub.strip():
                        chunks.append(Document(
                            page_content=sub.strip(),
                            metadata={"page": page, "article": art_num}
                        ))
                    sub = header + word + " "
                else:
                    sub += word + " "

            if sub.strip() and sub.strip() != header.strip():
                chunks.append(Document(
                    page_content=sub.strip(),
                    metadata={"page": page, "article": art_num}
                ))

    print(f"   Created {len(chunks)} chunks total.")

    # ── sanity checks ─────────────────────────────────────────────
    for target in ["12", "14", "19", "21", "21A", "32", "226", "368"]:
        hits = [c for c in chunks if c.metadata.get("article") == target]
        if hits:
            preview = hits[0].page_content[:80].replace("\n", " ")
            print(f"   ✓ Article {target:5s} → {len(hits)} chunk(s) | '{preview}...'")
        else:
            print(f"   ✗ Article {target} NOT FOUND")

    return chunks


def embed_and_store(chunks: list[Document]):
    print(f"\n🔢 Embedding {len(chunks)} chunks (batch size {BATCH_SIZE})...")

    embeddings = OllamaEmbeddings(
        model=EMBED_MODEL,
        base_url=OLLAMA_URL,
    )

    test = embeddings.embed_query("Article 21 right to life")
    print(f"   ✓ Ollama connected — dim: {len(test)}")

    vectorstore = None
    total   = len(chunks)
    batches = list(range(0, total, BATCH_SIZE))

    for i, start in enumerate(batches):
        batch = chunks[start: start + BATCH_SIZE]
        end   = min(start + BATCH_SIZE, total)
        print(f"   Batch {i+1}/{len(batches)}  "
              f"({start+1}–{end} / {total})", end="\r")

        if vectorstore is None:
            vectorstore = Chroma.from_documents(
                documents=batch,
                embedding=embeddings,
                persist_directory=CHROMA_PATH,
            )
        else:
            vectorstore.add_documents(batch)

    count = vectorstore._collection.count()
    print(f"\n✅ Done — {count} vectors stored at {CHROMA_PATH}")
    return vectorstore


def main():
    if os.path.exists(CHROMA_PATH) and os.listdir(CHROMA_PATH):
        print(f"⚠️  ChromaDB exists at {CHROMA_PATH}")
        ans = input("   Re-ingest and overwrite? (y/n): ").strip().lower()
        if ans != "y":
            print("   Skipping.")
            sys.exit(0)
        shutil.rmtree(CHROMA_PATH)
        print("   Old DB removed.")

    pages  = load_pdf(PDF_PATH)
    chunks = chunk_body(pages)
    embed_and_store(chunks)


if __name__ == "__main__":
    main()