"""FastAPI dependency injection for services and auth."""

from typing import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from src.api.auth import decode_access_token
from src.db.connection import DatabaseManager
from src.services.conversation_memory_service import ConversationMemoryService
from src.services.memory_service import MemoryService
from src.services.portfolio_service import PortfolioService
from src.services.recommendation_service import RecommendationService
from src.services.user_profile_service import UserProfileService

_db_manager: DatabaseManager = None
_bearer = HTTPBearer(auto_error=False)


def init_db(database_url: str = None) -> DatabaseManager:
    global _db_manager
    _db_manager = DatabaseManager(database_url)
    _db_manager.connect()
    return _db_manager


def get_db() -> Generator[Session, None, None]:
    if _db_manager is None:
        init_db()
    with _db_manager.get_session() as session:
        yield session


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    session: Session = Depends(get_db),
) -> str:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    svc = UserProfileService(session)
    user = svc.get_user(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user_id


def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    session: Session = Depends(get_db),
) -> str | None:
    if credentials is None:
        return None
    return decode_access_token(credentials.credentials)


def get_user_service(session: Session = Depends(get_db)) -> UserProfileService:
    return UserProfileService(session)


def get_portfolio_service(session: Session = Depends(get_db)) -> PortfolioService:
    return PortfolioService(session)


def get_recommendation_service(session: Session = Depends(get_db)) -> RecommendationService:
    return RecommendationService(session)


def get_memory_service() -> MemoryService:
    return MemoryService()


def get_conversation_service() -> ConversationMemoryService:
    return ConversationMemoryService()


def get_alert_service(session: Session = Depends(get_db)) -> "AlertService":
    from src.services.alert_service import AlertService
    return AlertService(session)


def get_transaction_service(session: Session = Depends(get_db)) -> "TransactionService":
    from src.services.transaction_service import TransactionService
    return TransactionService(session)


def get_analysis_service(session: Session = Depends(get_db)) -> "AnalysisService":
    from src.services.analysis_service import AnalysisService
    return AnalysisService(session)
