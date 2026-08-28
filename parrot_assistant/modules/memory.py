import sys
import os
import chromadb

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import MEMORY_DB_PATH

class MemoryManager:
    """
    Handles Short-term context buffer + Long-term Vector DB (ChromaDB)
    """
    def __init__(self):
        self.short_term_buffer = []
        self.max_buffer_size = 10

        # Initialize ChromaDB for long term memory
        os.makedirs(os.path.dirname(MEMORY_DB_PATH) if os.path.dirname(MEMORY_DB_PATH) else ".", exist_ok=True)
        self.chroma_client = chromadb.PersistentClient(path=MEMORY_DB_PATH)
        self.collection = self.chroma_client.get_or_create_collection(name="assistant_memory")
        self.doc_id = self.collection.count()

    def add_to_short_term(self, role: str, content: str):
        self.short_term_buffer.append({"role": role, "content": content})
        if len(self.short_term_buffer) > self.max_buffer_size:
            self.short_term_buffer.pop(0)

    def get_short_term_context(self) -> str:
        context = ""
        for msg in self.short_term_buffer:
            context += f"{msg['role'].capitalize()}: {msg['content']}\n"
        return context

    def add_to_long_term(self, content: str):
        self.collection.add(
            documents=[content],
            ids=[f"doc_{self.doc_id}"]
        )
        self.doc_id += 1

    def query_long_term(self, query: str, n_results: int = 2) -> list:
        if self.collection.count() == 0:
            return []

        results = self.collection.query(
            query_texts=[query],
            n_results=min(n_results, self.collection.count())
        )
        return results['documents'][0] if results['documents'] else []

    def clear_short_term(self):
        self.short_term_buffer = []
