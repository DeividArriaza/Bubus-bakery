import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from .auth import SESSION_COOKIE, create_session, current_user, hash_password, normalize_email, public_user, require_origin, revoke_session, verify_password
from .db import apply_migrations, catalog_data, make_engine, make_session_factory, seed_catalog
from .models import User


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
    origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if origin.strip()]
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["GET", "POST"], allow_headers=["Content-Type"])

    secure_cookie = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"

    def auth_error(message: str, status: int) -> JSONResponse:
        return JSONResponse(status_code=status, content={"error": message})

    def cookie_response(response, token: str):
        response.set_cookie(SESSION_COOKIE, token, httponly=True, secure=secure_cookie, samesite="lax", max_age=7 * 24 * 60 * 60, path="/")
        return response

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "servicio": "api"}

    @app.get("/api/catalog")
    def catalog() -> dict:
        try:
            return {"products": catalog_data(session_factory)}
        except SQLAlchemyError:
            return JSONResponse(status_code=503, content={"error": "No pudimos cargar el catálogo en este momento."})

    @app.post("/api/auth/register", status_code=201)
    def register(request: Request, payload: dict):
        require_origin(request, origins)
        try:
            email = normalize_email(payload.get("email"))
            password_hash = hash_password(payload.get("password"))
            name = payload.get("name")
            if not isinstance(name, str) or not name.strip() or len(name.strip()) > 120:
                raise ValueError("Ingresa tu nombre.")
        except ValueError as error:
            return auth_error(str(error), 422)
        with session_factory() as session:
            if session.scalar(select(User).where(User.email == email)) is not None:
                return auth_error("Ya existe una cuenta con ese correo.", 409)
            user = User(email=email, name=name.strip(), password_hash=password_hash, role="customer", email_verified=False, active=True, created_at=datetime.now(timezone.utc))
            session.add(user)
            session.flush()
            token = create_session(session, user)
            response = JSONResponse(status_code=201, content={"user": public_user(user)})
            return cookie_response(response, token)

    @app.post("/api/auth/login")
    def login(request: Request, payload: dict):
        require_origin(request, origins)
        try:
            email = normalize_email(payload.get("email"))
        except ValueError:
            return auth_error("Correo o contraseña incorrectos.", 401)
        password = payload.get("password")
        with session_factory() as session:
            user = session.scalar(select(User).where(User.email == email))
            if user is None or not user.active or not verify_password(password, user.password_hash):
                return auth_error("Correo o contraseña incorrectos.", 401)
            token = create_session(session, user)
            response = JSONResponse(content={"user": public_user(user)})
            return cookie_response(response, token)

    @app.get("/api/auth/session")
    def session_status(request: Request):
        try:
            return {"user": public_user(current_user(request, session_factory))}
        except Exception as error:
            if hasattr(error, "status_code"):
                return auth_error(error.detail, error.status_code)
            raise

    @app.post("/api/auth/logout", status_code=204)
    def logout(request: Request):
        require_origin(request, origins)
        revoke_session(request, session_factory)
        response = JSONResponse(status_code=204, content=None)
        response.delete_cookie(SESSION_COOKIE, path="/")
        return response

    @app.get("/api/auth/operator")
    def operator_area(request: Request):
        user = current_user(request, session_factory)
        if user.role != "operator":
            return auth_error("No tienes permisos para esta sección.", 403)
        return {"ok": True}

    @app.get("/api/auth/google/start")
    def google_start():
        return auth_error("El acceso con Google aún no está configurado.", 503)

    @app.exception_handler(Exception)
    async def unexpected_error(_: Request, __: Exception):
        return JSONResponse(status_code=500, content={"error": "Ocurrió un error inesperado."})

    @app.exception_handler(HTTPException)
    async def http_error(_: Request, error: HTTPException):
        message = error.detail if isinstance(error.detail, str) else "La solicitud no es válida."
        return JSONResponse(status_code=error.status_code, content={"error": message})

    return app


app = create_app() if os.getenv("DATABASE_URL") else FastAPI(title="Bubu's bakery API")
