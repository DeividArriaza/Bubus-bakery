from pathlib import Path
from typing import Callable

from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from .models import Base, Component, Option, OptionGroup, Product

ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "migrations"


def make_engine(database_url: str) -> Engine:
    kwargs = {"pool_pre_ping": True}
    if database_url.startswith("sqlite"):
        kwargs.update({"connect_args": {"check_same_thread": False}})
    return create_engine(database_url, **kwargs)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def apply_migrations(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE IF NOT EXISTS schema_migrations (version VARCHAR(40) PRIMARY KEY)"))
        applied = {row[0] for row in connection.execute(text("SELECT version FROM schema_migrations"))}
        for migration in sorted(MIGRATIONS.glob("*.sql")):
            version = migration.name.split("_", 1)[0]
            if version in applied:
                continue
            migration_sql = "\n".join(line for line in migration.read_text().splitlines() if not line.strip().startswith("--"))
            statements = [statement.strip() for statement in migration_sql.split(";") if statement.strip()]
            for statement in statements:
                connection.execute(text(statement))
            connection.execute(text("INSERT INTO schema_migrations (version) VALUES (:version)"), {"version": version})


def init_test_database(engine: Engine) -> None:
    Base.metadata.create_all(engine)


def create_test_session() -> tuple[sessionmaker[Session], Engine]:
    engine = create_engine("sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    return make_session_factory(engine), engine


def _ensure_product(session: Session, values: dict) -> tuple[Product, bool]:
    item = session.scalar(select(Product).where(Product.slug == values["slug"]))
    if item is not None:
        return item, False
    item = Product(**values)
    session.add(item)
    session.flush()
    return item, True


def _add_components_if_empty(session: Session, parent: Product, components: list[tuple[Product, int]]) -> None:
    existing_child_ids = set(session.scalars(select(Component.child_id).where(Component.parent_id == parent.id)))
    session.add_all([
        Component(parent_id=parent.id, child_id=child.id, quantity=quantity)
        for child, quantity in components
        if child.id not in existing_child_ids
    ])


def _add_mixed_options_if_missing(session: Session, parent: Product, almond: Product, simple: Product) -> None:
    group = session.scalar(select(OptionGroup).where(OptionGroup.product_id == parent.id, OptionGroup.code == "sixth-brownie"))
    if group is None:
        group = OptionGroup(product_id=parent.id, code="sixth-brownie", label="Elige el sexto brownie", min_selections=1, max_selections=1)
        session.add(group)
        session.flush()
    existing_product_ids = set(session.scalars(select(Option.product_id).where(Option.group_id == group.id)))
    session.add_all([
        Option(group_id=group.id, product_id=product.id, quantity=1)
        for product in (almond, simple)
        if product.id not in existing_product_ids
    ])


def seed_catalog(session_factory: Callable[[], Session]) -> None:
    seed = [
        ("simple", "Simple", "individual", "Chocolate intenso y textura fudgy.", 1000, "individual"),
        ("m-and-m", "M&M", "individual", "Brownie con M&M.", 1500, "individual"),
        ("snickers", "Snickers", "individual", "Brownie con caramelo y Snickers.", 1700, "individual"),
        ("almendra", "Almendra", "individual", "Brownie con almendra.", 1500, "individual"),
        ("simple-caja-6", "Caja de 6 Simple", "composite", "Seis brownies Simple.", 6000, "caja6"),
        ("m-and-m-caja-6", "Caja de 6 M&M", "composite", "Seis brownies M&M.", 7500, "caja6"),
        ("snickers-caja-6", "Caja de 6 Snickers", "composite", "Seis brownies Snickers.", 8000, "caja6"),
        ("almendra-caja-6", "Caja de 6 Almendra", "composite", "Seis brownies de almendra.", 7000, "caja6"),
        ("mixta-caja-6", "Caja mixta", "composite", "Seis brownies con una elección limitada.", 8500, "caja6"),
    ]
    with session_factory() as session:
        products: dict[str, Product] = {}
        for slug, name, kind, description, price_cents, presentation in seed:
            products[slug], _ = _ensure_product(session, {
                "slug": slug, "name": name, "kind": kind, "description": description,
                "price_cents": price_cents, "category": "brownie", "presentation": presentation, "active": True,
            })
        for slug, child_slug in [("simple-caja-6", "simple"), ("m-and-m-caja-6", "m-and-m"), ("snickers-caja-6", "snickers"), ("almendra-caja-6", "almendra")]:
            _add_components_if_empty(session, products[slug], [(products[child_slug], 6)])
        _add_components_if_empty(session, products["mixta-caja-6"], [(products["snickers"], 2), (products["m-and-m"], 3)])
        _add_mixed_options_if_missing(session, products["mixta-caja-6"], products["almendra"], products["simple"])
        session.commit()


def catalog_data(session_factory: Callable[[], Session]) -> list[dict]:
    from .commerce import sellable_product_ids

    with session_factory() as session:
        all_products, sellable_ids = sellable_product_ids(session)
        products = [product for product in all_products.values() if product.id in sellable_ids]
        names = {product.id: product.slug for product in all_products.values()}
        result = []
        for product in products:
            components = session.scalars(select(Component).where(Component.parent_id == product.id).order_by(Component.id))
            groups = session.scalars(select(OptionGroup).where(OptionGroup.product_id == product.id).order_by(OptionGroup.id))
            option_groups = []
            for group in groups:
                options = [option for option in session.scalars(select(Option).where(Option.group_id == group.id).order_by(Option.id)) if option.product_id in sellable_ids]
                option_groups.append({
                    "code": group.code, "label": group.label, "minSelections": group.min_selections,
                    "maxSelections": group.max_selections,
                    "options": [{"product": names[option.product_id], "quantity": option.quantity} for option in options],
                })
            result.append({
                "slug": product.slug, "name": product.name, "kind": product.kind, "category": product.category,
                "presentation": product.presentation, "description": product.description, "currency": "GTQ",
                "priceCents": product.price_cents,
                # Compatibilidad temporal para consumidores de la primera entrega; la fuente es price_cents.
                "prices": {product.presentation: product.price_cents},
                "composition": [{"product": names[component.child_id], "quantity": component.quantity} for component in components],
                "optionGroups": option_groups,
            })
        return result
