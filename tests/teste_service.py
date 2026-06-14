


from fastapi import FastAPI, APIRouter
from contextlib import asynccontextmanager

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String
from .db import Base, engine


class UserExemple(Base):
    __tablename__ = "pessoa"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nome: Mapped[str] = mapped_column(String)
    idade: Mapped[int] = mapped_column(Integer)




router = APIRouter(prefix="/exemplo", tags=["exemplos"])

@router.get("/{item}")
def exemplo_get(item):
    return item


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(lifespan=lifespan)
        
app.include_router(router)



@app.get("/")
def read_root():
    return {"message": "API de contratos de aluguel ativa"}