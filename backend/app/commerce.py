import hashlib
import json
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Component, Option, OptionGroup, Order, OrderItem, Product, Sale, SaleItem, User

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
        allowed = {
            option.product_id: option
            for option in session.scalars(select(Option).where(Option.group_id == group.id))
            if option.product_id in product_slugs
        }
        if group.min_selections and not allowed:
            raise _error(f"No hay opciones disponibles para {group.label.lower()}.")
        product_id = next((pid for pid, slug in product_slugs.items() if slug == choice), None)
        option = allowed.get(product_id)
        if option is None:
            raise _error(f"La opción elegida para {group.label.lower()} no es válida.")
        selected.append({"group": group.code, "product": choice, "quantity": option.quantity})
    return selected


def sellable_product_ids(session: Session) -> tuple[dict[int, Product], set[int]]:
    all_products = {product.id: product for product in session.scalars(select(Product))}
    components = {}
    for component in session.scalars(select(Component).order_by(Component.id)):
        components.setdefault(component.parent_id, []).append(component)
    groups = {}
    for group in session.scalars(select(OptionGroup).order_by(OptionGroup.id)):
        groups.setdefault(group.product_id, []).append(group)
    options = {}
    for option in session.scalars(select(Option).order_by(Option.id)):
        options.setdefault(option.group_id, []).append(option)
    memo: dict[int, bool] = {}

    def valid(product_id: int, path: set[int]) -> bool:
        if product_id in memo:
            return memo[product_id]
        product = all_products.get(product_id)
        if product is None or not product.active or product_id in path:
            memo[product_id] = False
            return False
        next_path = path | {product_id}
        for component in components.get(product_id, []):
            if component.quantity < 1 or not valid(component.child_id, next_path):
                memo[product_id] = False
                return False
        for group in groups.get(product_id, []):
            active_options = [option for option in options.get(group.id, []) if valid(option.product_id, next_path)]
            if len(active_options) < group.min_selections or group.max_selections < group.min_selections:
                memo[product_id] = False
                return False
        memo[product_id] = True
        return True

    for product_id in all_products:
        valid(product_id, set())
    return all_products, {product_id for product_id, is_valid in memo.items() if is_valid}


def calculate_items(session: Session, raw_items: object, *, delivery_only_boxes: bool) -> tuple[list[dict], int]:
    if not isinstance(raw_items, list) or not raw_items or len(raw_items) > MAX_LINES:
        raise _error(f"Incluye entre 1 y {MAX_LINES} productos.")
    slugs = [item.get("slug") if isinstance(item, dict) else None for item in raw_items]
    all_by_id, sellable_ids = sellable_product_ids(session)
    products = {product.slug: product for product in all_by_id.values() if product.id in sellable_ids and product.slug in slugs}
    product_ids = {product.id: product.slug for product in all_by_id.values() if product.id in sellable_ids}
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
        if any(component.child_id not in product_ids for component in components):
            raise _error("La composición de este producto ya no está disponible.")
        composition = [{"product": product_ids[component.child_id], "quantity": component.quantity} for component in components]
        selected = _selected_options(session, product, raw.get("options"), product_ids)
        if not components and product.presentation == "caja6":
            raise _error("La composición de esta caja no está disponible.")
        snapshot = {"composition": composition, "selectedOptions": selected}
        snapshots.append({"product": product, "quantity": quantity, "snapshot": snapshot, "lineTotalCents": product.price_cents * quantity})
        subtotal += product.price_cents * quantity
    return snapshots, subtotal


def payload_fingerprint(payload: dict) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def normalize_intention_items(raw_items: object) -> list[dict]:
    if not isinstance(raw_items, list) or not raw_items or len(raw_items) > MAX_LINES:
        raise _error(f"Incluye entre 1 y {MAX_LINES} productos.")
    normalized = []
    for raw in raw_items:
        if not isinstance(raw, dict) or not isinstance(raw.get("slug"), str) or not raw["slug"].strip():
            raise _error("Uno de los productos no es válido.")
        quantity = raw.get("quantity")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1 or quantity > MAX_QUANTITY:
            raise _error(f"La cantidad debe ser un entero entre 1 y {MAX_QUANTITY}.")
        raw_options = raw.get("options") or {}
        if not isinstance(raw_options, dict) or any(not isinstance(key, str) or not isinstance(value, str) for key, value in raw_options.items()):
            raise _error("Las opciones del producto no son válidas.")
        normalized.append({"slug": raw["slug"].strip(), "quantity": quantity, "options": {key: raw_options[key] for key in sorted(raw_options)}})
    return normalized


def order_intention(*, fulfillment: object, payment_intent: object, contact_reference: object, raw_items: object) -> dict:
    if fulfillment != "envio":
        raise _error("Por ahora las solicitudes web son únicamente para envío.")
    if payment_intent not in {"NO_DEFINIDO", "AL_PEDIR", "AL_RECIBIR"}:
        raise _error("La intención de pago no es válida.")
    if contact_reference is not None and (not isinstance(contact_reference, str) or len(contact_reference.strip()) > 120):
        raise _error("La referencia de contacto es demasiado larga.")
    return {
        "fulfillment": "envio",
        "paymentIntent": payment_intent,
        "contactReference": contact_reference.strip() if isinstance(contact_reference, str) else None,
        "items": normalize_intention_items(raw_items),
    }


def sale_intention(*, payment_method: object, customer_id: int | None, customer_name: object, reference: object, received_confirmed: object, raw_items: object) -> dict:
    if payment_method not in {"efectivo", "transferencia", "EFECTIVO", "TRANSFERENCIA"}:
        raise _error("El medio debe ser efectivo o transferencia.")
    if customer_name is not None and (not isinstance(customer_name, str) or len(customer_name.strip()) > 120):
        raise _error("El nombre del cliente es demasiado largo.")
    if reference is not None and (not isinstance(reference, str) or len(reference.strip()) > 120):
        raise _error("La referencia es demasiado larga.")
    if received_confirmed is not True:
        raise _error("El operador debe confirmar explícitamente la recepción del pago.")
    return {
        "paymentMethod": payment_method.upper(),
        "customerId": customer_id,
        "customerName": customer_name.strip() if isinstance(customer_name, str) else None,
        "reference": reference.strip() if isinstance(reference, str) else None,
        "receivedConfirmed": True,
        "items": normalize_intention_items(raw_items),
    }


def historical_order_intention(order: Order, items: list[OrderItem]) -> dict:
    return {
        "fulfillment": order.fulfillment,
        "paymentIntent": order.payment_intent,
        "contactReference": order.contact_reference,
        "items": [{"slug": item.product_slug, "quantity": item.quantity, "options": {option["group"]: option["product"] for option in json.loads(item.snapshot_json).get("selectedOptions", [])}} for item in items],
    }


def historical_sale_intention(sale: Sale, items: list[SaleItem]) -> dict:
    return {
        "paymentMethod": sale.payment_method,
        "customerId": sale.customer_id,
        "customerName": sale.customer_name,
        "reference": sale.reference,
        "receivedConfirmed": True,
        "items": [{"slug": item.product_slug, "quantity": item.quantity, "options": {option["group"]: option["product"] for option in json.loads(item.snapshot_json).get("selectedOptions", [])}} for item in items],
    }


def order_fingerprint_data(order: Order, items: list[OrderItem]) -> dict:
    return {
        "fulfillment": order.fulfillment,
        "paymentIntent": order.payment_intent,
        "contactReference": order.contact_reference,
        "subtotalCents": order.subtotal_cents,
        "items": [{"slug": item.product_slug, "quantity": item.quantity, "snapshot": json.loads(item.snapshot_json)} for item in items],
    }


def sale_fingerprint_data(sale: Sale, items: list[SaleItem]) -> dict:
    return {
        "paymentMethod": sale.payment_method,
        "customerId": sale.customer_id,
        "customerName": sale.customer_name,
        "reference": sale.reference,
        "subtotalCents": sale.subtotal_cents,
        "items": [{"slug": item.product_slug, "quantity": item.quantity, "snapshot": json.loads(item.snapshot_json)} for item in items],
    }


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def order_json(session: Session, order: Order, *, include_customer: bool = False) -> dict:
    items = list(session.scalars(select(OrderItem).where(OrderItem.order_id == order.id).order_by(OrderItem.id)))
    result = {"id": order.id, "status": order.status, "paymentStatus": order.payment_status, "paymentIntent": order.payment_intent, "deliveryStatus": order.delivery_status, "fulfillment": order.fulfillment, "subtotalCents": order.subtotal_cents, "shippingAmountCents": order.shipping_amount_cents, "totalFinalCents": order.total_final_cents, "contactReference": order.contact_reference, "createdAt": order.created_at.isoformat(), "items": [{"slug": item.product_slug, "name": item.product_name, "unitPriceCents": item.unit_price_cents, "quantity": item.quantity, **json.loads(item.snapshot_json)} for item in items]}
    if include_customer:
        customer = session.get(User, order.customer_id)
        result["customer"] = {"name": customer.name, "email": customer.email, "contactReference": order.contact_reference} if customer is not None else None
    return result


def sale_json(session: Session, sale: Sale) -> dict:
    items = list(session.scalars(select(SaleItem).where(SaleItem.sale_id == sale.id).order_by(SaleItem.id)))
    return {"id": sale.id, "paymentMethod": sale.payment_method, "paymentStatus": sale.payment_status, "subtotalCents": sale.subtotal_cents, "customerName": sale.customer_name, "reference": sale.reference, "createdAt": sale.created_at.isoformat(), "items": [{"slug": item.product_slug, "name": item.product_name, "unitPriceCents": item.unit_price_cents, "quantity": item.quantity, **json.loads(item.snapshot_json)} for item in items]}
