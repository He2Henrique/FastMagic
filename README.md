# FastMagic

FastMagic e uma biblioteca em Python para acelerar a criacao de APIs REST com
FastAPI, SQLAlchemy e Pydantic.

A ideia do projeto, ate agora, e reduzir codigo repetitivo em tres pontos:

- geracao de schemas Pydantic a partir de models SQLAlchemy;
- operacoes genericas de repositorio para CRUD;
- geracao automatica de rotas REST (CRUD) para um `APIRouter` do FastAPI.

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
  generic_router.py
```

O pacote exporta:

```python
from FastMagic import SchemaModel, GenericRepository, GenericAPI, Route
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

- `list_records(order_by=None, filters=None)`: lista os registros do model,
  com ordenacao e filtros opcionais;
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
users_por_nome = repo.list_records(order_by="name")
users_mais_velhos = repo.list_records(order_by="-age")
users_ativos = repo.list_records(filters={"active": True})
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

`order_by` aceita uma coluna (`"name"`), uma lista de colunas
(`["name", "-age"]`) e o prefixo `-` indica ordem descendente. `filters` e um
`dict[str, Any]` cuja chave pode ter um sufixo de comparacao — `__gte`,
`__lte`, `__gt`, `__lt` — ou nenhum, para igualdade exata:

```python
repo.list_records(filters={"age__gte": 18, "age__lt": 65})
repo.list_records(filters={"created_at__gte": date(2026, 1, 1)})
```

Caso `order_by` ou `filters` referenciem uma coluna que nao existe no model, o
repositorio levanta `ValueError`.

Na rota gerada por `GenericAPI` (`GET /`), `order_by` vira query param
(`?order_by=name` ou `?order_by=-age,name`) e qualquer outro query param e
tratado como filtro, com os mesmos sufixos de comparacao aceitos pelo
repositorio (`?age__gte=18&age__lt=65`, `?active=true`,
`?created_at__gte=2026-01-01`). O valor da query string e convertido para o
tipo Python da coluna (`int`, `float`, `bool`, `date`, `datetime`) antes de
filtrar. Uma coluna invalida ou um valor que nao pode ser convertido retorna
`400 Bad Request`.

## GenericAPI

`GenericAPI` registra rotas CRUD prontas em um `APIRouter` do FastAPI,
usando um `GenericRepository` por baixo dos panos.

```python
from fastapi import APIRouter, FastAPI

from FastMagic import GenericAPI, SchemaModel
from app.database import get_session
from app.models import User


class UserSchema(SchemaModel):
    sa_model = User


router = APIRouter(prefix="/users", tags=["users"])
GenericAPI(router, get_session, User, UserSchema)

app = FastAPI()
app.include_router(router)
```

O segundo parametro e a propria funcao de dependencia de `Session` (a mesma
que voce passaria para `Depends` do FastAPI, no formato
`Generator[Session, None, None]`) — nao uma sessao ja criada. `GenericAPI`
registra essa funcao com `Depends` em cada rota gerada, entao cada requisicao
recebe sua propria sessao, que e fechada ao final da requisicao.

Rotas registradas por padrao (equivalentes a `routes=Route.ALL`):

- `POST /`: cria um registro a partir de `schema.request`, retorna `201`;
- `GET /`: lista registros (`schema.response`), aceitando `order_by` e
  filtros via query params, como descrito na secao de `GenericRepository`;
- `GET /{item_id}`: busca por chave primaria, `404` se nao encontrado;
- `PUT /{item_id}`: atualiza parcialmente via `schema.update`, `404` se nao
  encontrado;
- `DELETE /{item_id}`: remove, retorna `204`, `404` se nao encontrado.

Para expor apenas algumas rotas, use o parametro `routes` com a flag `Route`:

```python
from FastMagic import GenericAPI, Route

GenericAPI(router, get_session(), User, UserSchema, routes=Route.CREATE | Route.LIST)
GenericAPI(router, get_session(), User, UserSchema, routes=Route.ALL & ~Route.DELETE)
```

Valores disponiveis: `Route.CREATE`, `Route.LIST`, `Route.GET`,
`Route.UPDATE`, `Route.DELETE` e `Route.ALL`.

Tambem e possivel expor uma rota extra para um relacionamento do model, usando
`get_related_records` do repositorio por baixo:

```python
api = GenericAPI(router, get_session(), User, UserSchema)
api.add_related_route("/{item_id}/posts", "posts", PostSchema.response)
```

Isso registra `GET /{item_id}/posts`, retornando `404` se o registro pai nao
existir.

## Observacoes

- O nome do pacote no `pyproject.toml` e `fastmagic`, mas o modulo importado e
  `FastMagic`.
- `GenericRepository.create` recebe o parametro `dictnary` (grafia mantida
  como esta no codigo hoje).
