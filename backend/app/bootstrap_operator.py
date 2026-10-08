import argparse
import getpass
import os
import sys
from datetime import datetime, timezone

from sqlalchemy import select

from .auth import hash_password, normalize_email
from .db import apply_migrations, make_engine, make_session_factory
from .models import User


def main() -> int:
    parser = argparse.ArgumentParser(description="Crea explícitamente un operador local; no crea cuentas predeterminadas.")
    parser.add_argument("--email", default=os.getenv("BOOTSTRAP_OPERATOR_EMAIL"))
    parser.add_argument("--name", default=os.getenv("BOOTSTRAP_OPERATOR_NAME", "Operador"))
    args = parser.parse_args()
    email = args.email or input("Correo del operador: ")
    password = os.getenv("BOOTSTRAP_OPERATOR_PASSWORD") or getpass.getpass("Contraseña del operador (no se mostrará): ")
    try:
        email = normalize_email(email)
        password_hash = hash_password(password)
    except ValueError as error:
        print(f"Error de validación: {error}", file=sys.stderr)
        return 2
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL es obligatoria.", file=sys.stderr)
        return 2
    engine = make_engine(database_url)
    apply_migrations(engine)
    session_factory = make_session_factory(engine)
    with session_factory() as session:
        if session.scalar(select(User).where(User.email == email)) is not None:
            print("Ya existe una cuenta con ese correo; no se modificó.", file=sys.stderr)
            return 1
        session.add(User(email=email, name=args.name, password_hash=password_hash, role="operator", email_verified=False, active=True, created_at=datetime.now(timezone.utc)))
        session.commit()
    print("Operador creado. La contraseña no se almacena en texto plano.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
