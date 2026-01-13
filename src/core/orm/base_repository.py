import logging
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from sqlalchemy import Select, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from .base_model import BaseModel

logger = logging.getLogger(__name__)

ModelType = TypeVar("ModelType", bound=BaseModel)


class BaseRepository(Generic[ModelType]):
    model: Type[ModelType]

    def __init__(self, read_session: AsyncSession, write_session: AsyncSession):
        self._read_session = read_session
        self._write_session = write_session
        self._query: Optional[Select[Any]] = None
        self._relationships: list[str] = []
        self._include_deleted: bool = False

    @property
    def read_session(self) -> AsyncSession:
        if self._read_session is None:
            raise RuntimeError("read_session not provided to repository")
        return self._read_session

    @property
    def write_session(self) -> AsyncSession:
        if self._write_session is None:
            raise RuntimeError("write_session not provided to repository")
        return self._write_session

    def _reset_query_state(self) -> None:
        self._query = None
        self._relationships = []
        self._include_deleted = False

    def query(self) -> "BaseRepository[ModelType]":
        self._reset_query_state()
        self._query = select(self.model)

        if not self._include_deleted and hasattr(self.model, "deleted_at"):
            deleted_at = getattr(self.model, "deleted_at", None)
            if deleted_at is not None:
                self._query = self._query.where(deleted_at.is_(None))

        return self

    def with_(self, *relationships: str) -> "BaseRepository[ModelType]":
        self._relationships.extend(relationships)
        return self

    def where(self, **filters) -> "BaseRepository[ModelType]":
        if self._query is None:
            self.query()
        if self._query is not None:
            for key, value in filters.items():
                if not self._validate_column_name(key):
                    raise ValueError(
                        f"Invalid column name: '{key}' on {self.model.__name__}"
                    )

                column = getattr(self.model, key)
                self._query = self._query.where(column == value)
        return self

    def _validate_column_name(self, column_name: str) -> bool:
        if column_name.startswith("_"):
            logger.warning(
                f"Attempted to query private attribute '{column_name}' on {self.model.__name__}"
            )
            return False

        if column_name.startswith("__"):
            logger.warning(
                f"Attempted to query magic method '{column_name}' on {self.model.__name__}"
            )
            return False

        if not hasattr(self.model, column_name):
            logger.warning(
                f"Column '{column_name}' does not exist on {self.model.__name__}"
            )
            return False

        if column_name not in self.model.__table__.columns:
            logger.debug(
                f"'{column_name}' is not a direct column on {self.model.__name__} "
                f"(might be relationship or property)"
            )

        return True

    def where_in(self, column: str, values: List[Any]) -> "BaseRepository[ModelType]":
        if self._query is None:
            self.query()
        if self._query is not None:
            col = getattr(self.model, column)
            self._query = self._query.where(col.in_(values))
        return self

    def where_not_null(self, column: str) -> "BaseRepository[ModelType]":
        if self._query is None:
            self.query()
        if self._query is not None:
            col = getattr(self.model, column)
            self._query = self._query.where(col.is_not(None))
        return self

    def where_null(self, column: str) -> "BaseRepository[ModelType]":
        if self._query is None:
            self.query()
        if self._query is not None:
            col = getattr(self.model, column)
            self._query = self._query.where(col.is_(None))
        return self

    def order_by(self, column: str, order: str = "asc") -> "BaseRepository[ModelType]":
        if self._query is None:
            self.query()
        if self._query is not None:
            if not self._validate_column_name(column):
                raise ValueError(
                    f"Invalid column name: '{column}' on {self.model.__name__}"
                )
            col = getattr(self.model, column)
            order_lower = order.lower()
            if order_lower == "desc":
                self._query = self._query.order_by(col.desc())
            else:
                self._query = self._query.order_by(col.asc())
        return self

    def limit(self, limit: int) -> "BaseRepository[ModelType]":
        if self._query is None:
            self.query()
        if self._query is not None:
            self._query = self._query.limit(limit)
        return self

    def offset(self, offset: int) -> "BaseRepository[ModelType]":
        if self._query is None:
            self.query()
        if self._query is not None:
            self._query = self._query.offset(offset)
        return self

    def _apply_relationships(self, query: Select) -> Select:
        for rel in self._relationships:
            if "." in rel:
                parts = rel.split(".")
                option = selectinload(getattr(self.model, parts[0]))
                for part in parts[1:]:
                    option = option.selectinload(getattr(self.model, part))
                query = query.options(option)
            else:
                query = query.options(selectinload(getattr(self.model, rel)))
        return query

    async def all(self) -> List[ModelType]:
        if self._query is None:
            self.query()
        if self._query is None:
            raise RuntimeError("Query not initialized")
        query = self._apply_relationships(self._query)
        result = await self.read_session.execute(query)
        data = list(result.scalars().all())
        self._reset_query_state()
        return data

    async def first(self) -> Optional[ModelType]:
        if self._query is None:
            self.query()
        if self._query is None:
            raise RuntimeError("Query not initialized")
        query = self._apply_relationships(self._query.limit(1))
        result = await self.read_session.execute(query)
        data = result.scalars().first()
        self._reset_query_state()
        return data

    async def get(self, id: Any) -> Optional[ModelType]:
        primary_key = self.model.__table__.primary_key
        primary_key_columns = list(getattr(primary_key, "columns", []))

        if len(primary_key_columns) == 1:
            pk_column = primary_key_columns[0]
            query = select(self.model).where(pk_column == id)
        else:
            if not isinstance(id, (tuple, dict)):
                raise ValueError(
                    f"Model {self.model.__name__} has composite primary key. "
                    "id must be tuple or dict."
                )

            if isinstance(id, dict):
                conditions = [col == id[col.name] for col in primary_key_columns]
            else:
                conditions = [col == id[i] for i, col in enumerate(primary_key_columns)]

            query = select(self.model).where(*conditions)

        if not self._include_deleted and hasattr(self.model, "deleted_at"):
            deleted_at = getattr(self.model, "deleted_at", None)
            if deleted_at is not None:
                query = query.where(deleted_at.is_(None))

        query = self._apply_relationships(query)
        result = await self.read_session.execute(query)
        return result.scalars().first()

    async def count(self) -> int:
        if self._query is None:
            self.query()
        if self._query is None:
            raise RuntimeError("Query not initialized")
        count_query = select(func.count()).select_from(self._query.subquery())
        result = await self.read_session.execute(count_query)
        count = result.scalar_one()
        self._reset_query_state()
        return count

    async def exists(self) -> bool:
        if self._query is None:
            self.query()
        if self._query is None:
            raise RuntimeError("Query not initialized")

        try:
            query = self._apply_relationships(self._query.limit(1))
            result = await self.read_session.execute(query)
            return result.scalars().first() is not None
        finally:
            self._reset_query_state()

    async def paginate(self, page: int = 1, per_page: int = 15) -> Dict[str, Any]:
        if page < 1:
            page = 1

        if self._query is None:
            self.query()
        if self._query is None:
            raise RuntimeError("Query not initialized")

        count_query = select(func.count()).select_from(self._query.subquery())
        count_result = await self.read_session.execute(count_query)
        total = count_result.scalar_one()

        offset = (page - 1) * per_page
        total_pages = (total + per_page - 1) // per_page

        data_query = self._apply_relationships(
            self._query.offset(offset).limit(per_page)
        )
        data_result = await self.read_session.execute(data_query)
        data = list(data_result.scalars().all())
        self._reset_query_state()

        return {
            "data": data,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        }

    async def create(self, data: Dict[str, Any]) -> ModelType:
        instance = self.model(**data)
        self.write_session.add(instance)
        await self.write_session.flush()
        await self.write_session.refresh(instance)
        return instance

    async def update(self, id: Any, data: Dict[str, Any]) -> Optional[ModelType]:
        primary_key = self.model.__table__.primary_key
        primary_key_columns = list(getattr(primary_key, "columns", []))

        if len(primary_key_columns) == 1:
            pk_column = primary_key_columns[0]
            query = select(self.model).where(pk_column == id)
        else:
            if not isinstance(id, (tuple, dict)):
                raise ValueError(
                    f"Model {self.model.__name__} has composite primary key. "
                    "id must be tuple or dict."
                )

            if isinstance(id, dict):
                conditions = [col == id[col.name] for col in primary_key_columns]
            else:
                conditions = [col == id[i] for i, col in enumerate(primary_key_columns)]

            query = select(self.model).where(*conditions)

        if not self._include_deleted and hasattr(self.model, "deleted_at"):
            deleted_at = getattr(self.model, "deleted_at", None)
            if deleted_at is not None:
                query = query.where(deleted_at.is_(None))

        result = await self.write_session.execute(query)
        instance = result.scalars().first()

        if not instance:
            return None

        for key, value in data.items():
            setattr(instance, key, value)

        await self.write_session.flush()
        await self.write_session.refresh(instance)
        return instance

    async def delete(self, id: Any) -> bool:
        primary_key = self.model.__table__.primary_key
        primary_key_columns = list(getattr(primary_key, "columns", []))

        if len(primary_key_columns) == 1:
            pk_column = primary_key_columns[0]
            query = select(self.model).where(pk_column == id)
        else:
            if not isinstance(id, (tuple, dict)):
                raise ValueError(
                    f"Model {self.model.__name__} has composite primary key. "
                    "id must be tuple or dict."
                )

            if isinstance(id, dict):
                conditions = [col == id[col.name] for col in primary_key_columns]
            else:
                conditions = [col == id[i] for i, col in enumerate(primary_key_columns)]

            query = select(self.model).where(*conditions)

        if not self._include_deleted and hasattr(self.model, "deleted_at"):
            deleted_at = getattr(self.model, "deleted_at", None)
            if deleted_at is not None:
                query = query.where(deleted_at.is_(None))

        result = await self.write_session.execute(query)
        instance = result.scalars().first()

        if not instance:
            return False

        await self.write_session.delete(instance)
        await self.write_session.flush()
        return True

    async def bulk_create(
        self, data_list: List[Dict[str, Any]], refresh: bool = False
    ) -> List[ModelType]:
        instances = [self.model(**data) for data in data_list]
        self.write_session.add_all(instances)
        await self.write_session.flush()

        if refresh:
            for instance in instances:
                await self.write_session.refresh(instance)

        return instances

    async def bulk_update(self, filters: Dict[str, Any], data: Dict[str, Any]) -> int:
        for key in filters.keys():
            if not self._validate_column_name(key):
                raise ValueError(
                    f"Invalid column name in filters: '{key}' on {self.model.__name__}"
                )

        for key in data.keys():
            if not self._validate_column_name(key):
                raise ValueError(
                    f"Invalid column name in data: '{key}' on {self.model.__name__}"
                )

        stmt = (
            update(self.model)
            .where(*[getattr(self.model, k) == v for k, v in filters.items()])
            .values(**data)
        )

        result = await self.write_session.execute(stmt)
        await self.write_session.flush()
        rowcount = getattr(result, "rowcount", None)
        return int(rowcount) if rowcount is not None else 0

    async def bulk_delete(self, filters: Dict[str, Any]) -> int:
        for key in filters.keys():
            if not self._validate_column_name(key):
                raise ValueError(
                    f"Invalid column name in filters: '{key}' on {self.model.__name__}"
                )

        stmt = delete(self.model).where(
            *[getattr(self.model, k) == v for k, v in filters.items()]
        )

        result = await self.write_session.execute(stmt)
        await self.write_session.flush()
        rowcount = getattr(result, "rowcount", None)
        return int(rowcount) if rowcount is not None else 0

    async def soft_delete(self, id: Any) -> bool:
        if not hasattr(self.model, "deleted_at"):
            raise AttributeError(f"{self.model.__name__} does not support soft delete")

        return await self.update(id, {"deleted_at": func.now()}) is not None

    def with_trashed(self) -> "BaseRepository[ModelType]":
        if not hasattr(self.model, "deleted_at"):
            logger.warning(
                f"Model {self.model.__name__} does not support soft delete. "
                f"with_trashed() has no effect."
            )
            return self

        self._include_deleted = True

        if self._query is not None:
            logger.debug(
                "with_trashed() called after query() - rebuilding query. "
                "Consider calling with_trashed() before query() for better control."
            )

        return self

    def only_trashed(self) -> "BaseRepository[ModelType]":
        if not hasattr(self.model, "deleted_at"):
            raise AttributeError(f"{self.model.__name__} does not support soft delete")

        self._reset_query_state()
        deleted_at = getattr(self.model, "deleted_at", None)
        if deleted_at is not None:
            self._query = select(self.model).where(deleted_at.is_not(None))
        self._include_deleted = True
        return self

    async def restore(self, id: Any) -> bool:
        if not hasattr(self.model, "deleted_at"):
            raise AttributeError(f"{self.model.__name__} does not support soft delete")

        return await self.update(id, {"deleted_at": None}) is not None
