import os
import json
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from .auth import AuthRateLimiter, PASSWORD_MAX_LENGTH, SESSION_COOKIE, create_session, current_user, hash_password, normalize_email, public_user, require_origin, revoke_session, validate_password, verify_password
from .commerce import calculate_items, now_utc, order_fingerprint_data, order_json, payload_fingerprint, sale_fingerprint_data, sale_json
from .db import apply_migrations, catalog_data, make_engine, make_session_factory, seed_catalog
from .models import Order, OrderItem, Sale, SaleItem, User


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
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["GET", "POST", "PATCH"], allow_headers=["Content-Type", "Idempotency-Key"])

    secure_cookie = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
    def configured_int(name: str, default: int) -> int:
        try:
            return max(1, int(os.getenv(name, str(default))))
        except ValueError:
            return default

    auth_limiter = AuthRateLimiter(configured_int("AUTH_RATE_LIMIT_ATTEMPTS", 5), configured_int("AUTH_RATE_LIMIT_WINDOW_SECONDS", 60), configured_int("AUTH_RATE_LIMIT_MAX_ENTRIES", 10_000))
    hash_slots = threading.BoundedSemaphore(configured_int("AUTH_MAX_HASH_CONCURRENCY", 4))
    auth_max_bytes = configured_int("AUTH_MAX_REQUEST_BYTES", 8_192)

    @app.middleware("http")
    async def limit_auth_request_size(request: Request, call_next):
        if request.url.path in {"/api/auth/register", "/api/auth/login"}:
            content_length = request.headers.get("content-length")
            if content_length and content_length.isdigit() and int(content_length) > auth_max_bytes:
                return JSONResponse(status_code=413, content={"error": "La solicitud de acceso es demasiado grande."})
        return await call_next(request)

    def client_key(request: Request) -> str:
        if os.getenv("TRUST_PROXY", "false").lower() == "true":
            forwarded = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
            if forwarded:
                return forwarded[:100]
        return (request.client.host if request.client else "desconocido")[:100]

    def auth_rate_limit(request: Request, email: str) -> None:
        retry_after = auth_limiter.check([f"ip:{client_key(request)}", f"account:{email}"])
        if retry_after is not None:
            raise HTTPException(status_code=429, detail="Demasiados intentos de acceso. Intenta nuevamente más tarde.", headers={"Retry-After": str(retry_after)})

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
            name = payload.get("name")
            if not isinstance(name, str) or not name.strip() or len(name.strip()) > 120:
                raise ValueError("Ingresa tu nombre.")
            validate_password(payload.get("password"))
        except ValueError as error:
            return auth_error(str(error), 422)
        with session_factory() as session:
            if session.scalar(select(User).where(User.email == email)) is not None:
                return auth_error("Ya existe una cuenta con ese correo.", 409)
            auth_rate_limit(request, email)
            with hash_slots:
                password_hash = hash_password(payload.get("password"))
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
            password = payload.get("password")
            if isinstance(password, str) and len(password) > PASSWORD_MAX_LENGTH:
                raise ValueError(f"La contraseña no puede superar {PASSWORD_MAX_LENGTH} caracteres.")
        except ValueError as error:
            if "superar" in str(error):
                return auth_error(str(error), 422)
            return auth_error("Correo o contraseña incorrectos.", 401)
        auth_rate_limit(request, email)
        with session_factory() as session:
            user = session.scalar(select(User).where(User.email == email))
            valid = False
            if user is not None and user.active:
                with hash_slots:
                    valid = verify_password(password, user.password_hash)
            if not valid:
                return auth_error("Correo o contraseña incorrectos.", 401)
            auth_limiter.clear(f"account:{email}")
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

    def require_idempotency(value: str | None) -> str:
        if not value or not value.strip() or len(value.strip()) > 100:
            raise HTTPException(status_code=422, detail="La solicitud necesita una clave de reintento válida.")
        return value.strip()

    def require_operator(request: Request) -> User:
        user = current_user(request, session_factory)
        if user.role != "operator":
            raise HTTPException(status_code=403, detail="No tienes permisos para esta sección.")
        return user

    @app.post("/api/orders", status_code=201)
    def create_order(request: Request, payload: dict, idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
        require_origin(request, origins)
        user = current_user(request, session_factory)
        key = require_idempotency(idempotency_key)
        with session_factory() as session:
            if payload.get("fulfillment") != "envio":
                raise HTTPException(status_code=422, detail="Por ahora las solicitudes web son únicamente para envío.")
            payment_intent = payload.get("paymentIntent", "NO_DEFINIDO")
            if payment_intent not in {"NO_DEFINIDO", "AL_PEDIR", "AL_RECIBIR"}:
                raise HTTPException(status_code=422, detail="La intención de pago no es válida.")
            snapshots, subtotal = calculate_items(session, payload.get("items"), delivery_only_boxes=True)
            contact_reference = payload.get("contactReference")
            if contact_reference is not None and (not isinstance(contact_reference, str) or len(contact_reference.strip()) > 120):
                raise HTTPException(status_code=422, detail="La referencia de contacto es demasiado larga.")
            contact_reference = contact_reference.strip() if isinstance(contact_reference, str) else None
            fingerprint = payload_fingerprint({
                "fulfillment": "envio", "paymentIntent": payment_intent, "contactReference": contact_reference,
                "subtotalCents": subtotal,
                "items": [{"slug": item["product"].slug, "quantity": item["quantity"], "snapshot": item["snapshot"]} for item in snapshots],
            })
            existing = session.scalar(select(Order).where(Order.customer_id == user.id, Order.idempotency_key == key))
            if existing is not None:
                stored_items = list(session.scalars(select(OrderItem).where(OrderItem.order_id == existing.id).order_by(OrderItem.id)))
                existing_fingerprint = existing.payload_fingerprint or payload_fingerprint(order_fingerprint_data(existing, stored_items))
                if existing_fingerprint != fingerprint:
                    raise HTTPException(status_code=409, detail="La clave de reintento ya fue usada con otra solicitud.")
                return JSONResponse(status_code=200, content=order_json(session, existing))
            timestamp = now_utc()
            order = Order(customer_id=user.id, fulfillment="envio", status="POR_CONFIRMAR", payment_status="PENDIENTE", payment_intent=payment_intent, delivery_status="PENDIENTE", subtotal_cents=subtotal, shipping_amount_cents=None, total_final_cents=None, contact_reference=contact_reference, idempotency_key=key, payload_fingerprint=fingerprint, created_at=timestamp, updated_at=timestamp)
            session.add(order)
            try:
                session.flush()
                for item in snapshots:
                    product = item["product"]
                    session.add(OrderItem(order_id=order.id, product_id=product.id, product_slug=product.slug, product_name=product.name, unit_price_cents=product.price_cents, quantity=item["quantity"], snapshot_json=json.dumps(item["snapshot"], ensure_ascii=False, sort_keys=True)))
                session.commit()
                return JSONResponse(status_code=201, content=order_json(session, order))
            except IntegrityError:
                session.rollback()
                winner = session.scalar(select(Order).where(Order.customer_id == user.id, Order.idempotency_key == key))
                if winner is None:
                    raise
                winner_items = list(session.scalars(select(OrderItem).where(OrderItem.order_id == winner.id).order_by(OrderItem.id)))
                winner_fingerprint = winner.payload_fingerprint or payload_fingerprint(order_fingerprint_data(winner, winner_items))
                if winner_fingerprint != fingerprint:
                    raise HTTPException(status_code=409, detail="La clave de reintento ya fue usada con otra solicitud.")
                return JSONResponse(status_code=200, content=order_json(session, winner))

    @app.get("/api/orders")
    def list_customer_orders(request: Request):
        user = current_user(request, session_factory)
        with session_factory() as session:
            orders = session.scalars(select(Order).where(Order.customer_id == user.id).order_by(Order.created_at.desc())).all()
            return {"orders": [order_json(session, order) for order in orders]}

    @app.get("/api/operator/orders")
    def list_operator_orders(request: Request):
        require_operator(request)
        with session_factory() as session:
            orders = session.scalars(select(Order).order_by(Order.created_at.desc())).all()
            return {"orders": [order_json(session, order, include_customer=True) for order in orders]}

    @app.patch("/api/operator/orders/{order_id}")
    def update_order(request: Request, order_id: int, payload: dict):
        require_origin(request, origins)
        require_operator(request)
        status = payload.get("status")
        if status not in {"POR_CONFIRMAR", "CONFIRMADA", "CANCELADA"}:
            raise HTTPException(status_code=422, detail="Ese estado de solicitud no es válido.")
        with session_factory() as session:
            order = session.get(Order, order_id, with_for_update=True)
            if order is None:
                raise HTTPException(status_code=404, detail="No encontramos esa solicitud.")
            if order.status == "CANCELADA" and status != "CANCELADA":
                raise HTTPException(status_code=409, detail="Una solicitud cancelada no se puede reabrir automáticamente.")
            order.status = status
            order.updated_at = now_utc()
            session.commit()
            return order_json(session, order, include_customer=True)

    @app.post("/api/operator/sales", status_code=201)
    def create_sale(request: Request, payload: dict, idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
        require_origin(request, origins)
        actor = require_operator(request)
        key = require_idempotency(idempotency_key)
        if payload.get("receivedConfirmed") is not True:
            raise HTTPException(status_code=422, detail="El operador debe confirmar explícitamente la recepción del pago.")
        method = payload.get("paymentMethod")
        if method not in {"efectivo", "transferencia", "EFECTIVO", "TRANSFERENCIA"}:
            raise HTTPException(status_code=422, detail="El medio debe ser efectivo o transferencia.")
        customer_name = payload.get("customerName")
        if customer_name is not None and (not isinstance(customer_name, str) or len(customer_name.strip()) > 120):
            raise HTTPException(status_code=422, detail="El nombre del cliente es demasiado largo.")
        reference = payload.get("reference")
        if reference is not None and (not isinstance(reference, str) or len(reference.strip()) > 120):
            raise HTTPException(status_code=422, detail="La referencia es demasiado larga.")
        with session_factory() as session:
            snapshots, subtotal = calculate_items(session, payload.get("items"), delivery_only_boxes=False)
            customer_id = None
            customer_email = payload.get("customerEmail")
            if customer_email:
                try:
                    normalized = normalize_email(customer_email)
                except ValueError as error:
                    raise HTTPException(status_code=422, detail=str(error)) from error
                member = session.scalar(select(User).where(User.email == normalized, User.active.is_(True)))
                customer_id = member.id if member is not None else None
            normalized_method = method.upper()
            customer_name = customer_name.strip() if isinstance(customer_name, str) else None
            reference = reference.strip() if isinstance(reference, str) else None
            fingerprint = payload_fingerprint({
                "paymentMethod": normalized_method, "customerId": customer_id, "customerName": customer_name,
                "reference": reference, "subtotalCents": subtotal,
                "items": [{"slug": item["product"].slug, "quantity": item["quantity"], "snapshot": item["snapshot"]} for item in snapshots],
            })
            existing = session.scalar(select(Sale).where(Sale.actor_id == actor.id, Sale.idempotency_key == key))
            if existing is not None:
                stored_items = list(session.scalars(select(SaleItem).where(SaleItem.sale_id == existing.id).order_by(SaleItem.id)))
                existing_fingerprint = existing.payload_fingerprint or payload_fingerprint(sale_fingerprint_data(existing, stored_items))
                if existing_fingerprint != fingerprint:
                    raise HTTPException(status_code=409, detail="La clave de reintento ya fue usada con otra venta.")
                return JSONResponse(status_code=200, content=sale_json(session, existing))
            timestamp = now_utc()
            sale = Sale(actor_id=actor.id, customer_id=customer_id, payment_method=normalized_method, payment_status="RECIBIDO", subtotal_cents=subtotal, customer_name=customer_name, reference=reference, idempotency_key=key, payload_fingerprint=fingerprint, received_confirmed_at=timestamp, created_at=timestamp)
            session.add(sale)
            try:
                session.flush()
                for item in snapshots:
                    product = item["product"]
                    session.add(SaleItem(sale_id=sale.id, product_id=product.id, product_slug=product.slug, product_name=product.name, unit_price_cents=product.price_cents, quantity=item["quantity"], snapshot_json=json.dumps(item["snapshot"], ensure_ascii=False, sort_keys=True)))
                session.commit()
                return JSONResponse(status_code=201, content=sale_json(session, sale))
            except IntegrityError:
                session.rollback()
                winner = session.scalar(select(Sale).where(Sale.actor_id == actor.id, Sale.idempotency_key == key))
                if winner is None:
                    raise
                winner_items = list(session.scalars(select(SaleItem).where(SaleItem.sale_id == winner.id).order_by(SaleItem.id)))
                winner_fingerprint = winner.payload_fingerprint or payload_fingerprint(sale_fingerprint_data(winner, winner_items))
                if winner_fingerprint != fingerprint:
                    raise HTTPException(status_code=409, detail="La clave de reintento ya fue usada con otra venta.")
                return JSONResponse(status_code=200, content=sale_json(session, winner))

    @app.exception_handler(Exception)
    async def unexpected_error(_: Request, __: Exception):
        return JSONResponse(status_code=500, content={"error": "Ocurrió un error inesperado."})

    @app.exception_handler(HTTPException)
    async def http_error(_: Request, error: HTTPException):
        message = error.detail if isinstance(error.detail, str) else "La solicitud no es válida."
        return JSONResponse(status_code=error.status_code, content={"error": message}, headers=error.headers or {})

    return app


app = create_app() if os.getenv("DATABASE_URL") else FastAPI(title="Bubu's bakery API")
