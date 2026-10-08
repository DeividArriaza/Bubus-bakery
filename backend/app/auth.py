import hashlib
import hmac
import secrets
import threading
import time
import unicodedata
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Callable

from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from .models import AppSession, User

SESSION_COOKIE = "bubus_session"
SESSION_DAYS = 7
PASSWORD_SCRYPT_N = 2**14
PASSWORD_SCRYPT_R = 8
PASSWORD_SCRYPT_P = 1
PASSWORD_MIN_LENGTH = 12
PASSWORD_MAX_LENGTH = 128


class AuthRateLimiter:
    """Límite acotado por proceso; no pretende ser distribuido entre workers."""

    def __init__(self, attempts: int = 5, window_seconds: int = 60, max_entries: int = 10_000):
        self.attempts = max(1, attempts)
        self.window_seconds = max(1, window_seconds)
        self.max_entries = max(100, max_entries)
        self._entries: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def check(self, keys: list[str]) -> int | None:
        now = time.monotonic()
        with self._lock:
            for key in keys:
                events = self._entries.get(key)
                if events is not None:
                    while events and events[0] <= now - self.window_seconds:
                        events.popleft()
                    if not events:
                        self._entries.pop(key, None)
            retry_after = 0
            for key in keys:
                events = self._entries.get(key, ())
                if len(events) >= self.attempts:
                    retry_after = max(retry_after, int(events[0] + self.window_seconds - now + 0.999))
            if retry_after:
                return max(1, retry_after)
            for key in keys:
                self._entries.setdefault(key, deque()).append(now)
            while len(self._entries) > self.max_entries:
                self._entries.pop(next(iter(self._entries)))
            return None

    def clear(self, key: str) -> None:
        with self._lock:
            self._entries.pop(key, None)


def normalize_email(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("El correo es obligatorio.")
    email = unicodedata.normalize("NFKC", value).strip().casefold()
    if len(email) > 320 or email.count("@") != 1:
        raise ValueError("Ingresa un correo válido.")
    local, domain = email.rsplit("@", 1)
    if not local or not domain or "." not in domain or any(character.isspace() for character in email):
        raise ValueError("Ingresa un correo válido.")
    return email


def hash_password(password: object) -> str:
    validate_password(password)
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=PASSWORD_SCRYPT_N, r=PASSWORD_SCRYPT_R, p=PASSWORD_SCRYPT_P)
    return f"scrypt${PASSWORD_SCRYPT_N}${PASSWORD_SCRYPT_R}${PASSWORD_SCRYPT_P}${salt.hex()}${digest.hex()}"


def verify_password(password: object, encoded: str | None) -> bool:
    if not isinstance(password, str) or len(password) < PASSWORD_MIN_LENGTH or len(password) > PASSWORD_MAX_LENGTH or not encoded or not encoded.startswith("scrypt$"):
        return False
    try:
        _, n, r, p, salt_hex, digest_hex = encoded.split("$", 5)
        digest = hashlib.scrypt(password.encode("utf-8"), salt=bytes.fromhex(salt_hex), n=int(n), r=int(r), p=int(p))
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def validate_password(password: object) -> None:
    if not isinstance(password, str) or len(password) < PASSWORD_MIN_LENGTH:
        raise ValueError(f"La contraseña debe tener al menos {PASSWORD_MIN_LENGTH} caracteres.")
    if len(password) > PASSWORD_MAX_LENGTH:
        raise ValueError(f"La contraseña no puede superar {PASSWORD_MAX_LENGTH} caracteres.")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _is_expired(value: datetime) -> bool:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value <= _utc_now()


def create_session(session: Session, user: User) -> str:
    raw_token = secrets.token_urlsafe(32)
    now = _utc_now()
    session.add(AppSession(user_id=user.id, token_hash=hashlib.sha256(raw_token.encode()).hexdigest(), expires_at=now + timedelta(days=SESSION_DAYS), created_at=now))
    session.commit()
    return raw_token


def current_user(request: Request, session_factory: sessionmaker[Session]) -> User:
    raw_token = request.cookies.get(SESSION_COOKIE)
    if not raw_token:
        raise HTTPException(status_code=401, detail="Necesitas iniciar sesión.")
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    with session_factory() as session:
        stored = session.scalar(select(AppSession).where(AppSession.token_hash == token_hash))
        if stored is None or stored.revoked_at is not None or _is_expired(stored.expires_at):
            raise HTTPException(status_code=401, detail="La sesión no es válida o ya expiró.")
        user = session.get(User, stored.user_id)
        if user is None or not user.active:
            raise HTTPException(status_code=401, detail="La sesión no es válida.")
        session.expunge(user)
        return user


def revoke_session(request: Request, session_factory: sessionmaker[Session]) -> None:
    raw_token = request.cookies.get(SESSION_COOKIE)
    if not raw_token:
        return
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    with session_factory() as session:
        stored = session.scalar(select(AppSession).where(AppSession.token_hash == token_hash))
        if stored is not None and stored.revoked_at is None:
            stored.revoked_at = _utc_now()
            session.commit()


def require_origin(request: Request, origins: list[str]) -> None:
    origin = request.headers.get("origin")
    if not origin or origin not in origins:
        raise HTTPException(status_code=403, detail="La solicitud no tiene un origen permitido.")


def public_user(user: User) -> dict:
    return {"email": user.email, "name": user.name, "role": user.role, "emailVerified": user.email_verified}
