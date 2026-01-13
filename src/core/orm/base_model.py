import re
from datetime import datetime
from typing import Any, Dict, Optional, Set

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, declared_attr, mapped_column
from src.core.configs import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class SoftDeleteMixin:
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


class BaseModel(Base, TimestampMixin):
    __abstract__ = True

    @declared_attr.directive
    def __tablename__(cls) -> str:
        name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", cls.__name__)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", name).lower()

    def to_dict(
        self, exclude: Optional[Set[str]] = None, include_relationships: bool = False
    ) -> Dict[str, Any]:
        if exclude is None:
            exclude = set()

        from datetime import datetime, date
        from uuid import UUID

        data = {}
        for column in self.__table__.columns:
            if column.name in exclude:
                continue

            value = getattr(self, column.name, None)

            if isinstance(value, datetime):
                value = value.isoformat()
            elif isinstance(value, date):
                value = value.isoformat()
            elif isinstance(value, UUID):
                value = str(value)

            data[column.name] = value

        if include_relationships:
            for rel_name, relationship in self.__mapper__.relationships.items():
                if rel_name in exclude:
                    continue

                try:
                    rel_value = getattr(self, rel_name)
                    if rel_value is None:
                        data[rel_name] = None
                    elif hasattr(rel_value, "__iter__") and not isinstance(
                        rel_value, str
                    ):
                        data[rel_name] = [
                            (
                                item.to_dict(
                                    exclude=exclude, include_relationships=False
                                )
                                if hasattr(item, "to_dict")
                                else str(item)
                            )
                            for item in rel_value
                        ]
                    else:
                        if hasattr(rel_value, "to_dict"):
                            data[rel_name] = rel_value.to_dict(
                                exclude=exclude, include_relationships=False
                            )
                        else:
                            data[rel_name] = str(rel_value)
                except Exception:
                    pass

        return data

    def __repr__(self) -> str:
        pk = getattr(self, "id", None)
        return f"<{self.__class__.__name__}(id={pk})>"
