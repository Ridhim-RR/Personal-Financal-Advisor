"""ChromaDB-powered semantic memory service.

Stores unstructured, semantic user context for personalization:
  - User_preferences:  "User prefers dividend stocks", "User dislikes oil"
  - Investment_goals:  "Retirement in 20 years", "Save for house in 5 years"
  - Recommendation_memory: "Was recommended AAPL buy, followed it"

This is NOT the system of record — that's PostgreSQL. ChromaDB augments
LLM context with relevant semantic memories during recommendation flows.
"""

import os
import uuid
from typing import Optional, List

from chromadb.utils import embedding_functions
from langsmith import traceable

from src.utils.chroma_client import get_chroma_client


# Collection names
COLL_PREFERENCES = "user_preferences"
COLL_GOALS = "investment_goals"
COLL_RECOMMENDATIONS = "recommendation_memory"


class MemoryService:
    """Semantic memory service backed by ChromaDB.

    Each "memory" is a short text snippet stored as a document with
    user_id in metadata. ChromaDB auto-embeds text using the default
    embedding function (all-MiniLM-L6-v2 via sentence-transformers)
    so queries return semantically similar memories.
    """

    def __init__(self, persist_dir: Optional[str] = None):
        self.client = get_chroma_client(persist_dir)
        # Use OpenAI embeddings only if a valid API key is explicitly configured
        # for embeddings (separate from the default LLM key).
        self.ef = None
        embed_key = os.getenv("OPENAI_EMBEDDING_API_KEY")
        if embed_key and len(embed_key) > 20 and "your-" not in embed_key:
            self.ef = embedding_functions.OpenAIEmbeddingFunction(
                api_key=embed_key,
                model_name="text-embedding-3-small",
            )
        # If not set, ChromaDB's default all-MiniLM-L6-v2 embedding function is used automatically.

        self._collections = {}

    def _get_collection(self, name: str):
        """Get or create a named ChromaDB collection."""
        if name not in self._collections:
            kwargs = {"name": name}
            if self.ef:
                kwargs["embedding_function"] = self.ef
            self._collections[name] = self.client.get_or_create_collection(**kwargs)
        return self._collections[name]

    # ── Store ─────────────────────────────────────────────────

    def store_preference(self, user_id: str, preference: str) -> str:
        """Store a user preference as a semantic memory."""
        doc_id = str(uuid.uuid4())
        self._get_collection(COLL_PREFERENCES).add(
            ids=[doc_id],
            documents=[preference],
            metadatas=[{"user_id": user_id, "type": "preference"}],
        )
        return doc_id

    def store_goal(self, user_id: str, goal: str) -> str:
        """Store an investment goal."""
        doc_id = str(uuid.uuid4())
        self._get_collection(COLL_GOALS).add(
            ids=[doc_id],
            documents=[goal],
            metadatas=[{"user_id": user_id, "type": "goal"}],
        )
        return doc_id

    def store_recommendation_memory(self, user_id: str, memory: str) -> str:
        """Store a memory about a past recommendation."""
        doc_id = str(uuid.uuid4())
        self._get_collection(COLL_RECOMMENDATIONS).add(
            ids=[doc_id],
            documents=[memory],
            metadatas=[{"user_id": user_id, "type": "recommendation"}],
        )
        return doc_id

    # ── Retrieve ──────────────────────────────────────────────
    @traceable
    def get_relevant_memories(self, user_id: str, query: str, limit: int = 5) -> List[str]:
        """Retrieve the most semantically relevant memories across all collections."""
        memories = []
        for coll_name in [COLL_PREFERENCES, COLL_GOALS, COLL_RECOMMENDATIONS]:
            try:
                coll = self._get_collection(coll_name)
                results = coll.query(
                    query_texts=[query],
                    where={"user_id": user_id},
                    n_results=max(1, limit // 3),
                )
                if results and results["documents"] and results["documents"][0]:
                    memories.extend(results["documents"][0])
            except Exception:
                continue
        return memories[:limit]

    def get_all_user_memories(self, user_id: str) -> List[dict]:
        """Return all stored memories for a user (for debugging / profile view)."""
        all_items = []
        for coll_name in [COLL_PREFERENCES, COLL_GOALS, COLL_RECOMMENDATIONS]:
            coll = self._get_collection(coll_name)
            results = coll.get(where={"user_id": user_id})
            if results and results["documents"]:
                for i in range(len(results["documents"])):
                    all_items.append({
                        "collection": coll_name,
                        "memory": results["documents"][i],
                        "metadata": results["metadatas"][i] if results["metadatas"] else {},
                    })
        return all_items

    # ── Onboarding ────────────────────────────────────────────

    def onboard_user(self, user_id: str, profile: dict, conversation: str = None):
        """Seed ChromaDB with initial semantic memories from the user profile.

        Called after PostgreSQL profile is created.
        """
        risk = profile.get("risk_appetite", "moderate")
        goal = profile.get("investment_goal", "growth")
        horizon = profile.get("investment_horizon", "medium")
        sectors = profile.get("preferred_sectors", [])

        self.store_preference(user_id, f"User has a {risk} investing style.")
        self.store_goal(user_id, f"Investment goal: {goal} with a {horizon} time horizon.")

        if sectors:
            self.store_preference(user_id, f"User prefers investing in: {', '.join(sectors)}.")

        excluded = profile.get("excluded_sectors", [])
        if excluded:
            self.store_preference(user_id, f"User avoids: {', '.join(excluded)}.")

        if conversation:
            self.store_preference(user_id, f"User said: {conversation}")

    # ── Clear ──────────────────────────────────────────────────

    def clear_user(self, user_id: str) -> None:
        """Remove all memories for a user from all collections."""
        for coll_name in [COLL_PREFERENCES, COLL_GOALS, COLL_RECOMMENDATIONS]:
            try:
                self._get_collection(coll_name).delete(where={"user_id": user_id})
            except Exception:
                continue
