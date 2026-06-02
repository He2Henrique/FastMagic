from typing import Any, ClassVar
from pydantic import BaseModel, ConfigDict, create_model
from sqlalchemy import inspect
from sqlalchemy.orm import DeclarativeBase

class SchemaModel:
    sa_model: ClassVar[type[DeclarativeBase] | None] = None

    request: ClassVar[type[BaseModel]]
    update: ClassVar[type[BaseModel]]
    response: ClassVar[type[BaseModel]]

    request_include: ClassVar[set[str] | None] = None
    request_exclude: ClassVar[set[str] | None] = None
    request_extra_fields: ClassVar[dict[str, Any]] = {}

    update_include: ClassVar[set[str] | None] = None
    update_exclude: ClassVar[set[str] | None] = None
    update_extra_fields: ClassVar[dict[str, Any]] = {}

    response_include: ClassVar[set[str] | None] = None
    response_exclude: ClassVar[set[str] | None] = None
    response_extra_fields: ClassVar[dict[str, Any]] = {}

    def __init_subclass__(cls) -> None:
        super().__init_subclass__()

        if cls.sa_model is None:
            return

        base_name = cls.__name__.removesuffix("Schema")

        cls.request = cls.schema_from_model(
            cls.sa_model,
            name=f"{base_name}RequestSchema",
            include=cls.request_include,
            exclude=cls._write_exclude(cls.sa_model, cls.request_exclude),
            extra_fields=cls.request_extra_fields,
        )
        cls.update = cls.schema_from_model(
            cls.sa_model,
            name=f"{base_name}UpdateSchema",
            include=cls.update_include,
            exclude=cls._write_exclude(cls.sa_model, cls.update_exclude),
            optional=True,
            extra_fields=cls.update_extra_fields,
            forbid_extra=True,
        )
        cls.response = cls.schema_from_model(
            cls.sa_model,
            name=f"{base_name}ResponseSchema",
            include=cls.response_include,
            exclude=cls.response_exclude,
            from_attributes=True,
            extra_fields=cls.response_extra_fields,
        )

    @classmethod
    def _write_exclude(
        cls,
        sa_model: type[DeclarativeBase],
        custom_exclude: set[str] | None = None,
    ) -> set[str]:
        mapper = inspect(sa_model)
        excluded = {
            column.key
            for column in mapper.columns
            if column.primary_key or column.server_default is not None
        }

        if custom_exclude:
            excluded.update(custom_exclude)

        return excluded

    def __init__(self, sa_model: type[DeclarativeBase]) -> None:
        self.sa_model_instance = sa_model

    def get_request_schema(self)-> type[BaseModel]:
        return self.schema_from_model(
            self.sa_model_instance,
            exclude=self._write_exclude(self.sa_model_instance),
        )
    
    def get_update_schema(self)-> type[BaseModel]:
        return self.schema_from_model(
            self.sa_model_instance,
            exclude=self._write_exclude(self.sa_model_instance),
            optional=True,
            forbid_extra=True,
        )
    
    def get_response_schema(self)-> type[BaseModel]:
        return self.schema_from_model(self.sa_model_instance, from_attributes=True)

    @staticmethod
    def schema_from_model(
        sa_model: type[DeclarativeBase],
        *,
        name: str | None = None,
        include: set[str] | None = None,
        exclude: set[str] | None = None,
        optional: bool = False,
        from_attributes: bool = False,
        extra_fields: dict[str, Any] | None = None,
        forbid_extra: bool = False,
    ) -> type[BaseModel]:
        mapper = inspect(sa_model)
        fields: dict[str, Any] = {}

        for column in mapper.columns:
            field_name = column.key

            if include and field_name not in include:
                continue

            if exclude and field_name in exclude:
                continue

            try:
                python_type = column.type.python_type
            except NotImplementedError:
                python_type = Any

            nullable = column.nullable or optional

            if nullable:
                python_type = python_type | None

            default = None if nullable else ...

            fields[field_name] = (python_type, default)

        if extra_fields:
            fields.update(extra_fields)

        if forbid_extra:
            config = ConfigDict(from_attributes=from_attributes, extra="forbid")
        else:
            config = ConfigDict(from_attributes=from_attributes)

        return create_model(
            name or f"{sa_model.__name__}Schema",
            __config__=config,
            **fields,
        )
