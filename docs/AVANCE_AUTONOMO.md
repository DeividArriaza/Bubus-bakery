# Avance autónomo — base-catalogo

Fecha: 2026-10-07 · Rama: `feat/base-catalogo`

## Alcance publicado

Landing responsive y catálogo público en español con React + TypeScript, FastAPI, PostgreSQL y Docker Compose. El diseño adapta la referencia Figma y usa sus imágenes extraídas cuando fue viable. Catálogo normalizado: 9 vendibles activos (4 individuales y 5 cajas de 6), precios GTQ en centavos, cajas compuestas, composición de mixta y opción Almendra/Simple. En esta etapa inicial todavía no se añadían login, pedidos, POS, puntos, Wallet, pagos ni integraciones sociales; las etapas posteriores implementaron cuentas, solicitudes web y POS básico, manteniendo diferidos puntos, Wallet y pagos con tarjeta.

Se preservan `docs/BubusFigma.pdf`, documentación previa y cambios ajenos. No se borró el volumen PostgreSQL. La migración es aditiva y el seed no sobrescribe nombres, precios, componentes u opciones existentes.

## Verificación ejecutada

- `docker compose build` → API y frontend construidos.
- `docker compose up -d` → `db`, `api` y `frontend` healthy.
- `docker compose exec -T api pytest -q` → `4 passed, 1 skipped, 1 warning`.
- Test Compose actualizado montado desde el árbol local → `1 passed`.
- En `frontend/`: `npm run test:run` → `3 passed`; `npm run typecheck` → correcto; `npm run build` → correcto.
- `npm audit --audit-level=moderate` en `frontend/` → `found 0 vulnerabilities`.
- La auditoría Python inicial se ejecutó en una venv temporal fuera del repo; tras actualizar el lock, `pip-audit -r backend/requirements.lock.txt` → `No known vulnerabilities found`. `docker compose exec -T api pip check` → `No broken requirements found`.
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

## Revisión final externa reportada; correcciones por este agente

La revisión externa reportó esos aspectos; este agente implementador los reprodujo y corrigió, sin ser el reviewer original. Se inspeccionaron auth, Origin/CSRF, CORS, roles, sesiones revocables, snapshots de precio/composición, privacidad, idempotencia, auditoría POS, ciclos del catálogo, secretos ignorados, Compose, DB privada y healthchecks. Se corrigió un fallo concreto de CORS: PATCH y `Idempotency-Key` no estaban declarados; ahora el preflight está cubierto por `test_cors_allows_authenticated_patch_and_idempotency_header_only_from_dev_origin`. Se añadió referencia interna no sensible de venta mediante migración 007 y foco visible en UI.

Resultados reproducibles de la revisión de integridad (sin borrar volumen): `docker compose build api && docker compose up -d api`; migraciones actuales `001..008`; `docker compose exec -T api pytest -q` → `21 passed, 4 skipped, 2 warnings`; suite PostgreSQL aislada → `3 passed, 2 warnings`; Compose, frontend, build/typecheck y auditorías siguen documentados en `docs/REVISION_INDEPENDIENTE.md`. Servicios locales: `http://localhost:5173`, `http://localhost:8000/api/health`; DB sin puerto host.

Implementado y verificado: catálogo compuesto acíclico en datos actuales, auth cliente/operador, solicitudes solo cajas para envío, subtotal y snapshots backend, estados separados, POS efectivo/transferencia, idempotencia, historial de actor/fecha/método/importes/referencia, UI española responsive y flujo browser desktop/móvil. Diferido: Google sin configuración, verificación/recuperación email sin proveedor, puntos sujetos a costes/reglas, Wallet, modalidad app nativa/PWA, tarjetas, inventario, banco, reparto, cobertura/coste/envío final, devoluciones y claim de producción.

## Seguridad y UX POS — revisión vigente pendiente de aceptación padre

La revisión independiente vigente corrigió idempotencia frontend con doble submit/reintento, selección POS mixta, detalle mínimo de cliente solo para operador y límites de acceso por proceso. Resultados actuales: backend `23 passed, 4 skipped`, PostgreSQL aislado `3 passed`, frontend `10 passed`, typecheck/build correctos, npm/pip audit sin vulnerabilidades conocidas y smoke browser desktop/móvil; evidencia completa en `docs/REVISION_INDEPENDIENTE.md`. El limitador no es distribuido multi-worker; Google, email, puntos, Wallet, tarjetas y cobertura/total final siguen diferidos.

## Revisión independiente de integridad — pendiente de aceptación padre

Se reprodujeron tres hallazgos reales sobre el SHA `90a1f0f`: seed incompleto cuando migraciones ya habían creado el grupo de opciones; colisión concurrente de idempotencia; y `KeyError`/composición vendible al desactivar componentes u opciones. Se corrigieron con seed aditivo por relación, huella lógica y resolución del ganador tras `IntegrityError` únicamente si existe, `SELECT FOR UPDATE` para estados, validación de grafo acíclico y filtrado de relaciones vendibles. La migración aditiva es `008_idempotency_fingerprints.sql`.

La suite aislada crea un schema PostgreSQL nuevo, aplica `001..008`, ejecuta seed dos veces y elimina solo ese schema de prueba: `3 passed, 2 warnings`; cubre 9 activos, mixta 2 Snickers + 3 M&M + Almendra/Simple, concurrencia pedido/venta y carrera cancelar/confirmar. SQLite se usa solo para validaciones sin garantía de concurrencia; no se presenta como prueba de locks Postgres. La aceptación final queda pendiente del ciclo padre.

## Corrección ciclo 2 — pendiente de aceptación padre

La segunda revisión externa independiente sobre `f9dd024` reportó cuatro hallazgos. Este agente implementador los reprodujo y corrigió; no fue el reviewer original ni se presenta esta sección como aprobación.

- Body auth chunked: límite real por stream antes de JSON/hash, `413` español y sin almacenamiento ilimitado.
- Idempotencia: migración aditiva `009_idempotency_intentions.sql`, lookup actor+clave primero, intención normalizada independiente de precio/estado actual, replay histórico `200`, conflicto lógico `409` y `IntegrityError` no relacionado no se absorbe.
- UI: selección de opción válida por producto y operación incierta con payload congelado, doble submit bloqueado, reintento/recuperación explícitos y nueva operación explícita.

Evidencia: backend `26 passed, 5 skipped`; PostgreSQL aislado `4 passed`; frontend `11 passed`, typecheck/build correctos; npm audit `0`; pip-audit aislado `No known vulnerabilities found`; Compose tres servicios healthy; capturas `docs/design-review/ux-ciclo-dos-1440.jpg(.b64)` y `ux-ciclo-dos-390.jpg(.b64)`. Padre aún debe aceptar.

## Estado posterior a revisión FINAL EXTERNA — pausado

La segunda revisión FINAL EXTERNA no aprobó `5265f6b`. El estado vigente es **NO_APROBADO_PARA_VENTAS_REALES** y el alcance es `development-demo`. El presupuesto de dos ciclos está agotado: no se corrige código ni se inicia un tercer ciclo en esta pausa. Los cinco hallazgos concretos, su reproducción y los tests faltantes están en [`ESTADO_PENDIENTE.md`](ESTADO_PENDIENTE.md).

Los resultados históricos (`backend 26/5`, PostgreSQL `4`, frontend `11`, typecheck/build y auditorías) se conservan, pero no cubren doble submit antes del render, intención de venta independiente de membresía, whitelist exacta de unique constraints, congelación visible del payload ni validación estricta de tipos/opciones. No se afirma ausencia total de vulnerabilidades de seguridad.
