# Revisión independiente de integridad backend

Fecha: 2026-10-08 · rama `feat/base-catalogo` · base inspeccionada `90a1f0fa90d1b124ebdeec2050acad2977e7af05`

Esta fue una revisión independiente dentro del mismo agente. No se usó otro modelo/agente y no se amplió el alcance funcional.

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

## Corrección seguridad, UX e idempotencia frontend — pendiente de aceptación padre

La revisión reprodujo estos fallos adicionales: `frontend: npm run test:run -- --run src/orders.test.ts` → `2 failed` porque cada llamada generaba una UUID distinta; `docker compose exec -T api pytest -q tests/test_auth.py` → `2 failed` porque la tercera tentativa no devolvía 429 y una contraseña de 129 caracteres era aceptada.

Correcciones: solicitud web y venta POS conservan una clave por operación en `useRef`, bloquean doble submit mientras hay petición y preservan la clave ante error de red; solo se limpia tras éxito y un `409` se muestra como conflicto honesto. El POS renderiza `optionGroups` reales: mixta Almendra/Simple y cajas homogéneas sin opciones ficticias. El operador ve nombre/correo/contacto mínimo, artículos, cantidades, composición, elección, intención/estados y subtotal/envío/total pendientes; el cliente no recibe el objeto `customer`.

Registro/login ahora limitan bytes (`AUTH_MAX_REQUEST_BYTES`, default 8192), contraseña `12..128`, intentos por IP/correo con ventana finita, `Retry-After` 429 y hash concurrente (`AUTH_MAX_HASH_CONCURRENCY`, default 4). El limitador es thread-safe, bounded y por proceso: no es garantía distribuida multi-worker. `X-Forwarded-For` solo se usa con `TRUST_PROXY=true`; por defecto se usa `request.client.host`; las entradas expiran en memoria y no se persisten.

GREEN reproducible: `docker compose exec -T api pytest -q` → `23 passed, 4 skipped, 2 warnings`; suite PostgreSQL aislada → `3 passed, 2 warnings`; frontend → `10 passed`, typecheck/build correctos, npm audit `0`; pip-audit → `No known vulnerabilities found`. Smoke browser real desktop 1440 y móvil 390 cubrió cliente→operador→detalle→POS mixta Simple→doble clic con una venta; 401 de consulta de sesión anónima fueron esperados, sin requests fallidas inesperadas. Capturas: `docs/design-review/ux-pos-1440.jpg(.b64)` y `ux-pos-390.jpg(.b64)`, b64 49 376/16 376 caracteres e ignorados. Fixtures propios eliminados, volumen intacto, tres servicios healthy. No es aprobación de reviewer ni claim de producción.
