# CLAUDE.md

Guía para que Claude Code trabaje sobre este repositorio.

## Contexto del proyecto

API del sitio web personal construida con:

- **FastAPI** — framework web async.
- **SQLAlchemy 2.0** — ORM con soporte async y sync (estilo `Mapped[...]`).
- **Alembic** — migraciones de base de datos.
- **Pydantic v2** — validación y serialización.
- **MySQL** — base de datos (driver async `aiomysql`, sync `pymysql`).

Python >= 3.11.

## Estructura del proyecto

```
app/
├── api/v1/              # Routers y endpoints versionados
│   ├── endpoints/       # Un archivo por recurso (health.py, users.py, ...)
│   └── router.py        # Agrega todos los routers del v1
├── core/                # Config, engine/session de base de datos
│   ├── config.py        # Settings con pydantic-settings
│   └── database.py      # Engines async/sync + session makers
├── dependencies/        # Depends() reutilizables (DB, auth, etc.)
├── models/              # Modelos SQLAlchemy (Base + mixins)
├── repositories/        # Acceso a datos (patrón Repository)
├── schemas/             # Pydantic models (request/response)
├── services/            # Lógica de negocio (orquesta repositorios)
└── main.py              # create_app() + lifespan + middlewares
alembic/                 # Migraciones
tests/                   # Tests (pytest + pytest-asyncio)
```

## Comandos habituales

```bash
# Entorno
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# Servidor de desarrollo
uvicorn app.main:app --reload

# Migraciones
alembic revision --autogenerate -m "mensaje"
alembic upgrade head
alembic downgrade -1

# Calidad
ruff check .
ruff format .
pytest
```

## Principios de código (obligatorios)

### Clean Code
- Nombres descriptivos (`get_user_by_email`, no `get_u`). Inglés para el código, español sólo en docs/comentarios si aporta.
- Funciones cortas, una sola responsabilidad. Si una función supera ~30 líneas, probablemente hay que dividirla.
- Evita comentarios que repiten lo que dice el código; sólo explica el **por qué**.
- Elimina código muerto. No dejes `# TODO` sin issue asociado.

### DRY (Don't Repeat Yourself)
- Lógica compartida → `services/` o helpers en `core/`.
- Queries repetidas → métodos en el repositorio correspondiente.
- Validaciones repetidas → validators de Pydantic o schemas base.
- Nunca copies-pegues más de dos veces: extrae.

### Código modular
- **Separación por capa** — routers sólo manejan HTTP, services la lógica, repositorios la persistencia, schemas la validación.
- **Los endpoints no llaman al ORM directamente** — pasan por un service o repositorio.
- **Los modelos SQLAlchemy nunca se exponen** al exterior — siempre se devuelven como schemas Pydantic.
- **Un archivo por recurso** en `endpoints/`, `models/`, `schemas/`, `repositories/`, `services/`.

### SOLID (lo esencial)
- Inyección de dependencias vía `Depends(...)` / `Annotated[...]`.
- Repositorios y services tipados con `TypeVar` / `Generic` cuando aporte.
- No acoples la lógica de negocio al framework (un service no debería importar `fastapi`).

## Reglas específicas del stack

### SQLAlchemy 2.0
- Usa la sintaxis nueva: `Mapped[...]` + `mapped_column(...)`. Nada de `Column(...)` al estilo 1.x.
- Queries con `select(...)` + `session.execute(...)`. No uses `session.query(...)`.
- Async por defecto para endpoints (`AsyncSession`). Usa sync sólo en scripts/Alembic.
- No hagas `commit` dentro de repositorios — eso es responsabilidad del service o del endpoint (transacción por request).
- `expire_on_commit=False` ya está configurado — ten cuidado al refrescar objetos.
- **Timestamps obligatorios en todo modelo:** `created_at`, `updated_at` y `deleted_at` (soft delete). `created_at`/`updated_at` vienen del `TimestampMixin`; `deleted_at` debe ser `DateTime(timezone=True)` nullable e indexado. Todas las queries por defecto deben filtrar `deleted_at IS NULL`.

### Alembic
- **Siempre** `--autogenerate` a partir de los modelos, pero **revisa la migración antes de aplicarla** (autogenerate no detecta todo: renombres, enums, constraints con nombre).
- Importa cada nuevo módulo de modelos en [alembic/env.py](alembic/env.py) para que autogenerate lo vea.
- Migraciones reversibles: `downgrade()` funcional siempre que sea posible.
- No edites migraciones ya aplicadas en entornos compartidos — crea una nueva.

### Pydantic v2
- `model_config = ConfigDict(from_attributes=True)` para schemas que se construyen desde modelos ORM.
- Usa `Field(...)` para restricciones (`min_length`, `ge`, `pattern`, ...).
- Separa schemas por intención: `XCreate`, `XUpdate`, `XRead`, `XInDB`. No reutilices el de lectura para crear.
- Valida en el borde (entrada del endpoint); dentro del sistema, confía en los tipos.

### FastAPI
- Rutas versionadas bajo `/api/v1`.
- `response_model` explícito en cada endpoint (no retornes modelos ORM crudos).
- Dependencias tipadas con `Annotated[Tipo, Depends(func)]`.
- Errores: lanza `HTTPException` con `status_code` correcto. Nada de `return {"error": ...}` con 200.

### Endpoints protegidos (auth)
- **Verificación de token: nunca dentro de services.** Vive en [app/dependencies/auth.py](app/dependencies/auth.py) (`get_current_user`). Los services asumen que el usuario ya viene autenticado.
- **Todo endpoint que requiera autenticación usa el decorator `protected`:**
  ```python
  from app.dependencies.auth import CurrentUser, protected

  @router.post("/foo", dependencies=protected)
  async def foo(current_user: CurrentUser): ...
  ```
- `dependencies=protected` es obligatorio para marcar la intención, aunque el endpoint también reciba `current_user: CurrentUser`. Deja la protección explícita en la firma del endpoint.
- Si el endpoint NO necesita al usuario, basta con `dependencies=protected` (sin el parámetro).
- No dupliques decodificación de JWT en otros archivos. Si necesitas validar el token desde otro lugar, reutiliza `get_current_user` o `decode_access_token` de [app/core/security.py](app/core/security.py).

### MySQL / configuración
- Strings de conexión se derivan en [app/core/config.py](app/core/config.py) — no las construyas a mano en otros archivos.
- Nunca commitees `.env`. Mantén `.env.example` actualizado si añades variables.
- Secretos sólo vía variables de entorno.

## Flujo para añadir un recurso (ej. `Post`)

1. **Modelo** — [app/models/post.py](app/models/post.py) con `Base` + `IDMixin` + `TimestampMixin`.
2. **Importar** ese módulo en [alembic/env.py](alembic/env.py).
3. **Schemas** — [app/schemas/post.py](app/schemas/post.py): `PostCreate`, `PostUpdate`, `PostRead`.
4. **Repositorio** — [app/repositories/post.py](app/repositories/post.py) extendiendo `BaseRepository[Post]`.
5. **Service** — [app/services/post.py](app/services/post.py) con la lógica de negocio.
6. **Endpoint** — [app/api/v1/endpoints/posts.py](app/api/v1/endpoints/posts.py) e incluirlo en [app/api/v1/router.py](app/api/v1/router.py).
7. **Migración** — `alembic revision --autogenerate -m "add post"` y revisar.
8. **Tests** — al menos un test por endpoint (happy path + un error).

## Qué NO hacer

- No mezclar lógica de negocio dentro de los endpoints.
- No llamar al ORM desde un endpoint sin pasar por service/repositorio.
- No exponer modelos SQLAlchemy como `response_model`.
- No usar `print` para logging — configurar logging apropiado si hace falta.
- No hacer `except Exception: pass`. Captura específica o deja propagar.
- No hacer `commit` en repositorios.
- No editar migraciones ya aplicadas.
- No duplicar validaciones entre schema y service.
