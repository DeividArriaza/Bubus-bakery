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
