"""ChromaDB-powered conversation memory service.

Stores user-assistant conversation turns with semantic embeddings so
the system can retrieve relevant past conversations during a session.

Collection: conversation_memory
  - id:       uuid
  - document: raw message text
  - metadata: {user_id, role, timestamp}
"""

import os
import uuid
from datetime import datetime
from typing import Optional, List

from chromadb.utils import embedding_functions

from src.utils.chroma_client import get_chroma_client

COLL_CONVERSATION = "conversation_memory"


class ConversationMemoryService:
    """Conversation history backed by ChromaDB.

    Unlike PostgreSQL-based logs, this service enables *semantic*
    retrieval of past conversations so the advisor can remember
    context like "user asked about Tesla 3 weeks ago".
    """

    def __init__(self, persist_dir: Optional[str] = None):
        self.client = get_chroma_client(persist_dir)
        self.ef = None
        embed_key = os.getenv("OPENAI_EMBEDDING_API_KEY")
        if embed_key and len(embed_key) > 20 and "your-" not in embed_key:
            self.ef = embedding_functions.OpenAIEmbeddingFunction(
                api_key=embed_key,
                model_name="text-embedding-3-small",
            )

    @property
    def collection(self):
        kwargs = {"name": COLL_CONVERSATION}
        if self.ef:
            kwargs["embedding_function"] = self.ef
        return self.client.get_or_create_collection(**kwargs)

    # ── Write ─────────────────────────────────────────────────

    def add_message(self, user_id: str, role: str, content: str) -> str:
        """Store a single conversation turn."""
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
        return msg_id

    def add_turn(self, user_id: str, user_message: str, assistant_message: str):
        """Store a user + assistant message pair."""
        self.add_message(user_id, "user", user_message)
        self.add_message(user_id, "assistant", assistant_message)

    # ── Read ──────────────────────────────────────────────────

    def get_recent_context(self, user_id: str, query: str = "", limit: int = 5) -> List[str]:
        """Get the most relevant past conversations via semantic search.

        Falls back to most recent messages if no query is provided.
        """
        if query:
            try:
                results = self.collection.query(
                    query_texts=[query],
                    where={"user_id": user_id},
                    n_results=limit,
                )
                if results and results["documents"] and results["documents"][0]:
                    metas = results["metadatas"][0] if results["metadatas"] else []
                    return [
                        f"{metas[i].get('role', 'user')}: {results['documents'][0][i]}"
                        for i in range(len(results["documents"][0]))
                    ]
            except Exception:
                pass

        # Fallback: return most recent messages by timestamp
        all_results = self.collection.get(where={"user_id": user_id})
        if not all_results or not all_results["metadatas"]:
            return []

        messages = []
        for i in range(len(all_results["metadatas"])):
            messages.append({
                "role": all_results["metadatas"][i].get("role", "user"),
                "content": all_results["documents"][i] if all_results["documents"] else "",
                "timestamp": all_results["metadatas"][i].get("timestamp", ""),
            })
        messages.sort(key=lambda m: m["timestamp"], reverse=True)

        return [f"{m['role']}: {m['content']}" for m in messages[:limit]]

    def clear_user(self, user_id: str) -> None:
        """Delete all conversation history for a user."""
        self.collection.delete(where={"user_id": user_id})
