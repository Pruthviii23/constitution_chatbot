import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

from backend.chain.rag_chain import build_chain

chain = build_chain()

# Each conversation needs a session_id
# In production the frontend sends this per user/tab
SESSION_ID = "test-session-1"
config = {"configurable": {"session_id": SESSION_ID}}

print("\n🏛️  Indian Constitution Chatbot")
print("   Type 'exit' to quit\n")

while True:
    question = input("You: ").strip()
    if question.lower() == "exit":
        break
    if not question:
        continue

    result = chain.invoke({"input": question}, config=config)

    print(f"\nBot: {result['answer']}")

    sources = result.get("context", [])
    if sources:
        pages = sorted(set(
            doc.metadata.get("page", "?") for doc in sources
        ))
        print(f"     📄 Sources: pages {pages}")
    print()