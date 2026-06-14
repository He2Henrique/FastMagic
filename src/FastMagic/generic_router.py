from typing import Any, TypeVar

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.orm import DeclarativeBase, Session
from generic_repo import GenericRepository

T = TypeVar("T", bound=DeclarativeBase)

class GenericAPI:

    

    def __init__(self, router: APIRouter, session: Session, model: type[T]) -> None:
        self.router = router

        self.repo = GenericRepository(session, model)

    def _not_founded_menssage(self)-> HTTPException:
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="not found",
        )
    
    def get_repo(self):
        pass

    def create_routes(self, routes: str):

        pass

    # @router.delete("/{aluguel_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_route(
        self,
        item_id: Any
    ):
        deleted_id = self.repo.delete(item_id)
        if deleted_id is None:
            raise self._not_founded_menssage()