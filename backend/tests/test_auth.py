from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import create_test_session, init_test_database
from app.main import create_app
from app.models import AppSession, User


ORIGIN = "http://localhost:5173"


def auth_client():
    session_factory, engine = create_test_session()
    init_test_database(engine)
    return TestClient(create_app(session_factory)), session_factory


def register_payload(email="cliente@ejemplo.com", password="UnaClaveSegura123!"):
    return {"email": email, "password": password, "name": "Cliente Bubu"}


def test_register_normalizes_email_hashes_password_and_creates_customer_session():
    client, session_factory = auth_client()
    response = client.post("/api/auth/register", json=register_payload(" Cliente@Ejemplo.COM "), headers={"Origin": ORIGIN})
    assert response.status_code == 201
    assert response.json() == {"user": {"email": "cliente@ejemplo.com", "name": "Cliente Bubu", "role": "customer", "emailVerified": False}}
    assert response.cookies.get("bubus_session")
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie and "secure" not in cookie
    with session_factory() as session:
        user = session.scalar(select(User).where(User.email == "cliente@ejemplo.com"))
        stored_session = session.scalar(select(AppSession).where(AppSession.user_id == user.id))
        assert user.password_hash != "UnaClaveSegura123!"
        assert user.role == "customer"
        assert user.email_verified is False
        assert stored_session.token_hash != response.cookies.get("bubus_session")


def test_login_session_logout_and_revocation_protect_private_session():
    client, session_factory = auth_client()
    client.post("/api/auth/register", json=register_payload(), headers={"Origin": ORIGIN})
    client.post("/api/auth/logout", headers={"Origin": ORIGIN})
    assert client.get("/api/auth/session").status_code == 401
    login = client.post("/api/auth/login", json={"email": "CLIENTE@EJEMPLO.COM", "password": "UnaClaveSegura123!"}, headers={"Origin": ORIGIN})
    assert login.status_code == 200
    assert login.json()["user"]["email"] == "cliente@ejemplo.com"
    assert client.get("/api/auth/session").status_code == 200
    assert client.post("/api/auth/logout", headers={"Origin": ORIGIN}).status_code == 204
    assert client.get("/api/auth/session").status_code == 401
    with session_factory() as session:
        stored = session.scalar(select(AppSession).order_by(AppSession.id.desc()))
        assert stored.revoked_at is not None


def test_auth_errors_are_spanish_and_duplicate_email_is_rejected():
    client, _ = auth_client()
    missing_origin = client.post("/api/auth/register", json=register_payload())
    assert missing_origin.status_code == 403
    assert "origen" in missing_origin.json()["error"].lower()
    assert client.post("/api/auth/register", json=register_payload(), headers={"Origin": ORIGIN}).status_code == 201
    duplicate = client.post("/api/auth/register", json=register_payload("CLIENTE@EJEMPLO.COM"), headers={"Origin": ORIGIN})
    assert duplicate.status_code == 409
    assert "correo" in duplicate.json()["error"].lower()
    wrong = client.post("/api/auth/login", json={"email": "cliente@ejemplo.com", "password": "incorrecta"}, headers={"Origin": ORIGIN})
    assert wrong.status_code == 401
    assert wrong.json() == {"error": "Correo o contraseña incorrectos."}


def test_customer_cannot_escalate_role_and_expired_or_revoked_sessions_are_denied():
    client, session_factory = auth_client()
    response = client.post("/api/auth/register", json={**register_payload(), "role": "operator"}, headers={"Origin": ORIGIN})
    assert response.status_code == 201
    assert response.json()["user"]["role"] == "customer"
    with session_factory() as session:
        stored = session.scalar(select(AppSession).order_by(AppSession.id.desc()))
        stored.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        session.commit()
    assert client.get("/api/auth/session").status_code == 401


def test_google_is_explicitly_unconfigured_without_fake_login():
    client, _ = auth_client()
    response = client.get("/api/auth/google/start")
    assert response.status_code == 503
    assert response.json() == {"error": "El acceso con Google aún no está configurado."}
