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

## Cobertura pendiente

Resultados históricos del implementador: backend 26 passed/5 skipped, PostgreSQL aislado 4 passed, frontend 11 passed, typecheck/build correctos, npm audit 0 y pip-audit 0. El padre reprodujo separadamente sobre `5265f6b`: backend 27 passed/4 skipped/2 warnings con `REPO_ROOT` configurada, frontend 11 passed/typecheck/build, pip-audit 0, npm audit 0 y PostgreSQL real remoto 4 passed. Ningún resultado cubre por sí solo todos los casos señalados ni permite afirmar ausencia total de vulnerabilidades o preparación para ventas.

Debe añadirse en un ciclo autorizado, sin borrar volúmenes:

- pruebas agrupadas de doble submit para solicitud y venta;
- pruebas PostgreSQL de miembro desactivado, dos emails no miembros, payload legacy y replay histórico;
- concurrencia con intenciones distintas bajo la misma clave;
- unique violation ajena a idempotencia;
- tipos inválidos para métodos/intenciones y opciones falsy en operación nueva y replay;
- UI que congele y muestre el payload pendiente real durante red incierta.

## Alcance diferido y límites

Puntos, Wallet, Google, verificación/recuperación de correo y reglas de cobertura, costo y logística de envíos siguen diferidos. No se implementa ni afirma disponibilidad de pagos con tarjeta, producción, despliegue remoto o ventas reales. No hay nuevas decisiones de negocio en este documento.

## Referencias

- [README y uso local](../README.md)
- [Instrucciones del repositorio](../AGENTS.md)
- [Plan de acción](PLAN_DE_ACCION.md)
- [Revisión independiente y evidencia histórica](REVISION_INDEPENDIENTE.md)
- [Verificación inicial y resultados](VERIFICACION_INICIAL.md)
- [Avance autónomo](AVANCE_AUTONOMO.md)
