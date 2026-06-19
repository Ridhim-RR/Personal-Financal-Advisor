import json
from typing import Optional

from src.utils.chroma_client import get_chroma_client


class ProfileStore:
    """Stores and retrieves user profiles in a ChromaDB collection.

    Each profile is stored as a document with:
      - id: user_id
      - document: JSON-serialized profile dict
      - metadata: {"user_id": str, "updated_at": str}
    """

    def __init__(self, collection_name: str = "user_profiles", persist_dir: Optional[str] = None):
        self.client = get_chroma_client(persist_dir)
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def get_profile(self, user_id: str) -> Optional[dict]:
        """Load a user's full profile by user_id."""
        result = self.collection.get(ids=[user_id])
        if result and result["documents"]:
            return json.loads(result["documents"][0])
        return None

    def create_profile(self, user_id: str, profile: dict) -> dict:
        """Create a new user profile."""
        profile["user_id"] = user_id
        self.collection.upsert(
            ids=[user_id],
            documents=[json.dumps(profile)],
            metadatas=[{"user_id": user_id}],
        )
        return profile

    def update_profile(self, user_id: str, updates: dict) -> Optional[dict]:
        """Partially update a user profile (merge into existing)."""
        existing = self.get_profile(user_id)
        if existing is None:
            return None
        existing.update(updates)
        self.collection.upsert(
            ids=[user_id],
            documents=[json.dumps(existing)],
            metadatas=[{"user_id": user_id}],
        )
        return existing

    def delete_profile(self, user_id: str) -> bool:
        """Remove a user profile."""
        existing = self.get_profile(user_id)
        if existing is None:
            return False
        self.collection.delete(ids=[user_id])
        return True

    def get_default_profile(self) -> dict:
        """Return a sensible default profile for new users."""
        return {
            "risk_appetite": "moderate",
            "investment_goal": "growth",
            "investment_horizon": "medium",
            "preferred_sectors": [],
            "excluded_sectors": [],
            "preferred_analysts": [],
            "current_positions": {},
            "target_allocation": {"cash": 1.0},
            "initial_capital": 100000.0,
            "margin_requirement": 0.0,
        }
