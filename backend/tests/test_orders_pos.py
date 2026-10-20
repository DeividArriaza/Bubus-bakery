from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.auth import create_session, hash_password
from app.db import create_test_session, init_test_database, seed_catalog
from app.main import create_app
from app.models import AppSession, Component, Order, Product, Sale, User

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


def test_order_and_sale_reject_inactive_components_cycles_and_inactive_options():
    client, factory = setup_clients()
    customer = create_user(factory, "invalid-structure-customer@example.com")
    operator = create_user(factory, "invalid-structure-operator@example.com", "operator")
    with factory() as session:
        simple = session.scalar(select(Product).where(Product.slug == "simple"))
        box = session.scalar(select(Product).where(Product.slug == "simple-caja-6"))
        almond = session.scalar(select(Product).where(Product.slug == "almendra"))
        almond.active = False
        session.commit()
    mixed = {"slug": "mixta-caja-6", "quantity": 1, "options": {"sixth-brownie": "almendra"}}
    order = client.post("/api/orders", json={"fulfillment": "envio", "items": [mixed]}, headers=auth_headers(customer, "inactive-option-order"))
    sale = client.post("/api/operator/sales", json={"items": [mixed], "paymentMethod": "efectivo", "receivedConfirmed": True}, headers=auth_headers(operator, "inactive-option-sale"))
    assert order.status_code == 422 and sale.status_code == 422
    with factory() as session:
        almond = session.scalar(select(Product).where(Product.slug == "almendra"))
        almond.active = True
        simple = session.scalar(select(Product).where(Product.slug == "simple"))
        simple.active = False
        session.commit()
    for endpoint, body, headers in [
        ("/api/orders", {"fulfillment": "envio", "items": [{"slug": "simple-caja-6", "quantity": 1}]}, auth_headers(customer, "inactive-component-order")),
        ("/api/operator/sales", {"items": [{"slug": "simple-caja-6", "quantity": 1}], "paymentMethod": "efectivo", "receivedConfirmed": True}, auth_headers(operator, "inactive-component-sale")),
    ]:
        assert client.post(endpoint, json=body, headers=headers).status_code == 422
    with factory() as session:
        simple = session.scalar(select(Product).where(Product.slug == "simple"))
        simple.active = True
        box = session.scalar(select(Product).where(Product.slug == "simple-caja-6"))
        component = session.scalar(select(Component).where(Component.parent_id == box.id))
        component.child_id = box.id
        session.commit()
    assert client.post("/api/orders", json={"fulfillment": "envio", "items": [{"slug": "simple-caja-6", "quantity": 1}]}, headers=auth_headers(customer, "cycle-order")).status_code == 422
    assert client.post("/api/operator/sales", json={"items": [{"slug": "simple-caja-6", "quantity": 1}], "paymentMethod": "efectivo", "receivedConfirmed": True}, headers=auth_headers(operator, "cycle-sale")).status_code == 422


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


def test_order_idempotency_key_with_different_logical_payload_is_conflict():
    client, factory = setup_clients()
    token = create_user(factory, "fingerprint@example.com")
    headers = auth_headers(token, "same-logical-key")
    first = client.post("/api/orders", json={"fulfillment": "envio", "items": [{"slug": "simple-caja-6", "quantity": 1}]}, headers=headers)
    different = client.post("/api/orders", json={"fulfillment": "envio", "items": [{"slug": "m-and-m-caja-6", "quantity": 1}]}, headers=headers)
    assert first.status_code == 201
    assert different.status_code == 409
    assert "reintento" in different.json()["error"].lower()


def test_order_replay_uses_historical_intention_after_price_change_and_inactive_product():
    client, factory = setup_clients()
    token = create_user(factory, "historical-order@example.com")
    body = {"fulfillment": "envio", "items": [{"slug": "simple-caja-6", "quantity": 1, "priceCents": 1}]}
    first = client.post("/api/orders", json=body, headers=auth_headers(token, "historical-order"))
    assert first.status_code == 201
    with factory() as session:
        product = session.scalar(select(Product).where(Product.slug == "simple-caja-6"))
        product.price_cents = 999999
        product.active = False
        session.commit()
    replay = client.post("/api/orders", json=body, headers=auth_headers(token, "historical-order"))
    assert replay.status_code == 200
    assert replay.json()["id"] == first.json()["id"]
    assert replay.json()["subtotalCents"] == 6000


def test_sale_replay_uses_historical_intention_after_price_change_and_inactive_product():
    client, factory = setup_clients()
    token = create_user(factory, "historical-operator@example.com", "operator")
    body = {"items": [{"slug": "simple", "quantity": 1, "priceCents": 1}], "paymentMethod": "efectivo", "receivedConfirmed": True}
    first = client.post("/api/operator/sales", json=body, headers=auth_headers(token, "historical-sale"))
    assert first.status_code == 201
    with factory() as session:
        product = session.scalar(select(Product).where(Product.slug == "simple"))
        product.price_cents = 999999
        product.active = False
        session.commit()
    replay = client.post("/api/operator/sales", json=body, headers=auth_headers(token, "historical-sale"))
    assert replay.status_code == 200
    assert replay.json()["id"] == first.json()["id"]
    assert replay.json()["subtotalCents"] == 1000


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


def test_sale_idempotency_key_with_different_logical_payload_is_conflict():
    client, factory = setup_clients()
    operator = create_user(factory, "sale-fingerprint@example.com", "operator")
    headers = auth_headers(operator, "same-sale-key")
    first = client.post("/api/operator/sales", json={"items": [{"slug": "simple", "quantity": 1}], "paymentMethod": "efectivo", "receivedConfirmed": True}, headers=headers)
    different = client.post("/api/operator/sales", json={"items": [{"slug": "m-and-m", "quantity": 1}], "paymentMethod": "efectivo", "receivedConfirmed": True}, headers=headers)
    assert first.status_code == 201
    assert different.status_code == 409
    assert "reintento" in different.json()["error"].lower()


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
    assert visible.json()["orders"][0]["customer"] == {"name": "owner", "email": "owner@example.com", "contactReference": None}
    assert "customer" not in own.json()["orders"][0]
    changed = client.patch(f"/api/operator/orders/{order_id}", json={"status": "CONFIRMADA"}, headers=auth_headers(operator, "order-status"))
    assert changed.status_code == 200 and changed.json()["status"] == "CONFIRMADA"


def test_cors_allows_authenticated_patch_and_idempotency_header_only_from_dev_origin():
    client, _ = setup_clients()
    response = client.options("/api/operator/orders/1", headers={"Origin": ORIGIN, "Access-Control-Request-Method": "PATCH", "Access-Control-Request-Headers": "content-type,idempotency-key"})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ORIGIN
    assert "PATCH" in response.headers["access-control-allow-methods"]
    assert "idempotency-key" in response.headers["access-control-allow-headers"].lower()


def sale_body(**overrides):
    return {"items": [{"slug": "simple", "quantity": 1}], "paymentMethod": "efectivo", "receivedConfirmed": True, **overrides}


def test_sale_replay_with_member_email_survives_member_deactivation():
    client, factory = setup_clients()
    create_user(factory, "miembro@example.com")
    operator = create_user(factory, "op-miembro@example.com", "operator")
    body = sale_body(customerEmail="miembro@example.com")
    first = client.post("/api/operator/sales", json=body, headers=auth_headers(operator, "member-replay"))
    assert first.status_code == 201
    with factory() as session:
        session.scalar(select(User).where(User.email == "miembro@example.com")).active = False
        session.commit()
    replay = client.post("/api/operator/sales", json=body, headers=auth_headers(operator, "member-replay"))
    assert replay.status_code == 200 and replay.json()["id"] == first.json()["id"]


def test_sale_same_key_with_two_different_non_member_emails_is_conflict():
    client, factory = setup_clients()
    operator = create_user(factory, "op-no-miembro@example.com", "operator")
    first = client.post("/api/operator/sales", json=sale_body(customerEmail="uno-externo@example.com"), headers=auth_headers(operator, "non-member-key"))
    second = client.post("/api/operator/sales", json=sale_body(customerEmail="dos-externo@example.com"), headers=auth_headers(operator, "non-member-key"))
    assert first.status_code == 201
    assert second.status_code == 409
    replay = client.post("/api/operator/sales", json=sale_body(customerEmail=" UNO-externo@example.com "), headers=auth_headers(operator, "non-member-key"))
    assert replay.status_code == 200 and replay.json()["id"] == first.json()["id"]


def test_legacy_sale_intention_with_customer_id_replays_after_member_deactivation():
    client, factory = setup_clients()
    create_user(factory, "legado@example.com")
    operator = create_user(factory, "op-legado@example.com", "operator")
    body = sale_body(customerEmail="legado@example.com")
    first = client.post("/api/operator/sales", json=body, headers=auth_headers(operator, "legacy-intent"))
    assert first.status_code == 201
    with factory() as session:
        sale = session.get(Sale, first.json()["id"])
        member = session.scalar(select(User).where(User.email == "legado@example.com"))
        sale.idempotency_intent_json = '{"customerId": %d, "customerName": null, "items": [{"options": {}, "quantity": 1, "slug": "simple"}], "paymentMethod": "EFECTIVO", "receivedConfirmed": true, "reference": null}' % member.id
        member.active = False
        session.commit()
    replay = client.post("/api/operator/sales", json=body, headers=auth_headers(operator, "legacy-intent"))
    assert replay.status_code == 200 and replay.json()["id"] == first.json()["id"]
    with factory() as session:
        session.get(Sale, first.json()["id"]).idempotency_intent_json = None
        session.commit()
    pre_009 = client.post("/api/operator/sales", json=body, headers=auth_headers(operator, "legacy-intent"))
    assert pre_009.status_code == 200 and pre_009.json()["id"] == first.json()["id"]


def test_invalid_payment_types_are_422_not_500():
    client, factory = setup_clients()
    customer = create_user(factory, "tipos@example.com")
    operator = create_user(factory, "op-tipos@example.com", "operator")
    for index, intent in enumerate([{"x": 1}, ["AL_PEDIR"], 1, True]):
        response = client.post("/api/orders", json={"fulfillment": "envio", "paymentIntent": intent, "items": [{"slug": "simple-caja-6", "quantity": 1}]}, headers=auth_headers(customer, f"bad-intent-{index}"))
        assert response.status_code == 422, intent
    for index, method in enumerate([{"x": 1}, ["efectivo"], 1, None]):
        response = client.post("/api/operator/sales", json=sale_body(paymentMethod=method), headers=auth_headers(operator, f"bad-method-{index}"))
        assert response.status_code == 422, method
    response = client.post("/api/operator/sales", json=sale_body(customerEmail={"x": 1}), headers=auth_headers(operator, "bad-email"))
    assert response.status_code == 422


def test_falsy_non_dict_options_are_422_for_new_operation_and_replay():
    client, factory = setup_clients()
    operator = create_user(factory, "op-opciones@example.com", "operator")
    ok = client.post("/api/operator/sales", json=sale_body(), headers=auth_headers(operator, "options-replay"))
    assert ok.status_code == 201
    for index, options in enumerate([[], False, 0, ""]):
        body = sale_body(items=[{"slug": "simple", "quantity": 1, "options": options}])
        fresh = client.post("/api/operator/sales", json=body, headers=auth_headers(operator, f"options-new-{index}"))
        replay = client.post("/api/operator/sales", json=body, headers=auth_headers(operator, "options-replay"))
        assert fresh.status_code == 422, options
        assert replay.status_code == 422, options


def test_order_status_with_non_string_type_is_422_not_500():
    client, factory = setup_clients()
    customer = create_user(factory, "estado-tipo@example.com")
    operator = create_user(factory, "op-estado-tipo@example.com", "operator")
    created = client.post("/api/orders", json={"fulfillment": "envio", "items": [{"slug": "simple-caja-6", "quantity": 1}]}, headers=auth_headers(customer, "status-type"))
    order_id = created.json()["id"]
    for index, status in enumerate([["CONFIRMADA"], {"x": 1}, 1, None]):
        response = client.patch(f"/api/operator/orders/{order_id}", json={"status": status}, headers=auth_headers(operator, f"status-type-{index}"))
        assert response.status_code == 422, status
