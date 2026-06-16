from typing import Optional

from sqlalchemy.orm import Session

from src.db.models import UserORM, UserProfileORM
from src.db.repository import BaseRepository


class UserProfileService:
    """Manages user accounts and profiles in PostgreSQL.

    System of record for:
      - User identity (email, auth)
      - Risk appetite, investment goals, horizon
      - Sector preferences / exclusions
      - Account metadata (initial capital, margin)
    """

    def __init__(self, session: Session):
        self.session = session
        self.user_repo = BaseRepository(UserORM, session)
        self.profile_repo = BaseRepository(UserProfileORM, session)

    # ── User ──────────────────────────────────────────────────

    def create_user(self, email: str, password_hash: Optional[str] = None) -> UserORM:
        """Register a new user and create an empty profile."""
        user = self.user_repo.create(email=email, password_hash=password_hash)
        self.profile_repo.create(user_id=user.id)
        return user

    def get_user(self, user_id: str) -> Optional[UserORM]:
        return self.user_repo.get(user_id)

    def get_user_by_email(self, email: str) -> Optional[UserORM]:
        return self.user_repo.get_by(email=email)

    def delete_user(self, user_id: str) -> bool:
        return self.user_repo.delete(user_id)

    # ── Profile ───────────────────────────────────────────────

    def get_profile(self, user_id: str) -> Optional[UserProfileORM]:
        return self.profile_repo.get_by(user_id=user_id)

    def get_profile_dict(self, user_id: str) -> dict:
        """Return profile as a plain dict for LangGraph state."""
        profile = self.get_profile(user_id)
        if not profile:
            return self._default_profile_dict()
        return {
            "user_id": profile.user_id,
            "risk_appetite": profile.risk_appetite,
            "investment_goal": profile.investment_goal,
            "investment_horizon": profile.investment_horizon,
            "preferred_sectors": profile.preferred_sectors or [],
            "excluded_sectors": profile.excluded_sectors or [],
            "preferred_analysts": profile.preferred_analysts or [],
            "initial_capital": profile.initial_capital or 100000.0,
            "margin_requirement": profile.margin_requirement or 0.0,
        }

    def update_profile(self, user_id: str, **updates) -> Optional[UserProfileORM]:
        """Partially update user profile fields."""
        profile = self.get_profile(user_id)
        if not profile:
            return None
        return self.profile_repo.update(profile.id, **updates)

    def _default_profile_dict(self) -> dict:
        return {
            "risk_appetite": "moderate",
            "investment_goal": "growth",
            "investment_horizon": "medium",
            "preferred_sectors": [],
            "excluded_sectors": [],
            "preferred_analysts": [],
            "initial_capital": 100000.0,
            "margin_requirement": 0.0,
        }
