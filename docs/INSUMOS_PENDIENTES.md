# Insumos pendientes del negocio

Lo que el código no puede resolver solo: material y decisiones que debe aportar o aprobar la dueña o el usuario. Mientras falten, los agentes no deben inventarlos. Al resolver uno, marcarlo y anotar la fecha y la fuente.

## A. Material de marca y contenido (lo aporta el negocio)

- [ ] **Fotos reales de producto**: una por cada sabor (Snicker/Snickers, M&M, almendra, simple) y por cada caja (6 de un tipo y mixta). Fondo limpio, luz natural, horizontal, mínimo 1600 px. Hoy se usan 2 fotos provisionales (`frontend/public/assets/`).
- [ ] **Foto principal (hero)** de la landing, y opcionalmente fotos de la dueña, del proceso o de entregas.
- [ ] **Logo** en SVG o PNG con fondo transparente, más un favicon.
- [ ] **Paleta y tipografía aprobadas**. Hoy: rosa pálido, blanco y vino/coral como propuesta; existe referencia en `docs/BubusFigma.pdf`.
- [ ] **Textos aprobados**: frase principal, historia breve («quiénes somos»), descripción de cada producto e ingredientes o alérgenos (nueces, maní, lácteos, gluten).
- [ ] **Nombre comercial final**: «Snicker» o «Snickers».
- [ ] **Canales de contacto reales**: número de WhatsApp, usuario de Instagram y correo, para los botones de compra y contacto.
- [ ] **Horarios, días de entrega y tiempo de anticipación** para pedidos por encargo.

## B. Decisiones de operación

- [ ] **Envíos**: cobertura (zonas o municipios), costo, proveedor o entrega propia y programación.
- [ ] **Pagos**: cómo se confirma una transferencia (comprobante, verificación manual) y datos bancarios que se muestran, si aplica.
- [ ] **Flujo del pedido web**: quién lo revisa, cómo se confirma al cliente y estados que verá.
- [ ] **Operadores del POS**: quiénes tendrán acceso (la dueña y el usuario) y desde qué dispositivos.

## C. Decisiones técnicas abiertas de la revisión externa (ver `ESTADO_PENDIENTE.md`)

- [ ] Ventas antiguas de invitados sin correo: tratarlas siempre como conflicto con reconciliación manual o aceptar el riesgo.
- [ ] Verificación de correo al crear cuentas, o aceptar por ahora que una cuenta sin verificar quede asociada a ventas con ese correo.
- [ ] Hash del correo de ventas: cambiar a HMAC con secreto o tratarlo y protegerlo como dato personal.

## D. Fases posteriores (no bloquean la primera versión)

- [ ] Programa de puntos: requiere el cálculo de costes aprobado, la regla de acumulación, canjes y el momento de acreditación.
- [ ] Google Wallet y Apple Wallet: cuentas de emisor y certificados.
- [ ] App: nativa, multiplataforma o PWA.
- [ ] Login con Google y recuperación de contraseña por correo: proveedor de correo, credenciales y redirect URI.
- [ ] Publicación: dominio, hosting, base de datos administrada, respaldos y HTTPS.
- [ ] Datos personales: aviso de privacidad, consentimiento y política de retención.
