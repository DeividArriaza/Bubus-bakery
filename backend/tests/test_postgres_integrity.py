import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url

from app.auth import create_session, hash_password
from app.db import apply_migrations, make_session_factory, seed_catalog
from app.main import create_app
from app.models import Order, Product, Sale, User


def _isolated_database():
    raw_url = os.getenv("TEST_DATABASE_URL")
    if not raw_url:
        pytest.skip("requiere TEST_DATABASE_URL y PostgreSQL real")
    schema = f"integrity_{uuid.uuid4().hex}"
    admin = create_engine(raw_url)
    quoted_schema = '"' + schema + '"'
    with admin.begin() as connection:
        connection.execute(text(f"CREATE SCHEMA {quoted_schema}"))
    url = make_url(raw_url).update_query_dict({"options": f"-csearch_path={schema},public"})
    engine = create_engine(url, pool_pre_ping=True)
    factory = make_session_factory(engine)
    try:
        apply_migrations(engine)
        seed_catalog(factory)
        yield factory, engine
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f"DROP SCHEMA {quoted_schema} CASCADE"))
        admin.dispose()


@pytest.fixture()
def postgres_catalog():
    yield from _isolated_database()


def _user(factory, email: str, role: str = "customer") -> str:
    with factory() as session:
        user = User(email=email, name="Prueba", password_hash=hash_password("ClienteSeguro1234"), role=role, active=True, email_verified=False, created_at=datetime.now(timezone.utc))
        session.add(user)
        session.commit()
        session.refresh(user)
        return create_session(session, user)


def _headers(token: str, key: str) -> dict[str, str]:
    return {"Origin": "http://localhost:5173", "Cookie": f"bubus_session={token}", "Idempotency-Key": key}


def test_fresh_postgres_migrations_seed_twice_and_mixed_operations(postgres_catalog):
    factory, engine = postgres_catalog
    with factory() as session:
        products = list(session.execute(text("SELECT slug FROM products WHERE active ORDER BY id")))
        assert len(products) == 9
        assert session.execute(text("SELECT count(*) FROM product_components")).scalar_one() == 6
        assert session.execute(text("SELECT count(*) FROM options")).scalar_one() == 2
    seed_catalog(factory)
    with factory() as session:
        assert session.execute(text("SELECT count(*) FROM products WHERE active")).scalar_one() == 9
        assert session.execute(text("SELECT count(*) FROM product_components")).scalar_one() == 6
        assert session.execute(text("SELECT count(*) FROM options")).scalar_one() == 2
    customer = _user(factory, "fresh-customer@example.com")
    operator = _user(factory, "fresh-operator@example.com", "operator")
    app = create_app(factory)
    order = TestClient(app).post("/api/orders", json={"fulfillment": "envio", "items": [{"slug": "mixta-caja-6", "quantity": 1, "options": {"sixth-brownie": "almendra"}}]}, headers=_headers(customer, "fresh-order"))
    assert order.status_code == 201
    assert order.json()["items"][0]["selectedOptions"][0]["product"] == "almendra"
    sale = TestClient(app).post("/api/operator/sales", json={"items": [{"slug": "mixta-caja-6", "quantity": 1, "options": {"sixth-brownie": "simple"}}], "paymentMethod": "efectivo", "receivedConfirmed": True}, headers=_headers(operator, "fresh-sale"))
    assert sale.status_code == 201
    assert sale.json()["items"][0]["selectedOptions"][0]["product"] == "simple"


def test_postgres_order_and_sale_concurrent_retries_return_one_winner(postgres_catalog):
    factory, _ = postgres_catalog
    customer = _user(factory, "race-customer@example.com")
    operator = _user(factory, "race-operator@example.com", "operator")
    app = create_app(factory)
    order_body = {"fulfillment": "envio", "items": [{"slug": "simple-caja-6", "quantity": 1}]}
    sale_body = {"items": [{"slug": "simple", "quantity": 1}], "paymentMethod": "transferencia", "receivedConfirmed": True}
    barrier = threading.Barrier(2)

    def order_call():
        barrier.wait()
        return TestClient(app).post("/api/orders", json=order_body, headers=_headers(customer, "race-order"))

    with ThreadPoolExecutor(max_workers=2) as pool:
        order_responses = list(pool.map(lambda _: order_call(), range(2)))
    assert sorted(response.status_code for response in order_responses) == [200, 201]
    with factory() as session:
        assert len(session.scalars(select(Order)).all()) == 1

    barrier = threading.Barrier(2)

    def sale_call():
        barrier.wait()
        return TestClient(app).post("/api/operator/sales", json=sale_body, headers=_headers(operator, "race-sale"))

    with ThreadPoolExecutor(max_workers=2) as pool:
        sale_responses = list(pool.map(lambda _: sale_call(), range(2)))
    assert sorted(response.status_code for response in sale_responses) == [200, 201]
    with factory() as session:
        assert len(session.scalars(select(Sale)).all()) == 1


def test_postgres_historical_replays_ignore_current_price_and_availability(postgres_catalog):
    factory, _ = postgres_catalog
    customer = _user(factory, "historical-pg-customer@example.com")
    operator = _user(factory, "historical-pg-operator@example.com", "operator")
    app = create_app(factory)
    order_body = {"fulfillment": "envio", "items": [{"slug": "simple-caja-6", "quantity": 1, "priceCents": 1}]}
    order = TestClient(app).post("/api/orders", json=order_body, headers=_headers(customer, "historical-pg-order"))
    assert order.status_code == 201
    sale_body = {"items": [{"slug": "simple", "quantity": 1, "priceCents": 1}], "paymentMethod": "efectivo", "receivedConfirmed": True}
    sale = TestClient(app).post("/api/operator/sales", json=sale_body, headers=_headers(operator, "historical-pg-sale"))
    assert sale.status_code == 201
    with factory() as session:
        session.scalar(select(Product).where(Product.slug == "simple-caja-6")).active = False
        session.scalar(select(Product).where(Product.slug == "simple-caja-6")).price_cents = 999999
        session.scalar(select(Product).where(Product.slug == "simple")).active = False
        session.scalar(select(Product).where(Product.slug == "simple")).price_cents = 999999
        session.commit()
    replay_order = TestClient(app).post("/api/orders", json=order_body, headers=_headers(customer, "historical-pg-order"))
    replay_sale = TestClient(app).post("/api/operator/sales", json=sale_body, headers=_headers(operator, "historical-pg-sale"))
    assert replay_order.status_code == 200 and replay_order.json()["id"] == order.json()["id"]
    assert replay_sale.status_code == 200 and replay_sale.json()["id"] == sale.json()["id"]


def test_postgres_cancel_confirm_race_cannot_reopen_cancelled_order(postgres_catalog):
    factory, _ = postgres_catalog
    customer = _user(factory, "cancel-customer@example.com")
    operator = _user(factory, "cancel-operator@example.com", "operator")
    app = create_app(factory)
    created = TestClient(app).post("/api/orders", json={"fulfillment": "envio", "items": [{"slug": "simple-caja-6", "quantity": 1}]}, headers=_headers(customer, "cancel-order"))
    order_id = created.json()["id"]
    barrier = threading.Barrier(2)

    def change(status):
        barrier.wait()
        return TestClient(app).patch(f"/api/operator/orders/{order_id}", json={"status": status}, headers=_headers(operator, f"status-{status}"))

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(change, ["CANCELADA", "CONFIRMADA"]))
    with factory() as session:
        order = session.get(Order, order_id)
        assert order.status == "CANCELADA"
    cancelled = responses[0]
    confirmed = responses[1]
    assert cancelled.status_code == 200
    assert confirmed.status_code in {200, 409}
    late_confirmation = TestClient(app).patch(f"/api/operator/orders/{order_id}", json={"status": "CONFIRMADA"}, headers=_headers(operator, "status-late-confirm"))
    assert late_confirmation.status_code == 409
