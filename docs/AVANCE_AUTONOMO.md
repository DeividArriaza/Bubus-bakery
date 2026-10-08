# Avance autónomo — base-catalogo

Fecha: 2026-10-07 · Rama: `feat/base-catalogo`

## Alcance publicado

Landing responsive y catálogo público en español con React + TypeScript, FastAPI, PostgreSQL y Docker Compose. El diseño adapta la referencia Figma y usa sus imágenes extraídas cuando fue viable. Catálogo normalizado: 9 vendibles activos (4 individuales y 5 cajas de 6), precios GTQ en centavos, cajas compuestas, composición de mixta y opción Almendra/Simple. No se añadieron login, pedidos, POS, puntos, Wallet, pagos ni integraciones sociales.

Se preservan `docs/BubusFigma.pdf`, documentación previa y cambios ajenos. No se borró el volumen PostgreSQL. La migración es aditiva y el seed no sobrescribe nombres, precios, componentes u opciones existentes.

## Verificación ejecutada

- `docker compose build` → API y frontend construidos.
- `docker compose up -d` → `db`, `api` y `frontend` healthy.
- `docker compose exec -T api pytest -q` → `4 passed, 1 skipped, 1 warning`.
- Test Compose actualizado montado desde el árbol local → `1 passed`.
- En `frontend/`: `npm run test:run` → `3 passed`; `npm run typecheck` → correcto; `npm run build` → correcto.
- `npm audit --audit-level=moderate` en `frontend/` → `found 0 vulnerabilities`.
- `pip-audit` no disponible; no se instaló globalmente. `docker compose exec -T api pip check` → `No broken requirements found`.
- API → health correcto y catálogo `9 = 4 individuales + 5 cajas`.
- Playwright desktop 1440×1100 y móvil 390×844 → filtro de cajas deja 5, opción mixta visible, consola/network sin errores.
- `docker compose config --quiet` → correcto. Con entorno vacío y `.env` deshabilitado → rechazo claro por variable requerida ausente.
- Persistencia → precio/nombre de `simple` y cantidad de componente modificados sobrevivieron reinicio de API; se restauraron valores demo explícitamente.
- Servicios locales: API `127.0.0.1:8000`, frontend `127.0.0.1:5173`; DB sin puerto publicado.

## TDD y bloqueos

La primera ronda RED de esta corrección fue real: backend `3 failed, 2 passed` y frontend `2 failed, 1 passed` por el contrato normalizado ausente. Los fallos históricos por `pytest`/`package.json` inexistentes eran errores de entorno y no se presentan como RED de feature. Hubo una regresión de test al endurecer Compose: la imagen cacheada usó la aserción antigua; el test local actualizado pasó al montarse explícitamente.

No hay bloqueo de publicación. No se ejecutó `npm audit fix --force`, no se hizo commit previo de estos avances, ni push remoto todavía al crear este registro.

## Etapa de cuentas

Se añadió migración aditiva `004_auth.sql` sobre el volumen existente: usuarios separados de operadores y sesiones opacas revocables persistidas. Registro siempre crea `customer`; no existe operador predeterminado. `python -m app.bootstrap_operator` requiere una ejecución local explícita y contraseña por prompt o variable del proceso sin imprimirla. Contraseñas usan scrypt de la biblioteca estándar; las cookies son HttpOnly/SameSite y Secure es configurable.

TDD de auth: RED backend real `ImportError: AppSession` con tests nuevos; después un fallo real de contrato español para HTTPException; GREEN final `docker compose run --rm --no-deps -v "$PWD/backend:/app" api pytest -q` → `9 passed, 1 skipped, 1 warning`. Frontend tuvo RED real por selector ambiguo y por tipado del matcher; GREEN final `npm run test:run` → `5 passed`, `npm run typecheck` y `npm run build` correctos.

API real con PostgreSQL: registro `201`, sesión `200`, logout `204`, sesión posterior `401`; una sesión permaneció `200` tras reinicio de API. CSRF/origin sin Origin devuelve `403`; CORS preflight devuelve solo localhost permitido. Google devuelve `503` “aún no está configurado”; el botón está deshabilitado y no simula login. Verificación/recuperación de correo no expone tokens ni promete envío.

Capturas de acceso verificadas con Playwright: `docs/design-review/auth-desktop.jpg`, `auth-mobile.jpg` y sus `.b64` pequeños. Las respuestas `401` esperadas al consultar una sesión anónima aparecen como mensajes de consola del navegador, sin requests fallidas; quedan documentadas como comportamiento de acceso denegado.

## Solicitudes web y POS

Se añadió la migración aditiva `005_orders_sales.sql` y `006_order_payment_intent.sql`, sin borrar el volumen ni tocar catálogo/auth. Las solicitudes autenticadas aceptan solo cajas para `envio`, calculan subtotal desde el catálogo backend, congelan precio/nombre/composición/opciones por línea, dejan `shippingAmountCents` y `totalFinalCents` en `null`, y nacen `POR_CONFIRMAR` con pago/entrega separados. La intención `AL_PEDIR`/`AL_RECIBIR` no cobra.

El panel operador exige rol `operator`, lista y cambia solicitudes entre `POR_CONFIRMAR`, `CONFIRMADA` y `CANCELADA` (no reabre canceladas), y registra ventas presenciales con `EFECTIVO` o `TRANSFERENCIA`, actor, fecha, importes, líneas snapshot y confirmación explícita. No hay tarjeta, devolución, inventario, reparto, banco, puntos ni Wallet. No existe operador predeterminado; el smoke usó `bootstrap_operator` con secreto efímero y limpió solo sus fixtures.

TDD real: tests nuevos RED por import faltante; después RED de resolución de opciones y mensaje de validación; GREEN backend `14 passed, 1 skipped, 1 warning`, frontend `5 passed`, typecheck/build correctos. Test Compose actualizado: `1 passed`. Flujo API real cliente→solicitud `201`→operador consulta `200`/confirma `200`→venta `201` y reintento idempotente `200`; precios enviados adulterados fueron ignorados.

Browser end-to-end real desktop/móvil: cliente creó solicitud visible al operador; operador confirmó y registró venta. Capturas: `docs/design-review/orders-mobile.jpg`/`.b64` y `pos-desktop.jpg`/`.b64`. Sin requests fallidas ni errores de consola no esperados. Los estados, cobertura, costo y total final quedan honestamente pendientes de confirmación de la dueña.

## Revisión final independiente del mismo agente

No fue una revisión hecha por otro modelo/agente. Se inspeccionaron auth, Origin/CSRF, CORS, roles, sesiones revocables, snapshots de precio/composición, privacidad, idempotencia, auditoría POS, ciclos del catálogo, secretos ignorados, Compose, DB privada y healthchecks. Se corrigió un fallo concreto de CORS: PATCH y `Idempotency-Key` no estaban declarados; ahora el preflight está cubierto por `test_cors_allows_authenticated_patch_and_idempotency_header_only_from_dev_origin`. Se añadió referencia interna no sensible de venta mediante migración 007 y foco visible en UI.

Resultados reproducibles finales: `docker compose build && docker compose up -d` sin `-v`; migraciones `001..007`; `docker compose exec -T api pytest -q` → `16 passed, 1 skipped, 1 warning`; Compose test → `1 passed`; `cd frontend && npm run test:run` → `5 passed`; `npm run typecheck`/`npm run build` correctos; `npm audit --audit-level=moderate` → `found 0 vulnerabilities`; `pip-audit` no disponible y `pip check` limpio. Servicios locales: `http://localhost:5173`, `http://localhost:8000/api/health`; DB sin puerto host.

Implementado y verificado: catálogo compuesto acíclico en datos actuales, auth cliente/operador, solicitudes solo cajas para envío, subtotal y snapshots backend, estados separados, POS efectivo/transferencia, idempotencia, historial de actor/fecha/método/importes/referencia, UI española responsive y flujo browser desktop/móvil. Diferido: Google sin configuración, verificación/recuperación email sin proveedor, puntos sujetos a costes/reglas, Wallet, modalidad app nativa/PWA, tarjetas, inventario, banco, reparto, cobertura/coste/envío final, devoluciones y claim de producción.
