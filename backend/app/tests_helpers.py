from datetime import datetime, timezone

from .auth import create_session, hash_password
from .models import User


def authenticated_customer(session_factory, email: str) -> str:
    with session_factory() as session:
        user = User(email=email, name="Cliente", password_hash=hash_password("ClienteSeguro1234"), role="customer", email_verified=False, active=True, created_at=datetime.now(timezone.utc))
        session.add(user)
        session.commit()
        session.refresh(user)
        return create_session(session, user)
