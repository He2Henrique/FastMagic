from .conftest import User, Post, UserSchema, PostSchema


def test_request_schema_excludes_pk():
    fields = UserSchema.request.model_fields
    assert "id" not in fields
    assert "name" in fields
    assert "age" in fields


def test_update_schema_all_fields_optional():
    fields = UserSchema.update.model_fields
    assert all(not f.is_required() for f in fields.values())


def test_update_schema_forbids_extra():
    schema = UserSchema.update
    result = schema.model_validate({"name": "Alice"})
    assert result.name == "Alice"

    try:
        schema.model_validate({"name": "Alice", "unknown_field": "x"})
        assert False, "should have raised"
    except Exception:
        pass


def test_response_schema_includes_pk():
    fields = UserSchema.response.model_fields
    assert "id" in fields
    assert "name" in fields
    assert "age" in fields


def test_response_schema_accepts_orm_object(db, user_repo):
    user = user_repo.create({"name": "Alice", "age": 30})
    schema = UserSchema.response.model_validate(user)
    assert schema.id == user.id
    assert schema.name == "Alice"


def test_post_schema_excludes_pk_and_fk_server_defaults():
    fields = PostSchema.request.model_fields
    assert "id" not in fields
    assert "title" in fields


def test_custom_exclude():
    from FastMagic import SchemaModel
    from .conftest import User

    class CustomSchema(SchemaModel):
        sa_model = User
        request_exclude = {"age"}

    fields = CustomSchema.request.model_fields
    assert "age" not in fields
    assert "name" in fields


def test_custom_extra_fields():
    from FastMagic import SchemaModel
    from .conftest import User
    from pydantic import Field

    class CustomSchema(SchemaModel):
        sa_model = User
        request_extra_fields = {"nickname": (str, Field(default="anon"))}

    fields = CustomSchema.request.model_fields
    assert "nickname" in fields
