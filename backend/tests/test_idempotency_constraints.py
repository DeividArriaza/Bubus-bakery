from types import SimpleNamespace

from sqlalchemy.exc import IntegrityError

from app.commerce import is_idempotency_unique


class _PgUniqueViolation(Exception):
    sqlstate = "23505"

    def __init__(self, constraint: str):
        super().__init__(f'duplicate key value violates unique constraint "{constraint}"')
        self.diag = SimpleNamespace(constraint_name=constraint)


def _pg_error(constraint: str) -> IntegrityError:
    return IntegrityError("INSERT", {}, _PgUniqueViolation(constraint))


def _sqlite_error(message: str) -> IntegrityError:
    return IntegrityError("INSERT", {}, Exception(message))


def test_only_exact_postgres_idempotency_constraints_are_absorbed():
    assert is_idempotency_unique(_pg_error("orders_customer_id_idempotency_key_key"), "order")
    assert is_idempotency_unique(_pg_error("sales_actor_id_idempotency_key_key"), "sale")
    assert not is_idempotency_unique(_pg_error("sales_actor_id_idempotency_key_key"), "order")
    assert not is_idempotency_unique(_pg_error("orders_reference_key"), "order")
    assert not is_idempotency_unique(_pg_error("sales_payload_fingerprint_key"), "sale")
    assert not is_idempotency_unique(_pg_error("idempotency_audit_key"), "sale")


def test_only_exact_sqlite_idempotency_constraints_are_absorbed():
    assert is_idempotency_unique(_sqlite_error("UNIQUE constraint failed: orders.customer_id, orders.idempotency_key"), "order")
    assert is_idempotency_unique(_sqlite_error("UNIQUE constraint failed: sales.actor_id, sales.idempotency_key"), "sale")
    assert not is_idempotency_unique(_sqlite_error("UNIQUE constraint failed: sales.reference"), "sale")
    assert not is_idempotency_unique(_sqlite_error("NOT NULL constraint failed: sales.idempotency_key"), "sale")
