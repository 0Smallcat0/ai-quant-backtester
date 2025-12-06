import os
from typing import List, Dict, Optional, Any

# Try importing chromadb, handle missing failure gracefully for "Lite" environments
try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

class VectorStore:
    """
    A lightweight wrapper around ChromaDB for storing and retrieving code chunks.
    """
    def __init__(self, collection_name: str = "agent_knowledge", embedding_fn = None, persist_directory: str = "./db/chroma"):
        if not CHROMA_AVAILABLE:
            print("Warning: chromadb not installed. RAG will be disabled.")
            self.client = None
            self.collection = None
            return

        # Ensure persist directory exists
        os.makedirs(persist_directory, exist_ok=True)

        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # If no embedding function provided, Chroma uses default (all-MiniLM-L6-v2)
        # But we might want to pass OpenAI embedding function if we want better quality.
        # For now, let's allow passing it.
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=embedding_fn
        )

    def add_documents(self, documents: List[str], metadatas: List[Dict[str, Any]], ids: List[str]):
        """
        Adds documents to the store.
        """
        if not self.collection:
            return

        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

    def query(self, query: str, n_results: int = 5) -> Dict[str, Any]:
        """
        Queries the store for most relevant documents.
        """
        if not self.collection:
            return {"documents": [], "metadatas": [], "distances": []}

        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        return results
