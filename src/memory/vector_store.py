import json
import os
import uuid
from typing import Optional

from src.utils.chroma_client import get_chroma_client


class VectorStore:
    """Stores and searches text embeddings for personalization RAG
    using ChromaDB as the vector database backend.

    Automatically embeds text using ChromaDB's built-in embedding
    function (all-MiniLM-L6-v2 via sentence-transformers), so you
    don't need to manage embeddings manually.

    Collections used:
      - "user_rag": stores user conversations, preferences, and feedback
    """

    def __init__(self, collection_name: str = "user_rag", persist_dir: Optional[str] = None):
        self.client = get_chroma_client(persist_dir)
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def store(self, user_id: str, content_type: str, content: str, embedding: Optional[list[float]] = None) -> None:
        """Store a piece of content with ChromaDB auto-embedding.

        ChromaDB computes the embedding automatically from `documents`
        using its built-in default embedding function.
        """
        doc_id = str(uuid.uuid4())
        self.collection.add(
            ids=[doc_id],
            documents=[content],
            metadatas=[{
                "user_id": user_id,
                "content_type": content_type,
            }],
            embeddings=[embedding] if embedding else None,
        )

    def search(self, user_id: str, query: str, content_type: Optional[str] = None, limit: int = 5) -> list[str]:
        """Find most similar stored content by semantic similarity.

        ChromaDB automatically embeds the query and performs
        cosine similarity search against all stored documents.
        """
        where = {"user_id": user_id}
        if content_type:
            where["content_type"] = content_type

        results = self.collection.query(
            query_texts=[query],
            where=where,
            n_results=limit,
        )

        if results and results["documents"] and results["documents"][0]:
            return results["documents"][0]
        return []

    def clear_user(self, user_id: str) -> None:
        """Remove all stored entries for a user."""
        self.collection.delete(where={"user_id": user_id})
