
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from sqlalchemy import Select, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from .base_model import BaseModel

ModelType = TypeVar("ModelType", bound=BaseModel)


class BaseRepository(Generic[ModelType]):
    """
    Base repository.
    
    Usage:
        class UserRepository(BaseRepository[User]):
            model = User
        
        # Use in service
        repo = UserRepository(session)
        users = await repo.all()
    """
    
    model: Type[ModelType]

    def __init__(self, session: AsyncSession):
        self.session = session
        self._query: Optional[Select[Any]] = None
        self._relationships: list[str] = []
    
    def query(self) -> "BaseRepository[ModelType]":
        """Start a new query."""
        self._query = select(self.model)
        return self
    
    def with_(self, *relationships: str) -> "BaseRepository[ModelType]":
        """
        Eager load relationships (prevents N+1 queries).
        
        Usage:
            users = await repo.query().with_('posts', 'profile').all()
        """
        self._relationships.extend(relationships)
        return self
    
    def where(self, **filters) -> "BaseRepository[ModelType]":
        """
        Add WHERE conditions.
        
        Usage:
            users = await repo.query().where(status='active', age=25).all()
        """
        if self._query is None:
            self.query()
        if self._query is not None:
            for key, value in filters.items():
                column = getattr(self.model, key)
                self._query = self._query.where(column == value)
        return self
    
    def where_in(self, column: str, values: List[Any]) -> "BaseRepository[ModelType]":
        """
        Add WHERE IN condition.
        
        Usage:
            users = await repo.query().where_in('id', [1, 2, 3]).all()
        """
        if self._query is None:
            self.query()
        if self._query is not None:
            col = getattr(self.model, column)
            self._query = self._query.where(col.in_(values))
        return self
    
    def where_not_null(self, column: str) -> "BaseRepository[ModelType]":
        """Add WHERE column IS NOT NULL condition."""
        if self._query is None:
            self.query()
        if self._query is not None:
            col = getattr(self.model, column)
            self._query = self._query.where(col.is_not(None))
        return self
    
    def where_null(self, column: str) -> "BaseRepository[ModelType]":
        """Add WHERE column IS NULL condition."""
        if self._query is None:
            self.query()
        if self._query is not None:
            col = getattr(self.model, column)
            self._query = self._query.where(col.is_(None))
        return self
    
    def order_by(self, column: str, desc: bool = False) -> "BaseRepository[ModelType]":
        """
        Add ORDER BY clause.
        
        Usage:
            users = await repo.query().order_by('created_at', desc=True).all()
        """
        if self._query is None:
            self.query()
        if self._query is not None:
            col = getattr(self.model, column)
            self._query = self._query.order_by(col.desc() if desc else col.asc())
        return self
    
    def limit(self, limit: int) -> "BaseRepository[ModelType]":
        """Add LIMIT clause."""
        if self._query is None:
            self.query()
        if self._query is not None:
            self._query = self._query.limit(limit)
        return self
    
    def offset(self, offset: int) -> "BaseRepository[ModelType]":
        """Add OFFSET clause."""
        if self._query is None:
            self.query()
        if self._query is not None:
            self._query = self._query.offset(offset)
        return self

    
    def _apply_relationships(self, query: Select) -> Select:
        """
        Apply eager loading for relationships.

        Uses selectinload for better performance with 1-to-many relationships.
        selectinload issues a separate SELECT for related objects, avoiding
        cartesian products that can occur with joinedload.
        """
        for rel in self._relationships:
            if '.' in rel:
                # Nested relationship: user.posts.comments
                parts = rel.split('.')
                # Use selectinload consistently for all levels
                option = selectinload(getattr(self.model, parts[0]))
                for part in parts[1:]:
                    # Chain selectinload for nested relationships
                    option = option.selectinload(getattr(self.model, part))
                query = query.options(option)
            else:
                # Simple relationship - selectinload is optimal for collections
                query = query.options(selectinload(getattr(self.model, rel)))
        return query
    
    async def all(self) -> List[ModelType]:
        """
        Execute query and return all results.
        
        Usage:
            users = await repo.query().where(status='active').all()
        """
        if self._query is None:
            self.query()
        if self._query is None:
            raise RuntimeError("Query not initialized")
        query = self._apply_relationships(self._query)
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def first(self) -> Optional[ModelType]:
        """
        Execute query and return first result.
        
        Usage:
            user = await repo.query().where(email='test@example.com').first()
        """
        if self._query is None:
            self.query()
        if self._query is None:
            raise RuntimeError("Query not initialized")
        query = self._apply_relationships(self._query.limit(1))
        result = await self.session.execute(query)
        return result.scalars().first()
    
    async def get(self, id: Any) -> Optional[ModelType]:
        """
        Get record by ID with eager loading.
        
        Usage:
            user = await repo.with_('posts').get(1)
        """
        # Assume model has 'id' attribute for primary key lookup
        query = select(self.model).where(getattr(self.model, "id") == id)
        query = self._apply_relationships(query)
        result = await self.session.execute(query)
        return result.scalars().first()
    
    async def count(self) -> int:
        """
        Count records matching query.
        
        Usage:
            count = await repo.query().where(status='active').count()
        """
        if self._query is None:
            self.query()
        if self._query is None:
            raise RuntimeError("Query not initialized")
        # Create count query
        count_query = select(func.count()).select_from(self._query.subquery())
        result = await self.session.execute(count_query)
        return result.scalar_one()
    
    async def exists(self) -> bool:
        """
        Check if any record exists matching query.
        
        Usage:
            exists = await repo.query().where(email='test@example.com').exists()
        """
        count = await self.count()
        return count > 0
    
    async def paginate(
        self, 
        page: int = 1, 
        per_page: int = 15
    ) -> Dict[str, Any]:
        """
        Paginate results.
        
        Usage:
            result = await repo.query().where(status='active').paginate(page=2, per_page=10)
            # Returns: {
            #     'data': [...],
            #     'total': 100,
            #     'page': 2,
            #     'per_page': 10,
            #     'total_pages': 10
            # }
        """
        if page < 1:
            page = 1
        
        # Get total count
        total = await self.count()
        
        # Calculate pagination
        offset = (page - 1) * per_page
        total_pages = (total + per_page - 1) // per_page
        
        # Get data
        data = await self.offset(offset).limit(per_page).all()
        
        return {
            'data': data,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_prev': page > 1,
        }
    
    async def create(self, data: Dict[str, Any]) -> ModelType:
        """
        Create new record.
        
        Usage:
            user = await repo.create({'name': 'John', 'email': 'john@example.com'})
        """
        instance = self.model(**data)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance
    
    async def update(self, id: Any, data: Dict[str, Any]) -> Optional[ModelType]:
        """
        Update record by ID.
        
        Usage:
            user = await repo.update(1, {'name': 'John Doe'})
        """
        instance = await self.get(id)
        if not instance:
            return None
        
        for key, value in data.items():
            setattr(instance, key, value)
        
        await self.session.flush()
        await self.session.refresh(instance)
        return instance
    
    async def delete(self, id: Any) -> bool:
        """
        Delete record by ID.
        
        Usage:
            success = await repo.delete(1)
        """
        instance = await self.get(id)
        if not instance:
            return False
        
        await self.session.delete(instance)
        await self.session.flush()
        return True
    
    async def bulk_create(self, data_list: List[Dict[str, Any]]) -> List[ModelType]:
        """
        Bulk create records.
        
        Usage:
            users = await repo.bulk_create([
                {'name': 'John', 'email': 'john@example.com'},
                {'name': 'Jane', 'email': 'jane@example.com'}
            ])
        """
        instances = [self.model(**data) for data in data_list]
        self.session.add_all(instances)
        await self.session.flush()
        
        for instance in instances:
            await self.session.refresh(instance)
        
        return instances
    
    async def bulk_update(self, filters: Dict[str, Any], data: Dict[str, Any]) -> int:
        """
        Bulk update records matching filters.
        
        Usage:
            count = await repo.bulk_update(
                {'status': 'pending'},
                {'status': 'active'}
            )
        """
        stmt = update(self.model).where(
            *[getattr(self.model, k) == v for k, v in filters.items()]
        ).values(**data)
        
        result = await self.session.execute(stmt)
        await self.session.flush()
        # SQLAlchemy 2.x: rowcount is on result, but type checker may not see it
        rowcount = getattr(result, "rowcount", None)
        return int(rowcount) if rowcount is not None else 0
    
    async def bulk_delete(self, filters: Dict[str, Any]) -> int:
        """
        Bulk delete records matching filters.
        
        Usage:
            count = await repo.bulk_delete({'status': 'inactive'})
        """
        stmt = delete(self.model).where(
            *[getattr(self.model, k) == v for k, v in filters.items()]
        )
        
        result = await self.session.execute(stmt)
        await self.session.flush()
        rowcount = getattr(result, "rowcount", None)
        return int(rowcount) if rowcount is not None else 0
    
    async def soft_delete(self, id: Any) -> bool:
        """
        Soft delete record (if model has deleted_at).
        
        Usage:
            success = await repo.soft_delete(1)
        """
        if not hasattr(self.model, 'deleted_at'):
            raise AttributeError(f"{self.model.__name__} does not support soft delete")
        
        return await self.update(id, {'deleted_at': func.now()}) is not None
    
    def with_trashed(self) -> "BaseRepository[ModelType]":
        """Include soft deleted records in query."""
        # Query will include deleted records
        return self
    
    def only_trashed(self) -> "BaseRepository[ModelType]":
        """Only get soft deleted records."""
        if hasattr(self.model, 'deleted_at'):
            return self.where_not_null('deleted_at')
        return self
    
    async def restore(self, id: Any) -> bool:
        """Restore soft deleted record."""
        if not hasattr(self.model, 'deleted_at'):
            raise AttributeError(f"{self.model.__name__} does not support soft delete")
        
        return await self.update(id, {'deleted_at': None}) is not None