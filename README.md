# FastMagic

FastMagic e uma biblioteca em Python para acelerar a criacao de APIs REST com
FastAPI, SQLAlchemy e Pydantic.

A ideia do projeto, ate agora, e reduzir codigo repetitivo em tres pontos:

- geracao de schemas Pydantic a partir de models SQLAlchemy;
- operacoes genericas de repositorio para CRUD;
- uma camada simples de service sobre o repositorio.

## Status atual

O projeto ainda esta em fase inicial. A versao configurada no `pyproject.toml`
e `0.1.0` e o pacote exige Python `>=3.11`.

Dependencias principais:

- `fastapi[standard]`
- `sqlalchemy`

## Instalacao em desenvolvimento

Dentro da raiz do projeto:

```bash
pip install -e .
```

## Estrutura atual

```text
src/FastMagic/
  __init__.py
  schema_model.py
  generic_repo.py
  generic_service.py
```

O pacote exporta:

```python
from FastMagic import SchemaModel, GenericRepository, GenericService
```

## SchemaModel

`SchemaModel` cria schemas Pydantic dinamicamente a partir de um model
SQLAlchemy.

Ao criar uma classe filha com `sa_model`, tres schemas sao gerados
automaticamente:

- `request`: schema para criacao;
- `update`: schema para atualizacao parcial;
- `response`: schema para resposta, com `from_attributes=True`.

Exemplo:

```python
from FastMagic import SchemaModel
from app.models import User


class UserSchema(SchemaModel):
    sa_model = User


UserCreate = UserSchema.request
UserUpdate = UserSchema.update
UserResponse = UserSchema.response
```

Por padrao, campos de escrita ignoram colunas que sao chave primaria ou possuem
`server_default`.

Tambem e possivel ajustar quais campos entram ou saem dos schemas:

```python
class UserSchema(SchemaModel):
    sa_model = User

    request_exclude = {"created_at"}
    response_extra_fields = {
        "display_name": (str | None, None),
    }
```

Opcoes disponiveis na classe:

- `request_include` / `request_exclude`
- `request_extra_fields`
- `update_include` / `update_exclude`
- `update_extra_fields`
- `response_include` / `response_exclude`
- `response_extra_fields`

Tambem existe o metodo estatico `schema_from_model`, caso seja necessario gerar
um schema manualmente.

## GenericRepository

`GenericRepository` encapsula operacoes comuns de banco usando uma `Session` do
SQLAlchemy e um model.

Metodos disponiveis:

- `list_records()`: lista todos os registros do model;
- `get_by_id(id_to_search)`: busca um registro pela chave primaria;
- `create(dictnary)`: cria, salva e retorna um novo registro;
- `update(id_to_update, **data_to_update)`: atualiza um registro pela chave primaria;
- `delete(id_to_delete)`: remove um registro pela chave primaria;
- `get_related_records(parent_id, relationship_name, child_relationships=())`: busca registros relacionados usando `selectinload`.

Exemplo:

```python
from FastMagic import GenericRepository
from app.models import User


repo = GenericRepository(db=session, model=User)

users = repo.list_records()
user = repo.get_by_id(1)
created = repo.create({"name": "Ana", "email": "ana@example.com"})
updated = repo.update(1, name="Ana Maria")
deleted_id = repo.delete(1)
```

Para relacionamentos:

```python
orders = repo.get_related_records(
    parent_id=1,
    relationship_name="orders",
)
```

Caso o relacionamento informado nao exista no model, o repositorio levanta
`ValueError`.

## GenericService

`GenericService` e uma camada simples sobre `GenericRepository`. Ela apenas
repassa as chamadas para o repositorio, mantendo um ponto unico para futuras
regras de negocio.

Metodos disponiveis:

- `listar()`
- `get_by_id(id_to_search)`
- `get_related_records(parent_id, relationship_name, child_relationships=())`
- `create(data)`
- `update(id_to_update, **data_to_update)`
- `exclude(id_to_delete)`

Exemplo:

```python
from FastMagic import GenericRepository, GenericService
from app.models import User


repo = GenericRepository(db=session, model=User)
service = GenericService(repo)

users = service.listar()
user = service.get_by_id(1)
```

## Exemplo de uso com FastAPI

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from FastMagic import GenericRepository, GenericService, SchemaModel
from app.database import get_session
from app.models import User


class UserSchema(SchemaModel):
    sa_model = User


router = APIRouter(prefix="/users", tags=["users"])


def get_user_service(db: Session = Depends(get_session)):
    repo = GenericRepository(db, User)
    return GenericService(repo)


@router.get("/", response_model=list[UserSchema.response])
def list_users(service: GenericService = Depends(get_user_service)):
    return service.listar()


@router.post("/", response_model=UserSchema.response)
def create_user(
    data: UserSchema.request,
    service: GenericService = Depends(get_user_service),
):
    return service.create(data.model_dump())
```

## Observacoes

- A biblioteca ainda nao possui testes versionados no diretorio `tests`.
- O nome do pacote no `pyproject.toml` e `fastmagic`, mas o modulo importado e
  `FastMagic`.
- Alguns nomes de metodos ainda misturam portugues e ingles, como `listar`,
  `exclude` e `get_by_id`.
