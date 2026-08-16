from datetime import date

import pytest
from .conftest import User, Post, UserSchema


def test_create(user_repo):
    user = user_repo.create({"name": "Alice", "age": 30})
    assert user.id is not None
    assert user.name == "Alice"
    assert user.age == 30


def test_list_records_empty(user_repo):
    assert user_repo.list_records() == []


def test_list_records(user_repo):
    user_repo.create({"name": "Alice", "age": 30})
    user_repo.create({"name": "Bob", "age": 25})
    records = user_repo.list_records()
    assert len(records) == 2


def test_list_records_order_by(user_repo):
    user_repo.create({"name": "Bob", "age": 25})
    user_repo.create({"name": "Alice", "age": 30})
    records = user_repo.list_records(order_by="name")
    assert [r.name for r in records] == ["Alice", "Bob"]


def test_list_records_order_by_descending(user_repo):
    user_repo.create({"name": "Alice", "age": 30})
    user_repo.create({"name": "Bob", "age": 25})
    records = user_repo.list_records(order_by="-age")
    assert [r.name for r in records] == ["Alice", "Bob"]


def test_list_records_order_by_invalid_column(user_repo):
    with pytest.raises(ValueError, match="nao e uma coluna"):
        user_repo.list_records(order_by="nonexistent")


def test_list_records_filters(user_repo):
    user_repo.create({"name": "Alice", "age": 30})
    user_repo.create({"name": "Bob", "age": 25})
    records = user_repo.list_records(filters={"name": "Alice"})
    assert len(records) == 1
    assert records[0].name == "Alice"


def test_list_records_filters_invalid_column(user_repo):
    with pytest.raises(ValueError, match="nao e uma coluna"):
        user_repo.list_records(filters={"nonexistent": "x"})


def test_list_records_filters_gte(user_repo):
    user_repo.create({"name": "Alice", "age": 30})
    user_repo.create({"name": "Bob", "age": 25})
    records = user_repo.list_records(filters={"age__gte": 30})
    assert [r.name for r in records] == ["Alice"]


def test_list_records_filters_lte(user_repo):
    user_repo.create({"name": "Alice", "age": 30})
    user_repo.create({"name": "Bob", "age": 25})
    records = user_repo.list_records(filters={"age__lte": 25})
    assert [r.name for r in records] == ["Bob"]


def test_list_records_filters_gt_and_lt(user_repo):
    user_repo.create({"name": "Alice", "age": 30})
    user_repo.create({"name": "Bob", "age": 25})
    user_repo.create({"name": "Carol", "age": 40})
    assert [r.name for r in user_repo.list_records(filters={"age__gt": 30})] == ["Carol"]
    assert [r.name for r in user_repo.list_records(filters={"age__lt": 30})] == ["Bob"]


def test_list_records_filters_date(user_repo):
    user_repo.create({"name": "Alice", "age": 30, "birthday": date(1996, 1, 1)})
    user_repo.create({"name": "Bob", "age": 25, "birthday": date(2001, 6, 15)})
    records = user_repo.list_records(filters={"birthday__gte": date(2000, 1, 1)})
    assert [r.name for r in records] == ["Bob"]


def test_get_by_id(user_repo):
    created = user_repo.create({"name": "Alice", "age": 30})
    found = user_repo.get_by_id(created.id)
    assert found is not None
    assert found.name == "Alice"


def test_get_by_id_not_found(user_repo):
    assert user_repo.get_by_id(999) is None


def test_update(user_repo):
    user = user_repo.create({"name": "Alice", "age": 30})
    updated = user_repo.update(user.id, name="Alice Updated")
    assert updated is not None
    assert updated.name == "Alice Updated"
    assert updated.age == 30


def test_update_not_found(user_repo):
    result = user_repo.update(999, name="Ghost")
    assert result is None


def test_delete(user_repo):
    user = user_repo.create({"name": "Alice", "age": 30})
    deleted_id = user_repo.delete(user.id)
    assert deleted_id == user.id
    assert user_repo.get_by_id(user.id) is None


def test_delete_not_found(user_repo):
    assert user_repo.delete(999) is None


def test_get_related_records(user_repo, post_repo):
    user = user_repo.create({"name": "Alice", "age": 30})
    post_repo.create({"title": "Post 1", "user_id": user.id})
    post_repo.create({"title": "Post 2", "user_id": user.id})

    posts = user_repo.get_related_records(user.id, "posts")
    assert posts is not None
    assert len(posts) == 2
    assert {p.title for p in posts} == {"Post 1", "Post 2"}


def test_get_related_records_parent_not_found(user_repo):
    result = user_repo.get_related_records(999, "posts")
    assert result is None


def test_get_related_records_invalid_relationship(user_repo):
    user = user_repo.create({"name": "Alice", "age": 30})
    with pytest.raises(ValueError, match="nao e um relacionamento"):
        user_repo.get_related_records(user.id, "nonexistent")
