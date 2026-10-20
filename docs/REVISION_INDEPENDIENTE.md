# Revisión independiente de integridad backend

Fecha: 2026-10-08 · rama `feat/base-catalogo` · base inspeccionada `90a1f0fa90d1b124ebdeec2050acad2977e7af05`

El reporte base provino de una revisión externa independiente. Este agente implementador no es el reviewer original: reprodujo los hallazgos y aplicó únicamente las correcciones de este ciclo.

## RED reproducible

Antes de implementar, tras reconstruir la imagen que contenía los tests nuevos:

```text
docker compose exec -T api pytest -q tests/test_catalog.py tests/test_orders_pos.py
3 failed, 11 passed, 2 warnings
```

Los fallos fueron: `KeyError` al catalogar una relación a producto inactivo, padre compuesto todavía expuesto, y reutilización de clave de pedido con payload diferente devuelta como `200`.

En PostgreSQL nuevo, `apply_migrations` seguido de `seed_catalog` inicialmente dejó `0` filas en `options`: la migración había creado el grupo, pero el seed solo completaba opciones cuando la caja era recién creada. El caso se reprodujo en un schema aislado; no se usó el volumen de desarrollo para simular una base vacía.

## Cambios acotados

- `seed_catalog` ahora inserta solo componentes/opciones faltantes aun con grupo/producto existente; no modifica nombres, precios, cantidades ni relaciones ya presentes.
- `008_idempotency_fingerprints.sql` añade columnas nullable para pedidos/ventas existentes sin borrar datos. El fingerprint se calcula después de validar y valorar desde backend; una carrera recupera el ganador solo tras rollback y solo si la fila única existe. Una colisión con payload lógico distinto responde `409` en español; otros `IntegrityError` no se convierten en éxito.
- El catálogo y `calculate_items` recorren relaciones con todos los IDs, rechazan ciclos, padres con componentes inactivos y grupos obligatorios sin opciones activas. No generan el slug ficticio `producto`; las opciones inactivas no se muestran ni se aceptan.
- La transición de estados bloquea la fila con `SELECT FOR UPDATE`; una confirmación posterior a cancelación responde `409`.

## GREEN y verificación

```text
docker compose build api && docker compose up -d api
docker compose exec -T api pytest -q
21 passed, 4 skipped, 2 warnings

docker compose exec -T api sh -lc 'TEST_DATABASE_URL="$DATABASE_URL" pytest -q tests/test_postgres_integrity.py'
3 passed, 2 warnings
```

La suite PostgreSQL crea un schema UUID aislado, aplica migraciones `001..008`, ejecuta el seed dos veces, valida 9 activos, composición mixta `2 Snickers + 3 M&M + 1 Almendra/Simple`, solicitudes/ventas válidas, dos pedidos concurrentes y dos ventas concurrentes con una sola fila y respuestas `201/200`, además de la carrera cancelar/confirmar y confirmación tardía `409`. Al finalizar elimina exclusivamente ese schema nuevo. No se ejecutó `down -v` ni se borró el volumen existente.

SQLite mantiene pruebas de validación/catálogos, pero no se usa para afirmar garantías de carrera, uniqueness o locks PostgreSQL.

Verificaciones adicionales tras la corrección: `docker compose ps` mostró `db`, `api`, `frontend` healthy; PostgreSQL conservó migraciones `001..008`, 9 productos activos y relaciones históricas inactivas sin ser borradas; `curl -fsS http://127.0.0.1:8000/api/health` devolvió `{"status":"ok","servicio":"api"}`. La suite frontend mantuvo `5 passed`, typecheck/build correctos y `npm audit --audit-level=moderate` → `found 0 vulnerabilities`; `pip-audit -r backend/requirements.lock.txt` → `No known vulnerabilities found`.

La aceptación por el ciclo padre sigue pendiente. No se implementaron puntos, Wallet ni otras decisiones diferidas.

## Corrección ciclo 2 — pendiente de aceptación padre

Origen: la segunda revisión externa independiente sobre `f9dd024`; este agente implementador reprodujo y corrigió los hallazgos, sin afirmar ser ese reviewer.

### RED real reproducible

- `docker compose run --rm --no-deps -v "$PWD/backend:/app" api pytest -q tests/test_auth.py::test_chunked_auth_body_is_rejected_before_json_or_hash tests/test_orders_pos.py::test_order_replay_uses_historical_intention_after_price_change_and_inactive_product tests/test_orders_pos.py::test_sale_replay_uses_historical_intention_after_price_change_and_inactive_product` → `3 failed, 2 warnings`: body chunked terminó en 400 y los dos reintentos históricos fueron 422.
- Frontend: el nuevo caso de operación incierta falló porque la cantidad seguía editable tras error de red.

### Cambios acotados

- El middleware de auth consume el stream en chunks con límite acumulado de 8192 bytes antes de JSON, validación o hash; responde `413` en español y no conserva un body sobre el límite. `Content-Length` queda solo como rechazo temprano.
- Migración aditiva `009_idempotency_intentions.sql` guarda la intención normalizada (slug, cantidad, opciones y campos lógicos), ignorando `priceCents`. Pedido/venta buscan primero por actor+clave; un replay idéntico devuelve el snapshot histórico `200` aunque cambie precio o disponibilidad. Payload lógico distinto conserva `409`; operaciones nuevas calculan precio desde catálogo vigente. Legacy recupera intención desde sus snapshots.
- La captura de `IntegrityError` solo resuelve la restricción de idempotencia identificada; errores de integridad distintos se relanzan.
- Cliente y POS reconcilian opciones contra el producto seleccionado; una operación incierta congela un payload y clave, ofrece `Reintentar`, `Recuperar resultado` y `Nueva operación`, y solo limpia tras éxito o acción explícita.

### GREEN y verificaciones actuales

- `docker compose run --rm --no-deps -v "$PWD/backend:/app" api pytest -q` → `26 passed, 4 skipped, 2 warnings`.
- `docker compose exec -T api sh -lc 'TEST_DATABASE_URL="$DATABASE_URL" pytest -q tests/test_postgres_integrity.py'` → `4 passed, 2 warnings`; schema PostgreSQL aislado, migraciones `001..009`, concurrencia, replay histórico y cancel/confirm sin borrar volumen.
- `frontend/`: `npm run test:run` → `11 passed`; `npm run typecheck` y `npm run build` → correctos; `npm audit --audit-level=high` → `found 0 vulnerabilities`.
- Auditoría aislada sin modificar el repo: `docker run --rm -v "$PWD/backend:/audit:ro" python:3.12-slim ... pip-audit -r /audit/requirements.lock.txt` → `No known vulnerabilities found`.
- `docker compose up -d --build`, health/API real y catálogo → 9 productos; `db`, `api`, `frontend` healthy, DB sin puerto host. Playwright desktop/móvil → consola sin errores; capturas nuevas: `docs/design-review/ux-ciclo-dos-1440.jpg(.b64)` y `ux-ciclo-dos-390.jpg(.b64)`, cada `.b64` <55 000 caracteres.

No se implementaron puntos, Wallet, Google, email, pagos tarjeta, cobertura/envío ni otros pendientes. No es aprobación del padre ni claim de producción.

## Corrección seguridad, UX e idempotencia frontend — pendiente de aceptación padre

La revisión reprodujo estos fallos adicionales: `frontend: npm run test:run -- --run src/orders.test.ts` → `2 failed` porque cada llamada generaba una UUID distinta; `docker compose exec -T api pytest -q tests/test_auth.py` → `2 failed` porque la tercera tentativa no devolvía 429 y una contraseña de 129 caracteres era aceptada.

Correcciones: solicitud web y venta POS conservan una clave por operación en `useRef`, bloquean doble submit mientras hay petición y preservan la clave ante error de red; solo se limpia tras éxito y un `409` se muestra como conflicto honesto. El POS renderiza `optionGroups` reales: mixta Almendra/Simple y cajas homogéneas sin opciones ficticias. El operador ve nombre/correo/contacto mínimo, artículos, cantidades, composición, elección, intención/estados y subtotal/envío/total pendientes; el cliente no recibe el objeto `customer`.

Registro/login ahora limitan bytes (`AUTH_MAX_REQUEST_BYTES`, default 8192), contraseña `12..128`, intentos por IP/correo con ventana finita, `Retry-After` 429 y hash concurrente (`AUTH_MAX_HASH_CONCURRENCY`, default 4). El limitador es thread-safe, bounded y por proceso: no es garantía distribuida multi-worker. `X-Forwarded-For` solo se usa con `TRUST_PROXY=true`; por defecto se usa `request.client.host`; las entradas expiran en memoria y no se persisten.

GREEN reproducible: `docker compose exec -T api pytest -q` → `23 passed, 4 skipped, 2 warnings`; suite PostgreSQL aislada → `3 passed, 2 warnings`; frontend → `10 passed`, typecheck/build correctos, npm audit `0`; pip-audit → `No known vulnerabilities found`. Smoke browser real desktop 1440 y móvil 390 cubrió cliente→operador→detalle→POS mixta Simple→doble clic con una venta; 401 de consulta de sesión anónima fueron esperados, sin requests fallidas inesperadas. Capturas: `docs/design-review/ux-pos-1440.jpg(.b64)` y `ux-pos-390.jpg(.b64)`, b64 49 376/16 376 caracteres e ignorados. Fixtures propios eliminados, volumen intacto, tres servicios healthy. No es aprobación de reviewer ni claim de producción.
