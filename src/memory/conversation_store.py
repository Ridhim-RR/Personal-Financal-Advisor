import json
import os
import uuid
from datetime import datetime
from typing import Optional

from src.utils.chroma_client import get_chroma_client


class ConversationStore:
    """Stores conversation history per user in a ChromaDB collection.

    Each message is stored as a document with:
      - id:        unique message id
      - document:  the message text
      - metadata:  {user_id, role, timestamp}
    Queries filter by user_id and sort by timestamp to preserve order.
    """

    def __init__(self, collection_name: str = "conversations", persist_dir: Optional[str] = None):
        self.client = get_chroma_client(persist_dir)
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_message(self, user_id: str, role: str, content: str) -> None:
        """Append a message to the user's conversation history."""
        msg_id = str(uuid.uuid4())
        self.collection.add(
            ids=[msg_id],
            documents=[content],
            metadatas=[{
                "user_id": user_id,
                "role": role,
                "timestamp": datetime.utcnow().isoformat(),
            }],
        )

    def get_history(self, user_id: str, limit: int = 10) -> list[dict]:
        """Return the most recent N messages for a user.

        ChromaDB's `get` with where-filter returns all matching docs.
        We sort by timestamp descending and take `limit`.
        """
        result = self.collection.get(
            where={"user_id": user_id},
        )
        if not result or not result["metadatas"]:
            return []

        # Build list of {role, content, timestamp} and sort
        messages = []
        for i in range(len(result["metadatas"])):
            messages.append({
                "role": result["metadatas"][i].get("role", "unknown"),
                "content": result["documents"][i] if result["documents"] else "",
                "timestamp": result["metadatas"][i].get("timestamp", ""),
            })

        messages.sort(key=lambda m: m["timestamp"], reverse=True)
        return messages[:limit]

    def clear_history(self, user_id: str) -> None:
        """Delete all conversation history for a user."""
        self.collection.delete(where={"user_id": user_id})

    def get_relevant_context(self, user_id: str, query: str, limit: int = 3) -> list[str]:
        """Return recent conversation messages as context strings.

        Uses ChromaDB's query (semantic search) if an embedding function
        is configured, otherwise falls back to simple timestamp sort.
        """
        try:
            # Try semantic search via ChromaDB's built-in embedding function
            results = self.collection.query(
                query_texts=[query],
                where={"user_id": user_id},
                n_results=limit,
            )
            if results and results["documents"] and results["documents"][0]:
                docs = results["documents"][0]
                meta = results["metadatas"][0] if results["metadatas"] else []
                return [
                    f"{meta[i].get('role', 'user')}: {docs[i]}"
                    for i in range(len(docs))
                ]
        except Exception:
            pass

        # Fallback: return most recent messages
        history = self.get_history(user_id, limit=limit)
        return [f"{m['role']}: {m['content']}" for m in history]
