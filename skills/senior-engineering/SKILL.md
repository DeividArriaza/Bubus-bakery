---
name: senior-engineering
description: "Use when writing, fixing, reviewing or refactoring code in Bubus-bakery (React + TypeScript, FastAPI, PostgreSQL, Docker Compose)."
version: 0.1.0
author: DeividArriaza
license: MIT
platforms: [windows, linux, macos]
metadata:
  tags: [engineering, tdd, react, fastapi, postgresql, efficiency, review]
---

# Ingeniería senior en Bubus-bakery

## Cuándo usar

Antes de escribir, corregir, revisar o refactorizar código del repositorio. Complementa [`AGENTS.md`](../../AGENTS.md) y [`docs/PLAN_DE_ACCION.md`](../../docs/PLAN_DE_ACCION.md); no los sustituye. Para Git y publicación usar [`git-multiple-accounts`](../git-multiple-accounts/SKILL.md).

## Mentalidad

- Resolver el problema real con el cambio más pequeño y correcto. Un diff corto y entendible vale más que una abstracción "por si acaso".
- Entender antes de tocar: leer el código afectado, sus pruebas y los documentos de estado (`docs/ESTADO_PENDIENTE.md`) antes de proponer cambios.
- Decidir con criterio y explicarlo en una línea; no presentar listas de opciones que no se van a seguir.
- Las reglas de negocio pendientes (puntos, envíos, costes, Wallet) no se inventan: se reportan como bloqueo.
- Dejar el código mejor de lo que estaba solo dentro del alcance encargado; lo demás se anota como hallazgo.

## Flujo de trabajo

1. **Contexto:** rama, `git status`, plan y hallazgo concreto. Preservar cambios ajenos.
2. **RED:** escribir primero una prueba que reproduzca el defecto o el comportamiento nuevo y verla fallar por la razón correcta. Un fallo por entorno (dependencia ausente, import roto) no cuenta como RED.
3. **GREEN:** el cambio mínimo que la hace pasar, siguiendo el estilo del archivo (naming, densidad de comentarios, idioma de los mensajes: español).
4. **Verificar:** suite completa + typecheck + build del lado tocado (ver comandos). Revisar el diff completo antes de declarar terminado.
5. **Reportar:** archivos cambiados, RED/GREEN con números reales, verificaciones no ejecutadas y por qué, riesgos residuales.
6. **Sin commit, push ni deploy** salvo autorización expresa del encargo.

## Principios de código

### Generales

- Nombres que expliquen intención; comentarios solo para el *por qué* no obvio.
- Validar en los bordes (entrada HTTP, formularios) y confiar en los invariantes dentro.
- Fallar de forma explícita y en español para el usuario; nunca tragar excepciones genéricas.
- No duplicar reglas de negocio entre frontend y backend: el backend es la fuente de verdad; el frontend solo refleja.
- Dinero siempre en centavos enteros GTQ; nunca `float`.

### Frontend (React 19 + TypeScript)

- Estado de React es asíncrono: para guardas que deben ser inmediatas (doble submit, operación en curso) usar `useRef` y fijar clave + payload antes del primer `await`.
- Con una operación pendiente o incierta, la UI muestra y reintenta el snapshot realmente enviado, no el borrador editable.
- Derivar valores en render en lugar de duplicarlos en estado; `useMemo` solo cuando el cálculo es caro o la identidad importa.
- Tipos estrictos: sin `any`; preferir uniones literales (`"efectivo" | "transferencia"`).
- Pruebas con Testing Library por rol/etiqueta accesible; simular eventos agrupados con `act(() => { ... })` cuando el defecto depende del mismo turno.

### Backend (FastAPI + PostgreSQL)

- Operaciones con efecto (pedido, venta, canje) son idempotentes: clave + intención normalizada; replay idéntico → mismo resultado, intención distinta → `409`.
- Concurrencia resuelta en la base: transacciones, `SELECT ... FOR UPDATE`, restricciones únicas con nombre explícito. Solo absorber la `UniqueViolation` de la restricción de idempotencia exacta.
- Validar tipos estrictamente antes de usar sets, dicts o normalizar opciones; un tipo inválido es `422`, nunca `500`.
- Evitar N+1: cargar relaciones en una consulta; revisar índices cuando se filtra o une por columnas nuevas.
- Migraciones solo aditivas y versionadas (`backend/migrations/NNN_*.sql`); el seed nunca sobrescribe datos existentes.
- Snapshots históricos de precio/composición en cada línea; no reinterpretar ventas antiguas con el catálogo actual.
- SQLite sirve para validación rápida; concurrencia, locks y unicidad se prueban en PostgreSQL (`tests/test_postgres_integrity.py`).

### Seguridad

- Secretos solo en `.env` local (ignorado); nunca en código, docs, logs ni mensajes.
- Autorización en el servidor por rol; el cliente nunca recibe datos de otros clientes ni objetos de operador.
- No borrar volúmenes (`docker compose down -v`) ni datos reales sin autorización.

## Eficiencia

- Medir antes de optimizar; optimizar el cuello de botella real (consultas, renders repetidos, payloads grandes), no micro-detalles.
- Complejidad razonable por defecto: evitar bucles anidados sobre colecciones que crecen, búsquedas lineales repetidas (usar `Map`/`dict`/`set`), y consultas dentro de bucles.
- No agregar dependencias para lo que resuelve la biblioteca estándar o unas pocas líneas; cada dependencia nueva requiere justificación y auditoría.

## Comandos de verificación

Frontend (`frontend/`):

```text
npm ci
npm run test:run
npm run typecheck
npm run build
npm audit --audit-level=moderate
```

Backend con Docker (raíz del repo, requiere `.env`):

```text
docker compose up -d --build
docker compose exec -T api pytest -q
docker compose exec -T api sh -lc 'TEST_DATABASE_URL="$DATABASE_URL" pytest -q tests/test_postgres_integrity.py'
```

Notas de entorno Windows: el backend requiere Python 3.12/3.13 (el lock incluye `uvloop`, solo Linux); usar Docker como vía canónica. Sin red hacia Docker Hub no se pueden construir las imágenes: reportarlo como bloqueo, no como fallo de pruebas.

## Revisión antes de entregar

- [ ] ¿La prueba nueva falló antes del cambio y pasa después?
- [ ] ¿El diff se limita al encargo y respeta el estilo existente?
- [ ] ¿Hay manejo de errores, concurrencia e idempotencia donde hay efectos?
- [ ] ¿Se ejecutaron suite, typecheck y build del lado tocado? ¿Qué no se pudo ejecutar?
- [ ] ¿Se actualizó `docs/ESTADO_PENDIENTE.md` solo con avance verificado?
