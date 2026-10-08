from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.auth import create_session, hash_password
from app.db import create_test_session, init_test_database, seed_catalog
from app.main import create_app
from app.models import AppSession, Order, Sale, User

ORIGIN = "http://localhost:5173"


def setup_clients():
    factory, engine = create_test_session()
    init_test_database(engine)
    seed_catalog(factory)
    app = create_app(factory)
    return TestClient(app), factory


def create_user(factory, email, role="customer"):
    with factory() as session:
        user = User(email=email, name=email.split("@")[0], password_hash=hash_password("ClienteSeguro1234"), role=role, email_verified=False, active=True, created_at=datetime.now(timezone.utc))
        session.add(user)
        session.commit()
        session.refresh(user)
        token = create_session(session, user)
    return token


def auth_headers(token, idem="pedido-1"):
    return {"Origin": ORIGIN, "Cookie": f"bubus_session={token}", "Idempotency-Key": idem}


def mixed_item():
    return {"slug": "mixta-caja-6", "quantity": 1, "options": {"sixth-brownie": "almendra"}}


def test_customer_request_calculates_backend_price_freezes_composition_and_hides_other_users():
    client, factory = setup_clients()
    first = create_user(factory, "uno@example.com")
    second = create_user(factory, "dos@example.com")
    body = {"fulfillment": "envio", "contactReference": "WhatsApp de prueba", "items": [{"slug": "simple-caja-6", "quantity": 1, "priceCents": 1}, mixed_item()]}
    response = client.post("/api/orders", json=body, headers=auth_headers(first))
    assert response.status_code == 201
    order = response.json()
    assert order["status"] == "POR_CONFIRMAR"
    assert order["subtotalCents"] == 6000 + 8500
    assert order["shippingAmountCents"] is None and order["totalFinalCents"] is None
    assert order["items"][1]["selectedOptions"] == [{"group": "sixth-brownie", "product": "almendra", "quantity": 1}]
    assert client.get("/api/orders", headers={"Cookie": f"bubus_session={second}"}).json()["orders"] == []
    with factory() as session:
        stored = session.scalar(select(Order).where(Order.id == order["id"]))
        assert stored is not None and stored.subtotal_cents == 14500
        assert stored.total_final_cents is None


def test_order_rejects_individual_delivery_invalid_mix_and_price_tampering():
    client, factory = setup_clients()
    token = create_user(factory, "cliente@example.com")
    headers = auth_headers(token, "reject-1")
    individual = client.post("/api/orders", json={"fulfillment": "envio", "items": [{"slug": "simple", "quantity": 1}]}, headers=headers)
    assert individual.status_code == 422 and "cajas" in individual.json()["error"].lower()
    invalid_mix = client.post("/api/orders", json={"fulfillment": "envio", "items": [{"slug": "mixta-caja-6", "quantity": 1, "priceCents": 0, "options": {}}]}, headers=auth_headers(token, "reject-2"))
    assert invalid_mix.status_code == 422 and "elección" in invalid_mix.json()["error"].lower()
    bad_quantity = client.post("/api/orders", json={"fulfillment": "envio", "items": [{"slug": "simple-caja-6", "quantity": 0}]}, headers=auth_headers(token, "reject-3"))
    assert bad_quantity.status_code == 422


def test_order_idempotency_does_not_duplicate_and_statuses_are_separate():
    client, factory = setup_clients()
    token = create_user(factory, "idempotent@example.com")
    body = {"fulfillment": "envio", "items": [{"slug": "simple-caja-6", "quantity": 1}]}
    first = client.post("/api/orders", json=body, headers=auth_headers(token, "same-key"))
    again = client.post("/api/orders", json=body, headers=auth_headers(token, "same-key"))
    assert first.status_code == 201 and again.status_code == 200
    assert first.json()["id"] == again.json()["id"]
    assert again.json()["paymentStatus"] == "PENDIENTE" and again.json()["deliveryStatus"] == "PENDIENTE"
    with factory() as session:
        assert len(session.scalars(select(Order)).all()) == 1


def test_operator_can_register_cash_sale_and_customer_cannot_or_claim_receipt():
    client, factory = setup_clients()
    customer = create_user(factory, "customer@example.com")
    operator = create_user(factory, "operator@example.com", "operator")
    body = {"customerEmail": "customer@example.com", "reference": "Ticket interno smoke", "items": [{"slug": "simple", "quantity": 2, "priceCents": 999999}], "paymentMethod": "efectivo", "receivedConfirmed": True}
    denied = client.post("/api/operator/sales", json=body, headers=auth_headers(customer, "sale-customer"))
    assert denied.status_code == 403
    sale = client.post("/api/operator/sales", json=body, headers=auth_headers(operator, "sale-1"))
    assert sale.status_code == 201
    assert sale.json()["subtotalCents"] == 2000 and sale.json()["paymentMethod"] == "EFECTIVO" and sale.json()["reference"] == "Ticket interno smoke"
    duplicate = client.post("/api/operator/sales", json=body, headers=auth_headers(operator, "sale-1"))
    assert duplicate.status_code == 200 and duplicate.json()["id"] == sale.json()["id"]
    not_confirmed = client.post("/api/operator/sales", json={**body, "receivedConfirmed": False}, headers=auth_headers(operator, "sale-2"))
    assert not_confirmed.status_code == 422
    with factory() as session:
        assert len(session.scalars(select(Sale)).all()) == 1


def test_operator_can_view_and_update_order_but_customer_cannot():
    client, factory = setup_clients()
    customer = create_user(factory, "owner@example.com")
    operator = create_user(factory, "staff@example.com", "operator")
    created = client.post("/api/orders", json={"fulfillment": "envio", "items": [{"slug": "simple-caja-6", "quantity": 1}]}, headers=auth_headers(customer, "order-view"))
    order_id = created.json()["id"]
    own = client.get("/api/orders", headers={"Cookie": f"bubus_session={customer}"})
    assert own.status_code == 200 and own.json()["orders"][0]["id"] == order_id
    denied = client.get("/api/operator/orders", headers={"Cookie": f"bubus_session={customer}"})
    assert denied.status_code == 403
    visible = client.get("/api/operator/orders", headers={"Cookie": f"bubus_session={operator}"})
    assert visible.status_code == 200 and visible.json()["orders"][0]["id"] == order_id
    changed = client.patch(f"/api/operator/orders/{order_id}", json={"status": "CONFIRMADA"}, headers=auth_headers(operator, "order-status"))
    assert changed.status_code == 200 and changed.json()["status"] == "CONFIRMADA"


def test_cors_allows_authenticated_patch_and_idempotency_header_only_from_dev_origin():
    client, _ = setup_clients()
    response = client.options("/api/operator/orders/1", headers={"Origin": ORIGIN, "Access-Control-Request-Method": "PATCH", "Access-Control-Request-Headers": "content-type,idempotency-key"})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ORIGIN
    assert "PATCH" in response.headers["access-control-allow-methods"]
    assert "idempotency-key" in response.headers["access-control-allow-headers"].lower()
