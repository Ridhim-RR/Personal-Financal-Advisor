"""Base repository with common CRUD operations for SQLAlchemy models."""

from typing import TypeVar, Generic, Type, Optional, List, Dict, Any
from sqlalchemy.orm import Session

from src.db.connection import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Generic repository with standard CRUD operations."""

    def __init__(self, model: Type[ModelType], session: Session):
        self.model = model
        self.session = session

    def get(self, id: str) -> Optional[ModelType]:
        return self.session.query(self.model).filter(self.model.id == id).first()

    def get_by(self, **filters) -> Optional[ModelType]:
        return self.session.query(self.model).filter_by(**filters).first()

    def list(self, **filters) -> List[ModelType]:
        return self.session.query(self.model).filter_by(**filters).all()

    def create(self, **kwargs) -> ModelType:
        instance = self.model(**kwargs)
        self.session.add(instance)
        self.session.flush()
        return instance

    def update(self, id: str, **updates) -> Optional[ModelType]:
        instance = self.get(id)
        if instance:
            for key, value in updates.items():
                setattr(instance, key, value)
            self.session.flush()
        return instance

    def delete(self, id: str) -> bool:
        instance = self.get(id)
        if instance:
            self.session.delete(instance)
            self.session.flush()
            return True
        return False

    def upsert(self, filter_key: str, filter_value: Any, **kwargs) -> ModelType:
        """Find by filter_key=filter_value, or create."""
        instance = self.session.query(self.model).filter(
            getattr(self.model, filter_key) == filter_value
        ).first()
        if instance:
            for key, value in kwargs.items():
                setattr(instance, key, value)
            self.session.flush()
            return instance
        return self.create(**kwargs)
