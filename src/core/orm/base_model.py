import re
from datetime import datetime, date
from typing import Any, Dict, Optional, Set
from collections.abc import Iterable
from uuid import UUID
from sqlalchemy import DateTime, func
from sqlalchemy.orm import declared_attr, mapped_column
from src.core.configs import Base


class BaseModel(Base):
    __abstract__ = True
    __created_at__ = True
    __updated_at__ = True
    __soft_delete__ = False

    @declared_attr.directive
    def __tablename__(cls) -> str:
        name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", cls.__name__)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", name).lower()

    @declared_attr
    def created_at(cls):
        if cls.__created_at__:
            return mapped_column(
                DateTime(timezone=True),
                nullable=False,
                server_default=func.now(),
            )

    @declared_attr
    def updated_at(cls):
        if cls.__updated_at__:
            return mapped_column(
                DateTime(timezone=True),
                nullable=False,
                server_default=func.now(),
                onupdate=func.now(),
            )

    @declared_attr
    def deleted_at(cls):
        if cls.__soft_delete__:
            return mapped_column(
                DateTime(timezone=True),
                nullable=True,
            )

    @property
    def is_deleted(self) -> bool:
        return bool(getattr(self, "deleted_at", None))

    def to_dict(
        self,
        exclude: Optional[Set[str]] = None,
        include_relationships: bool = False,
    ) -> Dict[str, Any]:
        if exclude is None:
            exclude = set()

        data: Dict[str, Any] = {}

        for column in self.__table__.columns:
            if column.name in exclude:
                continue

            value = getattr(self, column.name, None)

            if isinstance(value, (datetime, date)):
                value = value.isoformat()
            elif isinstance(value, UUID):
                value = str(value)

            data[column.name] = value

        if include_relationships:
            for rel_name in self.__mapper__.relationships.keys():
                if rel_name in exclude:
                    continue

                try:
                    rel_value = getattr(self, rel_name, None)

                    if rel_value is None:
                        data[rel_name] = None
                    elif isinstance(rel_value, Iterable) and not isinstance(
                        rel_value, (str, bytes)
                    ):
                        data[rel_name] = [
                            (
                                item.to_dict(exclude=exclude)
                                if hasattr(item, "to_dict")
                                else str(item)
                            )
                            for item in rel_value
                        ]
                    else:
                        data[rel_name] = (
                            rel_value.to_dict(exclude=exclude)
                            if hasattr(rel_value, "to_dict")
                            else str(rel_value)
                        )
                except Exception:
                    pass

        return data

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={getattr(self, 'id', None)})>"
