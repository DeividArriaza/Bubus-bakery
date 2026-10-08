import json
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Component, Option, OptionGroup, Order, OrderItem, Product, Sale, SaleItem

MAX_LINES = 20
MAX_QUANTITY = 50


def _error(message: str) -> HTTPException:
    return HTTPException(status_code=422, detail=message)


def _selected_options(session: Session, product: Product, raw_options: object, product_slugs: dict[int, str]) -> list[dict]:
    groups = list(session.scalars(select(OptionGroup).where(OptionGroup.product_id == product.id).order_by(OptionGroup.id)))
    if raw_options is None:
        raw_options = {}
    if not isinstance(raw_options, dict):
        raise _error("Las opciones del producto no son válidas.")
    known_codes = {group.code for group in groups}
    if set(raw_options) - known_codes:
        raise _error("La opción seleccionada no pertenece a este producto.")
    selected: list[dict] = []
    for group in groups:
        choice = raw_options.get(group.code)
        if group.min_selections == 1 and group.max_selections == 1 and not isinstance(choice, str):
            raise _error(f"Debes hacer una elección para {group.label.lower()}.")
        allowed = {option.product_id: option for option in session.scalars(select(Option).where(Option.group_id == group.id))}
        product_id = next((pid for pid, slug in product_slugs.items() if slug == choice), None)
        option = allowed.get(product_id)
        if option is None:
            raise _error(f"La opción elegida para {group.label.lower()} no es válida.")
        selected.append({"group": group.code, "product": choice, "quantity": option.quantity})
    return selected


def calculate_items(session: Session, raw_items: object, *, delivery_only_boxes: bool) -> tuple[list[dict], int]:
    if not isinstance(raw_items, list) or not raw_items or len(raw_items) > MAX_LINES:
        raise _error(f"Incluye entre 1 y {MAX_LINES} productos.")
    slugs = [item.get("slug") if isinstance(item, dict) else None for item in raw_items]
    all_products = list(session.scalars(select(Product).where(Product.active.is_(True))))
    products = {product.slug: product for product in all_products if product.slug in slugs}
    product_ids = {product.id: product.slug for product in all_products}
    snapshots: list[dict] = []
    subtotal = 0
    for raw in raw_items:
        if not isinstance(raw, dict) or raw.get("slug") not in products:
            raise _error("Uno de los productos ya no está disponible.")
        quantity = raw.get("quantity")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1 or quantity > MAX_QUANTITY:
            raise _error(f"La cantidad debe ser un entero entre 1 y {MAX_QUANTITY}.")
        product = products[raw["slug"]]
        if delivery_only_boxes and product.presentation != "caja6":
            raise _error("Las solicitudes para envío solo admiten cajas de 6.")
        components = list(session.scalars(select(Component).where(Component.parent_id == product.id).order_by(Component.id)))
        composition = [{"product": product_ids.get(component.child_id, "producto"), "quantity": component.quantity} for component in components]
        selected = _selected_options(session, product, raw.get("options"), product_ids)
        if not components and product.presentation == "caja6":
            raise _error("La composición de esta caja no está disponible.")
        snapshot = {"composition": composition, "selectedOptions": selected}
        snapshots.append({"product": product, "quantity": quantity, "snapshot": snapshot, "lineTotalCents": product.price_cents * quantity})
        subtotal += product.price_cents * quantity
    return snapshots, subtotal


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def order_json(session: Session, order: Order) -> dict:
    items = list(session.scalars(select(OrderItem).where(OrderItem.order_id == order.id).order_by(OrderItem.id)))
    return {"id": order.id, "status": order.status, "paymentStatus": order.payment_status, "paymentIntent": order.payment_intent, "deliveryStatus": order.delivery_status, "fulfillment": order.fulfillment, "subtotalCents": order.subtotal_cents, "shippingAmountCents": order.shipping_amount_cents, "totalFinalCents": order.total_final_cents, "contactReference": order.contact_reference, "createdAt": order.created_at.isoformat(), "items": [{"slug": item.product_slug, "name": item.product_name, "unitPriceCents": item.unit_price_cents, "quantity": item.quantity, **json.loads(item.snapshot_json)} for item in items]}


def sale_json(session: Session, sale: Sale) -> dict:
    items = list(session.scalars(select(SaleItem).where(SaleItem.sale_id == sale.id).order_by(SaleItem.id)))
    return {"id": sale.id, "paymentMethod": sale.payment_method, "paymentStatus": sale.payment_status, "subtotalCents": sale.subtotal_cents, "customerName": sale.customer_name, "createdAt": sale.created_at.isoformat(), "items": [{"slug": item.product_slug, "name": item.product_name, "unitPriceCents": item.unit_price_cents, "quantity": item.quantity, **json.loads(item.snapshot_json)} for item in items]}
