import pytest
from fastapi import FastAPI, APIRouter
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, Integer, String, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker, Mapped, mapped_column, relationship
from sqlalchemy.pool import StaticPool

from FastMagic import SchemaModel, GenericRepository, GenericAPI, Route

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    age: Mapped[int] = mapped_column(Integer)
    posts: Mapped[list["Post"]] = relationship("Post", back_populates="user")


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    user: Mapped["User"] = relationship("User", back_populates="posts")


class UserSchema(SchemaModel):
    sa_model = User


class PostSchema(SchemaModel):
    sa_model = Post


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def db(reset_db) -> Session:
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def user_repo(db):
    return GenericRepository(db, User)


@pytest.fixture
def post_repo(db):
    return GenericRepository(db, Post)


def make_session_gen(session: Session):
    yield session


@pytest.fixture
def client(db):
    router = APIRouter()
    GenericAPI(router, make_session_gen(db), User, UserSchema)
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)
