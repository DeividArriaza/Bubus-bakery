# AGENTS.md — Bubu's bakery

Guía para cualquier agente (Hermes, Claude Code, Codex) que trabaje en este repositorio. Léela completa antes de actuar.

## Qué es

Producto para Bubu's bakery, repostería real de brownies en Guatemala: landing con catálogo, cuentas de cliente, solicitudes web de cajas y un POS para la dueña y el usuario. Moneda GTQ y toda la UI en español.

Estado vigente: **NO_APROBADO_PARA_VENTAS_REALES** (`development-demo`). No afirmar que está listo para producción ni usarlo con ventas reales. No hay app nativa ni Wallet implementados.

## Documentos que mandan

| Documento | Para qué |
| --- | --- |
| [`docs/PLAN_DE_ACCION.md`](docs/PLAN_DE_ACCION.md) | Contexto de negocio, requisitos confirmados, propuestas y decisiones pendientes. Fuente de verdad del alcance. |
| [`docs/ESTADO_PENDIENTE.md`](docs/ESTADO_PENDIENTE.md) | Hallazgos de revisiones externas, ciclos de corrección y pendientes técnicos. |
| [`docs/INSUMOS_PENDIENTES.md`](docs/INSUMOS_PENDIENTES.md) | Lo que falta aportar o decidir por parte del negocio (fotos, marca, envíos, puntos…). |
| [`README.md`](README.md) | Cómo levantar y probar en local. |
| [`docs/BubusFigma.pdf`](docs/BubusFigma.pdf) | Referencia visual de diseño. |
| [`skills/senior-engineering/SKILL.md`](skills/senior-engineering/SKILL.md) | Antes de escribir, corregir o revisar código (TDD). |
| [`skills/git-multiple-accounts/SKILL.md`](skills/git-multiple-accounts/SKILL.md) | Antes de tareas de Git, SSH o publicación. |
| `docs/checkpoints/*.json`, `docs/REVISION_*.md`, `docs/VERIFICACION_INICIAL.md`, `docs/AVANCE_AUTONOMO.md` | Evidencia histórica; no reescribir resultados pasados. |

## Mapa del repositorio

```text
compose.yaml            db (PostgreSQL 16) + api (FastAPI) + frontend (Vite/React)
.env.example            variables obligatorias de Compose (copiar a .env local, nunca commitear)
backend/
  app/main.py           rutas FastAPI (create_app); migraciones + seed al arrancar
  app/auth.py           sesiones opacas en cookie bubus_session, scrypt, control de Origin
  app/commerce.py       pedidos y ventas: precios, snapshots, idempotencia
  app/db.py             runner de migraciones (schema_migrations) y seed idempotente del catálogo
  app/models.py         modelos SQLAlchemy
  app/bootstrap_operator.py   crea el usuario operador del POS
  migrations/NNN_*.sql  migraciones versionadas (001–009); nunca editar una ya aplicada
  tests/                pytest; test_postgres_integrity.py requiere TEST_DATABASE_URL
frontend/
  src/App.tsx           landing, catálogo, cuentas, solicitud web y POS
  src/api.ts auth.ts orders.ts types.ts   cliente de la API (/api) y contratos
  public/assets/        imágenes (provisionales hasta tener fotos reales)
  vite.config.ts        proxy /api → API_PROXY_TARGET
docs/                   plan, estado, insumos, revisiones y evidencia
skills/                 skills del repositorio para agentes
```

## Servicios y puertos locales

| Servicio | Host | Interno | Notas |
| --- | --- | --- | --- |
| frontend | `127.0.0.1:5173` | 5173 | proxy `/api` a `http://api:8000` dentro de Compose |
| api | `127.0.0.1:8100` | 8000 | `GET /api/health`, `GET /api/catalog` |
| db | sin puerto publicado | 5432 | volumen `postgres_data`; acceder con `docker compose exec db` |

Los puertos evitan choques con otros proyectos de esta máquina (8000, 8080, 3306, 3396 y 6379 están ocupados). No publicar en 8000.

## Comandos esenciales

```bash
docker compose up -d --build                     # levantar todo
docker compose ps                                # esperar healthy
docker compose run --rm -T -v "$PWD/backend:/app" api pytest -q
docker compose exec -T api sh -lc 'TEST_DATABASE_URL="$DATABASE_URL" pytest -q tests/test_postgres_integrity.py'
cd frontend && npm ci && npm run test:run && npm run typecheck && npm run build
docker compose down                              # nunca con -v sin autorización
```

## Reglas

1. Leer el plan, el estado y el encargo antes de trabajar; distinguir requisitos confirmados, propuestas y decisiones pendientes.
2. No inventar reglas de negocio, precios, textos de marca, fotos, horarios, cobertura de envíos ni puntos. Las reglas de puntos esperan el cálculo de costes aprobado. Si una decisión pendiente bloquea, reportarla.
3. Los pedidos web/app son alcance aprobado de la primera versión, sin asumir pasarela de pagos, integración automática con WhatsApp/Instagram ni puntos por crear un pedido.
4. El backend es la fuente de verdad. Web y app solo usan la API; nunca la base de datos.
5. Importes en centavos de GTQ calculados en backend; precio y composición se congelan por venta.
6. Pedidos y ventas son idempotentes (`idempotencyKey`): un reintento nunca debe crear un registro duplicado.
7. Código con TDD: RED real, GREEN mínimo y suite completa (backend, PostgreSQL, frontend, typecheck y build) antes de declarar terminado.
8. Seguridad: secretos fuera de Git, datos sintéticos (`@example.invalid`) en pruebas y nunca datos reales de clientes.
9. No borrar el volumen `postgres_data` ni hacer `DROP`, `TRUNCATE` o correcciones manuales de ventas sin autorización expresa.
10. Git: commits y PRs como DeividArriaza, en español y sin `Co-Authored-By` ni menciones de Claude o IA. Commit, push, merge a `main`, force-push y despliegues solo con autorización expresa del encargo.
11. Preservar cambios ajenos, limitar ediciones al alcance autorizado y verificar cada tarea con evidencia.

## Flujo de trabajo actual

- Rama de trabajo: `feat/base-catalogo`, PR #2 hacia `main` en `DeividArriaza/Bubus-bakery`.
- Ciclo: implementar con TDD → revisión externa por otro agente en solo lectura → corregir → nueva revisión. Registrar cada ciclo en `docs/ESTADO_PENDIENTE.md`.
- El estado `NO_APROBADO_PARA_VENTAS_REALES` solo se levanta con una revisión externa aprobatoria y la decisión del usuario.

## Fuera de alcance por ahora

Puntos y canjes, Google Wallet y Apple Wallet, app nativa o PWA, pagos con tarjeta, cobertura y costo de envíos, inventario, verificación y recuperación de correo, login con Google y despliegue a producción.
