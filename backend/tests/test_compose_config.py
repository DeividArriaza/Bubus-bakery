from pathlib import Path
import os
import pytest


COMPOSE = Path(os.getenv("REPO_ROOT", "/workspace")) / "compose.yaml"


def test_compose_requires_credentials_and_binds_public_services_locally():
    if not COMPOSE.exists():
        pytest.skip("requiere montar la raíz del repositorio para inspeccionar Compose")
    text = COMPOSE.read_text()
    assert '"127.0.0.1:8000:8000"' in text
    assert '"127.0.0.1:5173:5173"' in text
    assert "POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?" in text
    assert "POSTGRES_DB: ${POSTGRES_DB:?" in text
    assert "POSTGRES_USER: ${POSTGRES_USER:?" in text
    assert "${POSTGRES_PASSWORD:-" not in text
    db_section = text.split("  api:", 1)[0]
    assert "ports:" not in db_section
