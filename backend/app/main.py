import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from .db import apply_migrations, catalog_data, make_engine, make_session_factory, seed_catalog


def create_app(session_factory: sessionmaker[Session] | None = None) -> FastAPI:
    owns_database = session_factory is None
    if owns_database:
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            raise RuntimeError("DATABASE_URL es obligatoria para iniciar la API.")
        engine = make_engine(database_url)
        session_factory = make_session_factory(engine)
    else:
        engine = None

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if owns_database and engine is not None:
            apply_migrations(engine)
            seed_catalog(session_factory)
        yield
        if engine is not None:
            engine.dispose()

    app = FastAPI(title="Bubu's bakery API", version="0.1.0", lifespan=lifespan)
    origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "").split(",") if origin.strip()]
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET"], allow_headers=["*"])

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "servicio": "api"}

    @app.get("/api/catalog")
    def catalog() -> dict:
        try:
            return {"products": catalog_data(session_factory)}
        except SQLAlchemyError:
            return JSONResponse(status_code=503, content={"error": "No pudimos cargar el catálogo en este momento."})

    @app.exception_handler(Exception)
    async def unexpected_error(_: Request, __: Exception):
        return JSONResponse(status_code=500, content={"error": "Ocurrió un error inesperado."})

    return app


app = create_app() if os.getenv("DATABASE_URL") else FastAPI(title="Bubu's bakery API")
