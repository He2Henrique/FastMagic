from datetime import date, datetime
from enum import auto, Flag
from typing import Any, TypeVar, Generator

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import inspect
from sqlalchemy.orm import DeclarativeBase, Session

from .generic_repo import GenericRepository, split_filter_key
from .schema_model import SchemaModel

T = TypeVar("T", bound=DeclarativeBase)

_TRUE_VALUES = {"1", "true", "yes", "on"}


def _cast_filter_value(model: type, key: str, raw: str) -> Any:
    name, _ = split_filter_key(key)
    columns = inspect(model).mapper.columns
    if name not in columns:
        return raw

    python_type = columns[name].type.python_type
    if python_type is bool:
        return raw.strip().lower() in _TRUE_VALUES
    if python_type is datetime:
        return datetime.fromisoformat(raw)
    if python_type is date:
        return date.fromisoformat(raw)
    if python_type in (int, float):
        return python_type(raw)
    return raw


class Route(Flag):
    CREATE = auto()
    LIST = auto()
    GET = auto()
    UPDATE = auto()
    DELETE = auto()
    ALL = CREATE | LIST | GET | UPDATE | DELETE


class GenericAPI:
    def __init__(
        self,
        router: APIRouter,
        gen_session: Generator[Session, None, None],
        model: type[T],
        schema: type[SchemaModel],
        routes: Route = Route.ALL,
    ) -> None:
        self.router = router
        self.repo = GenericRepository(next(gen_session), model)

        self._register_crud_routes(schema.request, schema.update, schema.response, routes)

    def _register_crud_routes(
        self,
        request_schema: type[BaseModel],
        update_schema: type[BaseModel],
        response_schema: type[BaseModel],
        routes: Route,
    ) -> None:
        repo = self.repo
        not_found = self._not_found

        if Route.CREATE in routes:
            def create(payload):
                return repo.create(payload.model_dump())
            create.__annotations__.update({"payload": request_schema, "return": response_schema})
            self.router.post("", status_code=status.HTTP_201_CREATED)(create)

        if Route.LIST in routes:
            def list_all(request: Request, order_by: str | None = None):
                try:
                    filters = {
                        k: _cast_filter_value(repo.model, k, v)
                        for k, v in request.query_params.items()
                        if k != "order_by"
                    }
                    return repo.list_records(
                        order_by=order_by.split(",") if order_by else None,
                        filters=filters or None,
                    )
                except ValueError as exc:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
            list_all.__annotations__["return"] = list[response_schema]
            self.router.get("")(list_all)

        if Route.GET in routes:
            def get_by_id(item_id: Any):
                item = repo.get_by_id(item_id)
                if item is None:
                    raise not_found()
                return item
            get_by_id.__annotations__["return"] = response_schema
            self.router.get("/{item_id}")(get_by_id)

        if Route.UPDATE in routes:
            def update(item_id: Any, payload):
                data = payload.model_dump(exclude_unset=True)
                item = repo.update(item_id, **data) if data else repo.get_by_id(item_id)
                if item is None:
                    raise not_found()
                return item
            update.__annotations__.update({"payload": update_schema, "return": response_schema})
            self.router.patch("/{item_id}")(update)

        if Route.DELETE in routes:
            def delete(item_id: Any) -> None:
                if repo.delete(item_id) is None:
                    raise not_found()
            self.router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)(delete)

    def add_related_route(
        self,
        path: str,
        relationship_name: str,
        response_schema: type[BaseModel],
        child_relationships: tuple[str, ...] = (),
    ) -> None:
        repo = self.repo
        not_found = self._not_found

        def get_related(item_id: Any):
            records = repo.get_related_records(item_id, relationship_name, child_relationships)
            if records is None:
                raise not_found()
            return records
        get_related.__annotations__["return"] = list[response_schema]

        self.router.get(path)(get_related)

    def _not_found(self) -> HTTPException:
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="not found",
        )
