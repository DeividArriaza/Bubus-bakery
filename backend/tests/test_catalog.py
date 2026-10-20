from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.db import create_test_session, init_test_database, seed_catalog
from app.main import create_app
from app.models import Component, Option, Product


def client_with_catalog():
    session_factory, engine = create_test_session()
    init_test_database(engine)
    seed_catalog(session_factory)
    return TestClient(create_app(session_factory))


def test_health_reports_api_ready():
    response = client_with_catalog().get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "servicio": "api"}


def test_catalog_has_nine_sellable_prices_and_compositions():
    response = client_with_catalog().get("/api/catalog")
    assert response.status_code == 200
    products = {product["slug"]: product for product in response.json()["products"]}

    assert len(products) == 9
    assert {slug: products[slug]["priceCents"] for slug in products} == {
        "simple": 1000, "simple-caja-6": 6000,
        "m-and-m": 1500, "m-and-m-caja-6": 7500,
        "snickers": 1700, "snickers-caja-6": 8000,
        "almendra": 1500, "almendra-caja-6": 7000,
        "mixta-caja-6": 8500,
    }
    assert products["simple-caja-6"]["composition"] == [{"product": "simple", "quantity": 6}]
    assert products["m-and-m-caja-6"]["composition"] == [{"product": "m-and-m", "quantity": 6}]
    assert products["snickers-caja-6"]["composition"] == [{"product": "snickers", "quantity": 6}]
    assert products["almendra-caja-6"]["composition"] == [{"product": "almendra", "quantity": 6}]
    mixture = products["mixta-caja-6"]
    assert mixture["composition"] == [{"product": "snickers", "quantity": 2}, {"product": "m-and-m", "quantity": 3}]
    assert mixture["optionGroups"] == [{
        "code": "sixth-brownie", "label": "Elige el sexto brownie", "minSelections": 1, "maxSelections": 1,
        "options": [{"product": "almendra", "quantity": 1}, {"product": "simple", "quantity": 1}],
    }]


def test_seed_inserts_missing_without_overwriting_catalog_changes():
    session_factory, engine = create_test_session()
    init_test_database(engine)
    seed_catalog(session_factory)
    with session_factory() as session:
        simple = session.scalar(select(Product).where(Product.slug == "simple"))
        box = session.scalar(select(Product).where(Product.slug == "simple-caja-6"))
        component = session.scalar(select(Component).where(Component.parent_id == box.id))
        simple.name = "Nombre editado por la dueña"
        simple.price_cents = 1111
        component.quantity = 4
        session.commit()
    seed_catalog(session_factory)
    with session_factory() as session:
        simple = session.scalar(select(Product).where(Product.slug == "simple"))
        box = session.scalar(select(Product).where(Product.slug == "simple-caja-6"))
        component = session.scalar(select(Component).where(Component.parent_id == box.id))
        assert simple.name == "Nombre editado por la dueña"
        assert simple.price_cents == 1111
        assert component.quantity == 4
    assert len(client_with_catalog().get("/api/catalog").json()["products"]) == 9


def test_catalog_database_error_is_spanish():
    def broken_session():
        raise SQLAlchemyError("fallo controlado")

    response = TestClient(create_app(broken_session)).get("/api/catalog")
    assert response.status_code == 503
    assert response.json() == {"error": "No pudimos cargar el catálogo en este momento."}


def test_active_catalog_compositions_are_acyclic_and_prices_are_product_owned():
    session_factory, engine = create_test_session()
    init_test_database(engine)
    seed_catalog(session_factory)
    with session_factory() as session:
        products = {product.id: product for product in session.scalars(select(Product).where(Product.active.is_(True)))}
        graph = {product_id: [component.child_id for component in session.scalars(select(Component).where(Component.parent_id == product_id))] for product_id in products}
        def visit(node, path):
            assert node not in path, "el catálogo no puede contener ciclos de composición"
            for child in graph.get(node, []):
                visit(child, path | {node})
        for product_id in products:
            visit(product_id, set())
        assert all(product.price_cents >= 0 for product in products.values())


def test_inactive_options_are_hidden_and_cannot_be_selected():
    session_factory, engine = create_test_session()
    init_test_database(engine)
    seed_catalog(session_factory)
    with session_factory() as session:
        almond = session.scalar(select(Product).where(Product.slug == "almendra"))
        almond.active = False
        session.commit()
    client = TestClient(create_app(session_factory))
    catalog = {item["slug"]: item for item in client.get("/api/catalog").json()["products"]}
    assert catalog["mixta-caja-6"]["optionGroups"][0]["options"] == [{"product": "simple", "quantity": 1}]

    from app.tests_helpers import authenticated_customer

    token = authenticated_customer(session_factory, "inactiva@example.com")
    response = client.post(
        "/api/orders",
        json={"fulfillment": "envio", "items": [{"slug": "mixta-caja-6", "quantity": 1, "options": {"sixth-brownie": "almendra"}}]},
        headers={"Origin": "http://localhost:5173", "Cookie": f"bubus_session={token}", "Idempotency-Key": "inactive-option"},
    )
    assert response.status_code == 422
    assert "válida" in response.json()["error"]


def test_inactive_component_and_cycle_make_parent_not_sellable_without_placeholder():
    session_factory, engine = create_test_session()
    init_test_database(engine)
    seed_catalog(session_factory)
    with session_factory() as session:
        child = session.scalar(select(Product).where(Product.slug == "simple"))
        parent = session.scalar(select(Product).where(Product.slug == "simple-caja-6"))
        child.active = False
        session.commit()
    client = TestClient(create_app(session_factory))
    catalog = {item["slug"]: item for item in client.get("/api/catalog").json()["products"]}
    assert "simple-caja-6" not in catalog

    with session_factory() as session:
        child = session.scalar(select(Product).where(Product.slug == "simple"))
        child.active = True
        parent = session.scalar(select(Product).where(Product.slug == "simple-caja-6"))
        component = session.scalar(select(Component).where(Component.parent_id == parent.id))
        component.child_id = parent.id
        session.commit()
    catalog_response = client.get("/api/catalog")
    assert catalog_response.status_code == 200
    assert "simple-caja-6" not in {item["slug"] for item in catalog_response.json()["products"]}
