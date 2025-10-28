"""Reusable CRUD helpers built on SQLAlchemy ORM."""

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Generic CRUD operations for a SQLAlchemy model."""

    def __init__(self, model: Type[ModelType]):
        self.model = model

    def get(self, db: Session, obj_id: Any) -> Optional[ModelType]:
        return db.get(self.model, obj_id)

    def list(self, db: Session, *, skip: int = 0, limit: int = 100) -> List[ModelType]:
        stmt = select(self.model).offset(skip).limit(limit)
        return list(db.execute(stmt).scalars().all())

    def create(self, db: Session, *, obj_in: CreateSchemaType) -> ModelType:
        obj_data = _model_to_dict(obj_in)
        db_obj = self.model(**obj_data)  # type: ignore[arg-type]
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self,
        db: Session,
        *,
        db_obj: ModelType,
        obj_in: UpdateSchemaType | Dict[str, Any],
    ) -> ModelType:
        if isinstance(obj_in, BaseModel):
            update_data = _model_to_dict(obj_in)
        else:
            update_data = obj_in

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, db_obj: ModelType) -> ModelType:
        db.delete(db_obj)
        db.commit()
        return db_obj


def _model_to_dict(model: BaseModel) -> Dict[str, Any]:
    """Support both Pydantic v1 and v2 for dumping models."""
    if hasattr(model, "model_dump"):
        return model.model_dump(exclude_unset=True)  # type: ignore[call-arg]
    return model.dict(exclude_unset=True)
