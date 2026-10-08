# Verificación inicial — catálogo base

Fecha: 2026-10-07 · Rama: feat/base-catalogo

## Alcance y TDD

Entrega acotada a landing responsive y catálogo público. No implementa login, Google, pedidos, checkout, POS, puntos, Wallet, pagos ni delivery. No es un claim de producción.

Las pruebas de corrección se escribieron antes del código corregido y fallaron por comportamiento real:

- docker compose exec -T api pytest -q → 3 failed, 2 passed, 1 warning (faltaban las 9 filas normalizadas, cajas/componentes esperados y el test de configuración no estaba montado en el contenedor).
- Frontend: npm run test:run → 2 failed, 1 passed (la UI antigua leía el contrato de precios anterior y no soportaba el filtro normalizado).
- Corrección posterior de configuración: el test local antiguo esperaba interpolación no requerida; tras cambiar Compose a variables obligatorias, el contenedor cacheado dio 1 fallo por usar ese test viejo. Con el test actualizado montado explícitamente: 1 passed.
- No se cuentan los fallos históricos de entorno (pytest/package.json inexistentes) como RED de esta corrección.

GREEN:

- docker compose exec -T api pytest -q → 4 passed, 1 skipped, 1 warning.
- docker compose run --rm --no-deps -v "$PWD:/workspace" -e REPO_ROOT=/workspace api pytest -q tests/test_compose_config.py → 1 passed.
- En frontend/: npm run test:run → 1 file, 3 passed; npm run typecheck → correcto; npm run build → correcto.

Las pruebas cubren nueve productos, precios GTQ en centavos, componentes de las cuatro cajas simples y de la mixta, opciones, error API en español y seed no destructivo.

## Modelo, migraciones y seed

- Migraciones aplicadas: 001_initial.sql, 002_normalize_catalog.sql, 003_retire_legacy_mixta.sql.
- API final: 9 productos vendibles activos: 4 individuales y 5 cajas de 6; cada uno tiene price_cents, categoría y presentación. Las cajas son productos compuestos.
- Caja simple: componente del brownie correspondiente con cantidad 6. Mixta: 2 Snickers + 3 M&M + grupo de elección de 1 Almendra o Simple.
- La fuente normalizada es price_cents; las columnas legacy se conservan únicamente para migración/compatibilidad, no como modelo ORM ni fuente de UI.
- Se conserva la fila demo antigua mixta como inactiva; no se borraron filas ni se editaron datos de usuarios.
- El seed inserta faltantes y componentes/opciones ausentes; no sobrescribe nombres, precios ni composición existentes. La migración es aditiva y no requiere borrar volúmenes.
- Evidencia de persistencia: se cambió temporalmente en la DB demo el nombre/precio de simple y la cantidad de su componente, se reinició api, y se observaron los valores modificados con 9 productos; después se restauraron explícitamente los valores demo.

## Compose, configuración y API

- docker compose config --quiet → correcto. docker compose build → correcto.
- Con entorno vacío y .env deshabilitado, docker compose --env-file /dev/null config --quiet rechaza la configuración con mensaje de variable requerida ausente.
- docker compose down && docker compose up -d sin -v → servicios db, api, frontend healthy; el seed no duplicó filas.
- API: curl -fsS http://localhost:8000/api/health → {"status":"ok","servicio":"api"}; catálogo → 9 activos (4 individuales/5 cajas), precios y composiciones esperados.
- Frontend: http://localhost:5173. API en 127.0.0.1:8000; frontend en 127.0.0.1:5173; DB sin puerto publicado y solo en red interna.
- Compose exige POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD; no hay passwords fallback. .env.example documenta generar un secreto local; .env local es ignorado y no fue leído ni impreso.
- Healthchecks configurados para los tres servicios; frontend depende de API healthy.

## Auditoría

- Antes de actualizar dependencias: npm audit --audit-level=moderate → 6 vulnerabilidades (2 críticas, 1 alta, 3 moderadas), asociadas al árbol antiguo Vite/Vitest/esbuild.
- Tras actualizar versiones compatibles fijadas de Vite/Vitest/plugin React: npm audit --audit-level=moderate → found 0 vulnerabilities. No se ejecutó npm audit fix --force.
- La auditoría inicial de Python se reprodujo en una venv temporal fuera del repo con `pip-audit --no-deps -r /tmp/bubus-before-audit.txt` → 16 avisos: Starlette 0.41.3 (correcciones hasta 1.3.1) y pytest 8.3.4 (PYSEC-2026-1845, corrección 9.0.3). Tras actualizar el lock fijado, `pip-audit -r backend/requirements.lock.txt` → `No known vulnerabilities found`.
- `docker compose exec -T api pip check` → `No broken requirements found`; se registra como consistencia de instalación, no como sustituto del audit CVE.

## Navegador, capturas y límites

Se usó Playwright con Chromium descargado en la caché del entorno. En viewport 1440×1100 y 390×844 se verificó lang=es, título, carga, filtro Cajas de 6 (5 resultados), apertura de caja mixta y opción visible. Consola: 0 errores; network: 0 requests fallidas y 0 respuestas ≥400.

Capturas JPG y base64 (<55 000 caracteres por archivo):

- docs/design-review/landing-desktop.jpg / .b64
- docs/design-review/landing-mobile.jpg / .b64
- Referencia PDF recortada: docs/design-review/figma-reference-hero-login.jpg / .b64

Se extrajeron dos fotos reales embebidas del PDF a frontend/public/assets/. No se copiaron reseñas, “baked daily”, precios ni promesas de muestra como hechos del negocio. Quedan pendientes endurecimiento, observabilidad, backups probados, despliegue y revisión de contenido/legal.

## Revisión final y alcance vigente

La revisión final fue independiente dentro del mismo agente, no por un modelo reviewer distinto. Se verificaron auth/CSRF/CORS/roles/sesiones, ciclos del catálogo, precios y snapshots históricos, privacidad/idempotencia de solicitudes, auditoría POS, secretos, Docker/DB privada/localhost/healthchecks, foco y etiquetas móviles. Hallazgos corregidos: CORS ahora declara PATCH e Idempotency-Key; ventas guardan referencia interna no sensible mediante migración 007; UI tiene foco visible.

La revisión de dependencias está documentada en `docs/REVISION_DEPENDENCIAS.md`: se actualizaron FastAPI/Starlette, pytest, uvicorn, SQLAlchemy y psycopg con resolver real; no se usó `pip-audit --ignore-vulns`, `npm audit fix --force` ni se hizo claim de producción.

Comandos finales: `docker compose build && docker compose up -d` sin `-v`; migraciones PostgreSQL 001–007; `docker compose exec -T api pytest -q` → 16 passed, 1 skipped, 2 warnings; `docker compose exec -T api pip check` → limpio; en `frontend/`, test 5 passed, typecheck/build correctos, `npm audit --audit-level=moderate` → 0 vulnerabilidades; `pip-audit -r backend/requirements.lock.txt` → 0 vulnerabilidades conocidas.

La smoke browser real cubrió cliente crea solicitud → operador consulta/confirmación → venta POS; capturas adicionales: `docs/design-review/orders-mobile.jpg`/`.b64` y `pos-desktop.jpg`/`.b64`, cada `.b64` bajo 55 000 caracteres. URLs locales: `http://localhost:5173` y `http://localhost:8000/api/health`. `db`, `api` y `frontend` quedaron healthy; reinicio/rebuild fue sin borrar volumen.

Diferido y no fingido: Google por falta de configuración, proveedor de verificación/recuperación de correo, puntos hasta aprobar costes/reglas, Wallet, app nativa/PWA, tarjetas, inventario, banco, reparto, cobertura/coste/logística y devoluciones. No hay claim de producción.
