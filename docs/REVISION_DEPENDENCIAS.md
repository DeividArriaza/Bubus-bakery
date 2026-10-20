# Revisión de dependencias

Fecha: 2026-10-08 · Rama: `feat/base-catalogo` · base: `90a1f0fa90d1b124ebdeec2050acad2977e7af05`

## Antes

Se reprodujo el hallazgo en una venv temporal fuera del repositorio, sin instalar herramientas globales:

```text
/tmp/bubus-deps-audit-venv/bin/pip-audit --no-deps -r /tmp/bubus-before-audit.txt
Found 16 known vulnerabilities in 2 packages
```

El archivo de reproducción fijaba `fastapi==0.115.6`, `starlette==0.41.3` y `pytest==8.3.4`. Los hallazgos correspondieron a avisos de Starlette con correcciones hasta `1.3.1` y a `pytest` `PYSEC-2026-1845`, corregido en `9.0.3`. El intento de resolver el lock antiguo completo también falló porque `psycopg-binary==3.2.3` no estaba disponible para el índice/intérprete consultado.

## Cambio mínimo resuelto

El resolver real confirmó compatibilidad antes de editar el producto. `backend/pyproject.toml` fija FastAPI `0.142.4`, Starlette `1.3.1`, pytest `9.0.3`, uvicorn `0.54.0`, SQLAlchemy `2.0.54` y psycopg `3.3.6`. `backend/requirements.lock.txt` contiene las dependencias directas y transitivas completas fijadas, incluyendo `pydantic`, `anyio`, `httpx` y los extras de uvicorn. No se añadieron funciones de negocio.

Comandos de resolución y auditoría:

```text
/tmp/bubus-deps-audit-venv/bin/python -m pip install --dry-run --ignore-installed --no-cache-dir fastapi==0.142.4 starlette==1.3.1 pytest==9.0.3 uvicorn[standard]==0.54.0 SQLAlchemy==2.0.54 psycopg[binary]==3.3.6 httpx==0.28.1
/tmp/bubus-deps-audit-venv/bin/pip-audit -r backend/requirements.lock.txt
No known vulnerabilities found
```

## Regresión y ejecución

```text
docker compose build && docker compose up -d
db, api y frontend healthy; puertos 127.0.0.1:8000 y 127.0.0.1:5173; DB sin puerto publicado
docker compose exec -T api pytest -q
16 passed, 1 skipped, 2 warnings
docker compose exec -T api pip check
No broken requirements found
cd frontend && npm run test:run && npm run typecheck && npm run build && npm audit --audit-level=moderate
5 passed; typecheck correcto; build correcto; found 0 vulnerabilities
docker compose exec -T db psql ...
migraciones 001..007; 9 productos activos; 0 orders; 0 sales
curl -fsS http://127.0.0.1:8000/api/health
{"status":"ok","servicio":"api"}
curl -fsS http://127.0.0.1:8000/api/catalog
9 productos: 4 individuales y 5 cajas
```

El rebuild conservó el volumen PostgreSQL y el seed existente; no se ejecutó `down -v`. La smoke de navegador y capturas previas siguen documentadas en `docs/VERIFICACION_INICIAL.md`; esta revisión no amplió alcance. Quedan las limitaciones ya declaradas: no claim de producción, Google/email sin configuración, puntos/Wallet y pagos con tarjeta diferidos. El lock no incluye hashes de artefactos; `pip-audit` cubre vulnerabilidades conocidas, no una garantía de cadena de suministro.
