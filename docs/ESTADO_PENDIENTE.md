# Estado pendiente de aceptación

Fecha: 2026-10-08 · rama `feat/base-catalogo` · base publicada `5265f6b2e04b955c4ff09d20a3306ef3a1dbec45`

## Estado vigente

**NO_APROBADO_PARA_VENTAS_REALES**. El alcance actual es `development-demo`; no debe usarse con ventas reales hasta resolver los hallazgos de la revisión final externa. Se alcanzó el límite operativo de dos ciclos adoptado para esta revisión; se pausa a la espera de acordar el siguiente ciclo.

La revisión fue externa al implementador. Este agente no la presenta como una revisión propia ni como aprobación. En esta pausa solo se publica documentación.

## Hallazgos reproducidos por la revisión externa

1. **Alta — doble submit antes del render de React.** En `frontend/src/App.tsx` alrededor de las líneas 96–100 y 134–138, `busy`/`pending` son estado asíncrono. Dos submits en el mismo turno pueden pasar ambos guardas y hacer dos llamadas con UUID distintas para pedidos o ventas. Pendiente: lock síncrono con `useRef`, asignando clave y payload antes del primer `await`, y tests con submits agrupados.

2. **Media — intención de venta depende de membresía actual.** `customerId` se resuelve antes de guardar la intención. Un replay con miembro desactivado puede responder `409`; dos correos no miembros pueden colisionar como la misma intención. Pendiente: conservar `customerEmail` normalizado en la intención original, independiente de la membresía posterior, con pruebas PostgreSQL para miembros, legacy y replay.

3. **Media — whitelist incompleta de unique violations.** `is_idempotency_unique` acepta cualquier SQLSTATE `23505` cuyo texto/constraint contenga `orders` o `sales`, pudiendo absorber una restricción única ajena como si fuera idempotencia. Pendiente: permitir únicamente los nombres exactos de las restricciones de idempotencia y probar una unique violation no relacionada.

4. **Media — payload mostrado y payload reintentado divergen.** Durante el envío los campos siguen editables; por ejemplo, el draft puede pasar de cantidad 1 a 5 tras el primer submit, mostrar 5 después de un fallo de red y reintentar el payload original 1. Pendiente: congelar payload desde el inicio, bloquear edición mientras la operación está incierta y mostrar el snapshot realmente pendiente.

5. **Media — validación no estricta de tipos.** `paymentIntent`/`paymentMethod` pueden causar `TypeError` al evaluar pertenencia de listas/sets con objetos no hashables, produciendo 500. Además, `raw.get("options") or {}` acepta `[]`, `false`, `0` o `""` como `{}` en replay aunque una operación nueva debería responder 422. Pendiente: validar tipos estrictamente y de forma uniforme antes de usar sets o normalizar opciones.

## Ciclo 3 autorizado (2026-10-19) — avance verificado, pendiente de revisión

- **Hallazgo 1 corregido** (commit `1a250b2`): `inFlight`/`pendingRef` con `useRef` en solicitud y venta; clave y payload fijados antes del primer `await`. RED real: 3 pruebas nuevas con submits agrupados en un mismo `act` fallaron (2 llamadas en vez de 1; 3 en vez de 2 para reintento+recuperar). GREEN: frontend 14 passed, typecheck y build correctos.
- **Hallazgo 4 corregido** (sin commit al registrar esto): con operación pendiente (en curso o incierta) los campos quedan deshabilitados y muestran el snapshot enviado; el reintento usa ese mismo payload. RED real: 3 pruebas nuevas (edición durante envío, cantidad 1→5 en el mismo turno del submit) fallaron. GREEN: frontend 17 passed, typecheck y build correctos.
- **Hallazgos 2, 3 y 5 corregidos** en backend: la intención de venta guarda el SHA-256 del correo normalizado (no `customerId`) y la membresía solo se resuelve al crear; las intenciones legacy con `customerId` se traducen al comparar. `is_idempotency_unique` solo acepta `orders_customer_id_idempotency_key_key` / `sales_actor_id_idempotency_key_key` (y su texto SQLite exacto). `paymentIntent`/`paymentMethod` exigen `str` y `options` solo admite `null` u objeto, en operación nueva y replay. RED real: 5 fallos SQLite, 1 fallo PostgreSQL e `ImportError` del whitelist. GREEN: `docker compose run --rm -T -v "$PWD/backend:/app" api pytest -q` → 33 passed, 8 skipped; suite PostgreSQL aislada → 7 passed.
- Limitación conocida: una intención legacy sin miembro (`customerId` nulo) no conservó el correo; su replay solo coincide si el correo enviado hoy no pertenece a ningún usuario.

## Revisión externa del PR #2 (Codex, 2026-10-19) — ciclo 4

Resultado de la revisión: **NO APROBADO** para ventas reales; se mantiene `NO_APROBADO_PARA_VENTAS_REALES`.

Corregidos con TDD en este ciclo (RED real antes del cambio, pendiente de nueva revisión):

- **Hallazgo 1 — Alta:** una venta o solicitud incierta perdía clave y payload al recargar, desmontar o pulsar «Nueva venta/solicitud». Ahora la operación pendiente se guarda en `localStorage` (por usuario y tipo) antes del primer `await`, se restaura al montar con el formulario bloqueado y se quitaron los botones «Nueva …». Solo se libera tras éxito o rechazo definitivo 4xx (salvo 408/429); red caída o 5xx la mantienen pendiente. RED: 4 pruebas fallaron; GREEN: frontend 23 passed.
- **Hallazgo 3 — Media:** `PATCH /api/operator/orders/{id}` devolvía 500 con `status` no string; ahora responde 422. RED: 1 prueba falló; GREEN incluido abajo.
- **Hallazgo 6 — Baja:** el proxy de Vite estaba fijo en `http://api:8000`. Ahora usa `API_PROXY_TARGET` (Compose: `http://api:8000`; por defecto fuera de Compose: `http://127.0.0.1:8100`), documentado en el README. RED: prueba de configuración y de Compose fallaron.

Verificación: backend 35 passed, 7 skipped; PostgreSQL aislado 7 passed; frontend 23 passed, typecheck y build correctos; `docker compose up -d --build api frontend` con servicios healthy y `127.0.0.1:5173/api/catalog` devolviendo 9 productos vía proxy.

**Pendientes de decisión del usuario (no se tocaron):** hallazgos **2, 4 y 5** de esta revisión. Su detalle está en el reporte de la revisión externa de Codex, que no se incorporó a este repositorio; deben registrarse aquí cuando se decida cómo abordarlos.

## Cobertura pendiente

Resultados históricos del implementador: backend 26 passed/5 skipped, PostgreSQL aislado 4 passed, frontend 11 passed, typecheck/build correctos, npm audit 0 y pip-audit 0. El padre reprodujo separadamente sobre `5265f6b`: backend 27 passed/4 skipped/2 warnings con `REPO_ROOT` configurada, frontend 11 passed/typecheck/build, pip-audit 0, npm audit 0 y PostgreSQL real remoto 4 passed. Ningún resultado cubre por sí solo todos los casos señalados ni permite afirmar ausencia total de vulnerabilidades o preparación para ventas.

Debe añadirse en un ciclo autorizado, sin borrar volúmenes:

- ~~pruebas agrupadas de doble submit para solicitud y venta;~~ (ciclo 3)
- ~~pruebas PostgreSQL de miembro desactivado, dos emails no miembros, payload legacy y replay histórico;~~ (ciclo 3)
- ~~concurrencia con intenciones distintas bajo la misma clave;~~ (ciclo 3)
- ~~unique violation ajena a idempotencia;~~ (ciclo 3)
- ~~tipos inválidos para métodos/intenciones y opciones falsy en operación nueva y replay;~~ (ciclo 3)
- ~~UI que congele y muestre el payload pendiente real durante red incierta.~~ (ciclo 3)

## Alcance diferido y límites

Puntos, Wallet, Google, verificación/recuperación de correo y reglas de cobertura, costo y logística de envíos siguen diferidos. No se implementa ni afirma disponibilidad de pagos con tarjeta, producción, despliegue remoto o ventas reales. No hay nuevas decisiones de negocio en este documento.

## Referencias

- [README y uso local](../README.md)
- [Instrucciones del repositorio](../AGENTS.md)
- [Plan de acción](PLAN_DE_ACCION.md)
- [Revisión independiente y evidencia histórica](REVISION_INDEPENDIENTE.md)
- [Verificación inicial y resultados](VERIFICACION_INICIAL.md)
- [Avance autónomo](AVANCE_AUTONOMO.md)
