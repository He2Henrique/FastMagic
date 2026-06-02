from typing import Any, TypeVar, Generic, Type
from sqlalchemy import select, update, inspect
from sqlalchemy.orm import Session, selectinload, DeclarativeBase

T = TypeVar("T", bound=DeclarativeBase)

class GenericRepository(Generic[T]):

    def __init__(self, db: Session, model: Type[T]) -> None:
        self.db = db
        self.model = model

    def _pk_column(self):
        return inspect(self.model).mapper.primary_key[0]

    def list_records(self) -> list[T]:
        stmt = select(self.model)

        return list(self.db.execute(stmt).scalars().all())

    def get_by_id(self, id_to_search)-> T | None:
        return self.db.get(self.model, id_to_search) 

    def get_related_records(
        self,
        parent_id: Any,
        relationship_name: str,
        child_relationships: tuple[str, ...] = (),
    ) -> list[Any] | None:
        mapper = inspect(self.model)
        if relationship_name not in mapper.relationships:
            raise ValueError(f"{relationship_name} nao e um relacionamento de {self.model.__name__}.")

        relationship_attr = getattr(self.model, relationship_name)
        relationship = mapper.relationships[relationship_name]
        child_model = relationship.mapper.class_

        if child_relationships:
            child_mapper = inspect(child_model)
            for child_relationship in child_relationships:
                if child_relationship not in child_mapper.relationships:
                    raise ValueError(
                        f"{child_relationship} nao e um relacionamento de {child_model.__name__}."
                    )

            options = [
                selectinload(relationship_attr).selectinload(getattr(child_model, child_relationship))
                for child_relationship in child_relationships
            ]
        else:
            options = [selectinload(relationship_attr)]

        stmt = (
            select(self.model)
            .options(*options)
            .where(self._pk_column() == parent_id)
        )

        parent = self.db.execute(stmt).scalar_one_or_none()
        if parent is None:
            return None

        related_records = getattr(parent, relationship_name)
        if relationship.uselist:
            return list(related_records)

        return [related_records] if related_records is not None else []
    
    def create(self, dictnary: dict) -> T:
        record = self.model(**dictnary)

        self.db.add(record)

        self.db.commit()

        self.db.refresh(record)

        return record

    def delete(self, id_to_delete) -> int | None:
        record = self.get_by_id(id_to_delete)

        if(not record):
            return None

        self.db.delete(record)
        self.db.commit()
        
        return id_to_delete
    
    def update(self, id_to_update, **data_to_update) -> T | None:

        pk = self._pk_column()

        stmt = update(self.model).where(pk == id_to_update).values(**data_to_update).returning(self.model)

        result = self.db.execute(stmt)
        self.db.commit()
        return result.scalar_one_or_none()
           



