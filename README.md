# Bubu's bakery

Primera entrega real: landing responsive y catálogo público servido por una API FastAPI con PostgreSQL. La interfaz y los mensajes visibles están en español.

## Alcance de esta entrega

- Landing responsive inspirada en la referencia visual: rosa pálido, blanco y vino/coral.
- Catálogo persistente con precios en centavos de GTQ.
- Nueve productos vendibles normalizados: cuatro individuales y cinco cajas de 6; todas las cajas son productos compuestos con precio propio.
- La caja mixta expone su composición y elección real del sexto brownie.
- El registro histórico `mixta` de la demo se conserva como legado inactivo; la presentación vendible normalizada es `mixta-caja-6`.
- Migración versionada y seed idempotente.
- API pública de lectura: `GET /api/health` y `GET /api/catalog`.
- No incluye login, pedidos, checkout, POS, puntos ni Wallet.

## Ejecutar con Docker Compose

Requisitos: Docker y Docker Compose.

```bash
cp .env.example .env
# Sustituye POSTGRES_PASSWORD por un secreto local largo y único.
docker compose up --build
```

Compose exige `POSTGRES_DB`, `POSTGRES_USER` y `POSTGRES_PASSWORD`; no contiene fallbacks de credenciales. El archivo `.env` es local e ignorado por Git. No uses estos valores para producción.

URLs locales:

- Landing: <http://localhost:5173>
- Health: <http://localhost:8000/api/health>
- Catálogo: <http://localhost:8000/api/catalog>

La base de datos no publica un puerto al host. El volumen `postgres_data` conserva la información; el seed no duplica productos al reiniciar.

Los servicios se publican solo en `127.0.0.1`: frontend en `5173` y API en `8000`.

## Desarrollo sin Compose

Frontend:

```bash
cd frontend
npm ci
npm run dev
```

Backend: usar Python 3.12 o 3.13 en un entorno virtual y `backend/requirements.lock.txt`. La API espera `DATABASE_URL`; el Compose ya la configura.

## Verificación

Los comandos, resultados, capturas y limitaciones de la primera verificación se conservan en [`docs/VERIFICACION_INICIAL.md`](docs/VERIFICACION_INICIAL.md).

Contexto y reglas: [`AGENTS.md`](AGENTS.md), [`docs/PLAN_DE_ACCION.md`](docs/PLAN_DE_ACCION.md) y [`skills/git-multiple-accounts/SKILL.md`](skills/git-multiple-accounts/SKILL.md).
