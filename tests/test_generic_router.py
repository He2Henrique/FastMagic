import pytest
from fastapi import FastAPI, APIRouter
from fastapi.testclient import TestClient

from FastMagic import GenericAPI, Route
from .conftest import User, Post, UserSchema, PostSchema, make_session_gen


def test_create_route(client):
    response = client.post("/", json={"name": "Alice", "age": 30})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Alice"
    assert data["age"] == 30
    assert "id" in data


def test_list_route_empty(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == []


def test_list_route(client):
    client.post("/", json={"name": "Alice", "age": 30})
    client.post("/", json={"name": "Bob", "age": 25})
    response = client.get("/")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_by_id_route(client):
    created = client.post("/", json={"name": "Alice", "age": 30}).json()
    response = client.get(f"/{created['id']}")
    assert response.status_code == 200
    assert response.json()["name"] == "Alice"


def test_get_by_id_not_found(client):
    response = client.get("/999")
    assert response.status_code == 404


def test_update_route(client):
    created = client.post("/", json={"name": "Alice", "age": 30}).json()
    response = client.put(f"/{created['id']}", json={"name": "Alice Updated"})
    assert response.status_code == 200
    assert response.json()["name"] == "Alice Updated"
    assert response.json()["age"] == 30


def test_update_not_found(client):
    response = client.put("/999", json={"name": "Ghost"})
    assert response.status_code == 404


def test_delete_route(client):
    created = client.post("/", json={"name": "Alice", "age": 30}).json()
    response = client.delete(f"/{created['id']}")
    assert response.status_code == 204
    assert client.get(f"/{created['id']}").status_code == 404


def test_delete_not_found(client):
    response = client.delete("/999")
    assert response.status_code == 404


def test_partial_routes_only_create_and_list(db):
    router = APIRouter()
    GenericAPI(router, make_session_gen(db), User, UserSchema, routes=Route.CREATE | Route.LIST)
    app = FastAPI()
    app.include_router(router)
    c = TestClient(app)

    assert c.post("/", json={"name": "Alice", "age": 30}).status_code == 201
    assert c.get("/").status_code == 200
    assert c.get("/1").status_code == 404
    assert c.put("/1", json={"name": "x"}).status_code == 404
    assert c.delete("/1").status_code == 404


def test_route_all_minus_delete(db):
    router = APIRouter()
    GenericAPI(router, make_session_gen(db), User, UserSchema, routes=Route.ALL & ~Route.DELETE)
    app = FastAPI()
    app.include_router(router)
    c = TestClient(app)

    created = c.post("/", json={"name": "Alice", "age": 30}).json()
    assert c.delete(f"/{created['id']}").status_code == 405


def test_add_related_route(db, post_repo):
    router = APIRouter()
    api = GenericAPI(router, make_session_gen(db), User, UserSchema)
    api.add_related_route("/{item_id}/posts", "posts", PostSchema.response)

    app = FastAPI()
    app.include_router(router)
    c = TestClient(app)

    user = c.post("/", json={"name": "Alice", "age": 30}).json()
    post_repo.create({"title": "Post 1", "user_id": user["id"]})
    post_repo.create({"title": "Post 2", "user_id": user["id"]})

    response = c.get(f"/{user['id']}/posts")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_add_related_route_parent_not_found(db):
    router = APIRouter()
    api = GenericAPI(router, make_session_gen(db), User, UserSchema)
    api.add_related_route("/{item_id}/posts", "posts", PostSchema.response)

    app = FastAPI()
    app.include_router(router)
    c = TestClient(app)

    response = c.get("/999/posts")
    assert response.status_code == 404
