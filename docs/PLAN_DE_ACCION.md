# Bubu's bakery — Plan de acción y contexto persistente

## 1. Estado y autoridad del documento

- Versión: 0.5 — stack, idioma, diseño adaptable, cuentas, solicitudes web y POS básico confirmados; pagos externos, puntos e inventario siguen fuera.
- Este documento conserva el contexto de negocio y orienta futuras tareas delegadas. NO autoriza implementar todos los módulos ni tomar decisiones pendientes sin aprobación.
- Los agentes deben leerlo antes de trabajar y limitarse al encargo concreto recibido.
- Distinguir requisitos confirmados, propuestas y decisiones pendientes. Una propuesta no es una decisión aprobada.
- Los cambios de alcance o reglas de negocio deben acordarse con el usuario y registrarse aquí antes de implementarlos.
- Stack de la primera entrega confirmado por el usuario: React + TypeScript, FastAPI, PostgreSQL y Docker Compose. No implica aprobar presupuesto, cronograma ni reglas de puntos.
- Idioma confirmado para todo texto visible de UI y mensajes: español. La referencia Figma se adapta; su copy de muestra no se trata como hecho de negocio.

## 1.1 Estado implementado verificable

- [x] Rama de trabajo `feat/base-catalogo` creada sin perder documentos locales.
- [x] Landing responsive con hero y catálogo consumiendo la API.
- [x] API FastAPI de salud y lectura pública del catálogo.
- [x] PostgreSQL en Compose con migración `001_initial.sql`, seed idempotente y volumen persistente.
- [x] Productos individuales/cajas, precios en centavos GTQ y composición/opciones de caja mixta.
- [x] Catálogo normalizado de 9 vendibles (4 individuales y 5 cajas compuestas), con componentes configurables y seed no destructivo; la fila demo legacy `mixta` queda inactiva.
- [x] Pruebas backend y frontend, typecheck, build y recorrido visual desktop/móvil verificados; evidencia en `docs/VERIFICACION_INICIAL.md`.
- [x] Registro/login/logout de clientes, consulta de sesión, sesiones opacas revocables, contraseñas con scrypt, cookies HttpOnly/SameSite, CORS acotado y protección Origin/CSRF.
- [x] Solicitudes autenticadas para envío de cajas: subtotal backend, snapshot histórico de precio/composición, elección mixta exacta, idempotencia y privacidad por cliente.
- [x] Panel operador protegido: consulta/gestión de solicitudes y ventas POS de efectivo/transferencia con actor, fecha, importes y confirmación explícita.
- [ ] Verificación/recuperación por correo y Google: proveedor, credenciales y redirect URI pendientes; la UI no simula estas capacidades.
- [ ] Tarjeta, cobro automático, cobertura/coste/logística de entrega, devoluciones, inventario, puntos, Wallet e integraciones sociales: no implementados.

## 2. Contexto confirmado

Bubu's bakery es una repostería real de la novia del usuario. Su actividad principal es la venta de brownies. El objetivo es construir un producto que ayude a presentar el negocio, fomentar compras recurrentes y controlar sus ventas.

Operación actual conocida: la dueña registra las ventas en un chat de WhatsApp, indicando el nombre de la persona a quien vendió, cuántos brownies y de qué tipo, y el medio de pago: efectivo o transferencia. Recibe pedidos por WhatsApp e Instagram.

La operación incluye brownies disponibles y brownies preparados por encargo. Tiene envíos para personas en Guatemala; en esa modalidad vende únicamente cajas de 6 brownies, mixtas o de un tipo específico. El pago puede ser al pedir o al recibir. Fuera de envíos también vende individuales en la universidad, llevados en una especie de bolsa. Esto no significa que todas las ventas sean por caja ni que los envíos cubran cualquier dirección del país: cobertura detallada, costo y proveedor quedan pendientes.

El usuario aprueba como alcance de la primera versión propuesta recibir pedidos mediante web/app y permitir que esos canales acumulen puntos cuando las reglas futuras estén aprobadas. Esto no implica pasarela de pagos, integración automática con WhatsApp/Instagram ni emisión automática de puntos por crear un pedido.

Moneda confirmada: quetzales (Q / GTQ). Catálogo confirmado:

| Producto | Individual | Caja de 6 |
| --- | --- | --- |
| Simple | Q10 | Q60 |
| M&M | Q15 | Q75 |
| Snicker / Snickers | Q17 | Q80 |
| Almendra | Q15 | Q70 |
| Mixta | No aplica | Q85 |

La caja mixta tiene composición fija: 2 Snicker + 3 M&M + 1 brownie de almendra o simple, a elección del cliente. No es totalmente libre y no se informó recargo: Q85 en ambos casos. La nomenclatura comercial final de Snicker/Snickers queda pendiente.

El usuario solicita:

1. Una landing page para el negocio.
2. Un sistema de puntos por compras de brownies, canjeables por brownies gratuitos.
3. Un sistema POS para controlar ventas de los productos de Bubu's bakery.
4. Disponibilidad tanto como web como app.
5. Un plan en Markdown que sirva como contexto persistente para los agentes.

La forma de trabajo y los detalles se conversarán posteriormente. No asumir sucursales, volumen de ventas, datos de clientes ni identidad visual. No extrapolar las cajas de envío a todas las ventas.

## 3. Objetivo del producto

Conectar presencia pública, fidelización y operación comercial mediante información consistente: catálogo, ventas, clientes participantes, puntos y canjes.

La web y la app deben consultar la misma fuente de verdad para ventas y puntos. No mantener saldos independientes por canal. Esta es una propuesta de diseño a validar, no una selección de tecnologías.

## 4. Usuarios y canales — confirmados y propuestas pendientes

| Perfil | Necesidades | Acceso propuesto |
| --- | --- | --- |
| Visitante | Conocer brownies y otros productos, consultar cómo comprar | Landing pública |
| Cliente participante | Iniciar sesión para pedir por web/app y, cuando se aprueben reglas, consultar puntos y recompensas | Web y app; login pendiente de diseño |
| Personal de ventas | Registrar ventas, identificar clientes y gestionar canjes autorizados | POS móvil responsive y web |
| Dueña / administración | Mantener catálogo, configurar fidelización, revisar ventas y controlar accesos | Panel protegido |

El POS será usado por la dueña y el usuario, desde celular y web. Una interfaz POS móvil responsive y una interfaz web son necesidades confirmadas. Dos operadores con accesos individuales, permisos concretos y dispositivos o sistemas operativos compatibles son una propuesta a validar. La app nativa, multiplataforma o PWA siguen pendientes.

No asumir que todos los módulos necesitan estar en todos los canales. Definir qué incluye la app, quién la utiliza y si se requiere Android, iOS o ambos.

## 5. Alcance funcional

### 5.1 Landing page

**Requisito confirmado:** presentar el negocio mediante una landing.

**MVP propuesto:**

- Presentación de marca y propuesta del negocio.
- Catálogo o sección de productos, con brownies como foco principal.
- Fotografías, descripciones y precios solo si los aporta o aprueba la dueña.
- Explicación sencilla del programa de puntos cuando sus reglas estén definidas.
- Llamada a la acción para comprar o contactar; canal pendiente de aprobación.
- Diseño responsive, navegación accesible, rendimiento y metadatos básicos de buscadores.

**Aceptación propuesta:** funciona en móvil y escritorio; no publica información inventada; enlaces y llamadas a la acción son reales; no expone el POS ni datos privados.

La landing NO implica automáticamente checkout, pagos en línea, delivery ni pedidos dentro del sistema.

### 5.2 Programa de puntos

**Requisito confirmado:** acumular puntos por compras de brownies y canjearlos por brownies gratis.

**Objetivo confirmado; entrega posterior al cálculo de costes:** el programa no se descarta, pero no se definirán ni activarán fórmulas, umbrales, equivalencias o canjes antes de ese análisis y de la aprobación del usuario y la dueña.

**MVP propuesto, sujeto a reglas aprobadas:**

- Identificar al cliente participante con un mecanismo acordado.
- Asociar compras elegibles con el cliente.
- Registrar acumulaciones, canjes, reversos y ajustes como movimientos auditables.
- Mostrar saldo e historial al cliente y al personal autorizado.
- Validar saldo suficiente y registrar el producto gratuito entregado.
- Permitir reglas configurables sin fijar valores arbitrarios.

**Decisiones pendientes obligatorias:**

- ¿Se gana por unidad, por monto pagado o por otra regla?
- ¿Qué productos y variantes participan? ¿Qué pasa con descuentos y promociones?
- ¿Cuántos puntos requiere cada recompensa y qué brownie se entrega?
- ¿Los puntos vencen? ¿Hay límites de acumulación o canje?
- ¿Cuándo se acreditan: al registrar la venta o al confirmar su pago?
- ¿Cómo afectan anulaciones, devoluciones y devoluciones parciales?
- ¿Una recompensa genera puntos? ¿Se permite compra y canje en la misma venta?
- ¿Qué ocurre si se devuelve una compra cuyos puntos ya fueron gastados?
- ¿Cómo se identifica al cliente y cómo se recupera su acceso?
- ¿Se migrarán compras o saldos anteriores?
- ¿Cómo se calculan puntos para unidades frente a productos compuestos o cajas? No asumir puntos por caja.

**Flujos presenciales y online propuestos:**

- En venta presencial, identificar al participante con QR mediante la cámara del celular o con búsqueda manual restringida; asociar la venta, registrar efectivo/transferencia y confirmar la recepción del pago.
- En pedidos online, la identidad proviene de la cuenta autenticada y no requiere escaneo.
- Pedido, pago y entrega permanecen separados. El momento exacto de acreditación —pago, entrega o ambos— queda pendiente de decisión del negocio.
- No acreditar dos veces por caja y componentes. Los movimientos y canjes deben confirmarse de forma consistente e idempotente.

**Invariantes técnicas propuestas:**

- Calcular y validar puntos en el servidor, nunca confiar en un saldo enviado por la app.
- Un reintento de la misma venta o canje no duplica movimientos.
- Canjes concurrentes no pueden gastar el mismo saldo dos veces.
- Guardar los puntos aplicados y la versión de reglas para conservar el historial aunque cambie la configuración.
- Venta, movimiento de puntos y canje deben confirmarse de forma consistente; no dejar cambios parciales.
- No borrar movimientos para corregir errores: registrar reversos o ajustes autorizados con motivo y responsable.

**Aceptación propuesta:** pruebas de compra elegible/no elegible, saldo insuficiente, canje válido, reintentos, concurrencia, cancelación y devolución conforme a las reglas aprobadas.

### 5.3 POS y administración

**Requisito confirmado:** controlar las ventas de productos del negocio. El POS de Odoo es una referencia de experiencia sencilla, no una elección tecnológica ni una solicitud de instalar Odoo.

**MVP propuesto, incorporando el requisito confirmado de catálogo extensible:**

- Catálogo extensible: productos individuales y productos compuestos que contienen otros productos, con nombre, tipo, precio propio, estado activo y presentación.
- Composición configurable: producto contenedor, componente, cantidad y reglas de selección; permitir nuevas cajas, brownies y promociones agrupadas sin codificar cada combinación como excepción. El diseño técnico concreto queda pendiente.
- Capturar el nombre o referencia de la persona cliente sin exigirle una cuenta de fidelización.
- Distinguir brownies disponibles de brownies preparados por encargo.
- Modelar, cuando corresponda, la caja vendida y su composición por tipo con suma exacta de 6 unidades; la regla de 6 aplica a las cajas actuales, no a todo producto compuesto ni a promociones futuras.
- Modelar la caja mixta como 2 Snicker + 3 M&M + una elección limitada entre 1 almendra o 1 simple.
- Venta con líneas por tipo de brownie y cantidad, precios configurados y aprobados, descuentos permitidos y total.
- Registrar el medio de pago, inicialmente efectivo o transferencia, y el estado de la venta; registrar una transferencia no equivale a comprobar su recepción, cuyo mecanismo queda pendiente.
- Venta sin cliente identificado y venta asociada a un participante del programa.
- Acumulación/canje integrado con la venta según reglas aprobadas.
- Historial y detalle de ventas; anulación/devolución autorizada con trazabilidad.
- Resumen de ventas por período y por producto, separando ventas, devoluciones y recompensas.
- Preservar la composición y el precio históricos de cada venta; no inventar precios ni descuentos.
- Mantener el precio comercial propio del producto compuesto, independiente de la suma de componentes; no reinterpretar ventas antiguas con el catálogo actual.
- Validar ausencia de ciclos o autorreferencias en composiciones; profundidad de anidación, inventario y disponibilidad por componentes quedan pendientes.
- Roles y permisos para personal y administración, con accesos individuales propuestos para la dueña y el usuario.

**Aceptación propuesta:** una venta queda registrada una sola vez; conserva precios históricos; totales se calculan correctamente; el historial distingue estados; clientes no pueden usar funciones de personal; los puntos coinciden con las ventas asociadas.

**Pendiente de alcance:** inventario y lotes, recetas/costos, cierre de caja, comprobantes, obligaciones fiscales, impresora, lector, pagos integrados y operación offline. No prometer contabilidad ni facturación fiscal con un POS básico.

### 5.4 Web y app

**Requisito confirmado:** se busca tanto app como web; los pedidos mediante web/app son alcance aprobado de la primera versión propuesta. La disponibilidad efectiva de fidelización queda condicionada a reglas aprobadas.

**Opciones a evaluar, ninguna aprobada:**

- Web responsive y PWA instalable, si satisface lo que la dueña entiende por app.
- Web y aplicación móvil multiplataforma.
- Aplicaciones nativas cuando existan requisitos que lo justifiquen.

Una PWA no se considerará cumplimiento de la app sin aprobación explícita. Evaluar plataformas, instalación, publicación en tiendas, notificaciones, uso de cámara/QR, hardware del POS, conectividad y mantenimiento antes de decidir.

**Pedidos web/app — alcance aprobado, diseño y entrega pendientes:**

- La cuenta autenticada identifica al participante; la landing puede seguir siendo pública.
- Distinguir pedido de venta y definir cuándo un pedido se confirma, se cobra y se entrega.
- Representar por separado los estados del pedido, del pago y de la entrega, incluyendo pago al pedir o al recibir, sin asumir anticipos ni parcialidades.
- Para envíos, definir cobertura, costo, proveedor y programación; no asumir cobertura nacional ni que toda venta usa envío.
- En la modalidad de envío, evaluar cajas de 6 brownies, mixtas o de un tipo, sin convertir esa modalidad en regla general de ventas.
- No acreditar puntos por la mera creación de un pedido; el momento y las condiciones de acreditación deben seguir las reglas aprobadas.
- No asumir integración automática con WhatsApp o Instagram, carrito, checkout, delivery ni pasarela de pagos.

### 5.5 Cuentas, acceso y Wallet

**Confirmado:** ofrecer login normal y opción “Continuar con Google”. El cliente debe iniciar sesión para pedir por web/app y participar en puntos; una venta presencial del POS puede registrarse sin cuenta de cliente.

**Pendiente/propuesto:** definir el mecanismo concreto del login normal, verificación, recuperación, vinculación entre login normal, Google y Wallet, y uso de One Tap/ingreso automático. La vinculación debe requerir verificación apropiada; “login automático” no garantiza autenticación silenciosa.

**Wallet — alcance solicitado en ideación, fases pendientes:** evaluar tarjetas de fidelización para Google Wallet y Apple Wallet. La tarjeta puede usar identificador opaco/QR, saldo sincronizado y acceso al sitio, pero no es fuente de verdad ni permiso administrativo. No insertar credenciales o tokens duraderos en el QR; saldo de Wallet no sustituye la validación del backend. Revisar cuentas de emisor, certificados, elegibilidad, distribución y requisitos de login para iOS.

## 6. Arquitectura conceptual — stack inicial confirmado, detalles futuros pendientes

- Landing pública.
- Interfaz de clientes para cuentas, pedidos y fidelización, web y app según alcance aprobado.
- POS/panel privado.
- Backend compartido con autenticación, permisos y reglas de negocio.
- Persistencia transaccional para ventas y movimientos de puntos.
- Web y app acceden al backend/API; no se conectan directamente a la base de datos.
- Stack confirmado para esta base: React + TypeScript, FastAPI, PostgreSQL y Docker Compose.
- Base de datos en red privada; credenciales y reglas de precios, pedidos, permisos y puntos residen en el backend.
- **Requisito confirmado:** contenerizar por separado, al menos, frontend web, backend y base de datos; esto no exige microservicios ni selecciona proveedor cloud.

Entidades candidatas: producto, variante, composición, grupo de selección, cliente participante, cuenta de autenticación, usuario interno, pedido, línea de pedido, venta, línea de venta, registro de pago, estado de entrega, movimiento de puntos, recompensa, canje y evento de auditoría.

Separar identidad de cliente y permisos del personal. Guardar importes con precisión monetaria apropiada en quetzales (Q / GTQ), reglas explícitas de redondeo y precios históricos. Acordar zona horaria para reportes.

**Propuestas técnicas por validar:** Docker Compose para desarrollo y posible despliegue inicial en un solo host; volúmenes persistentes y respaldos/restauración de la base de datos; migraciones versionadas; configuración por entorno; secretos fuera de Git; HTTPS y comprobaciones de salud. Contenedores y volúmenes no sustituyen respaldos. No hay motor de base de datos, hosting ni estrategia de alta disponibilidad aprobados. La app móvil no se despliega como contenedor servidor.

## 7. Plan por fases y puertas de aprobación

### Fase 0 — Descubrimiento y acuerdos

- [x] Inspeccionar código, instrucciones, dependencias y estado Git del repositorio: solo README.md, sin código ni manifiestos, rama main siguiendo origin/main y árbol limpio antes de esta documentación.
- [x] Recopilar operación actual: ventas por WhatsApp con nombre, tipo, cantidad y medio de pago; pedidos por WhatsApp e Instagram; brownies disponibles y por encargo; individuales fuera de envíos y cajas de 6 en envíos.
- [x] Recopilar decisiones de catálogo y moneda: quetzales, productos individuales/cajas, precios confirmados y composición limitada de la mixta.
- [x] Recopilar que el POS será usado por la dueña y el usuario desde celular y web.
- [x] Confirmar pedidos mediante web/app como alcance de la primera versión propuesta, manteniendo pendientes su flujo detallado, pago y entrega.
- [ ] Conversar con el usuario y la dueña sobre operación actual, problemas y prioridades.
- [ ] Recopilar marca, fotografías y canales reales; cerrar, si corresponde, la etiqueta comercial Snicker/Snickers.
- [ ] Recopilar datos para el cálculo de costes del negocio; no inferir margen desde los precios de venta ni crear por ello un módulo software de costes.
- [ ] Resolver reglas de puntos y casos de devolución/canje después del cálculo de costes.
- [ ] Definir login normal, vinculación de identidades, permisos y dispositivos/SO.
- [ ] Definir cobertura, costo, proveedor y programación de envíos.
- [ ] Acordar MVP, presupuesto, restricciones y criterios de aceptación.

**Salida:** requisitos aprobados y preguntas bloqueantes resueltas. No empezar implementación por considerar este plan una autorización general.

### Fase 1 — Diseño de experiencia y solución

- [ ] Proponer flujos y pantallas de landing, cuentas, pedido web/app, compra en POS, consulta de puntos y canje.
- [ ] Validar los flujos con quienes operarán el negocio.
- [ ] Evaluar stack, despliegue y estrategia de app con sus costos y mantenimiento.
- [ ] Diseñar datos de productos compuestos, composiciones, pedidos, estados, permisos y contratos entre interfaces.
- [ ] Diseñar API reutilizable por web y futura app, con base de datos privada y acceso administrativo controlado.

**Salida:** diseño y decisiones técnicas aprobados, con backlog de tareas delimitadas.

### Fase 2 — Landing

- [ ] Implementar una sección vertical completa con contenido aprobado.
- [ ] Validar responsive, accesibilidad, enlaces y rendimiento.
- [ ] Preparar publicación únicamente con autorización.

**Salida:** landing verificada; no implica que POS, puntos o app ya estén listos.

### Fase 3 — Cuentas y pedidos web/app

- [ ] Implementar cuentas de cliente y login aprobado para pedir y participar en fidelización.
- [ ] Implementar pedidos con selección de composición mixta, estados separados de pedido/pago/entrega y pago al pedir o recibir.
- [ ] Mantener pedidos y ventas como entidades diferenciadas; no generar puntos por crear un pedido.
- [ ] Verificar permisos, reintentos e identificación sin integración bancaria o de WhatsApp/Instagram asumida.

**Salida:** pedido autenticado registrado y trazable hasta su estado acordado, sin confundirlo con venta o pago.

### Fase 4 — Base operativa y POS mínimo

- [ ] Implementar autenticación interna, catálogo extensible y venta persistida.
- [ ] Implementar productos individuales, compuestos y cajas actuales con composición seleccionable limitada.
- [ ] Implementar historial, precios/composición históricos, estados y reportes mínimos acordados.
- [ ] Verificar cálculos, permisos, reintentos y operación táctil en celular y web.

**Salida:** venta registrada y consultable de principio a fin, incluyendo producto y composición realmente vendidos.

### Fase 5 — Costes externos y fidelización integrada

- [ ] Recibir y aprobar el cálculo de costes del negocio, realizado fuera del producto; no implementar un módulo de costes sin encargo específico.
- [ ] Definir y aprobar reglas de puntos para unidades, productos compuestos y cajas, sin doble acreditación por contenedor y componentes.
- [ ] Implementar identificación del participante y libro de movimientos sobre las reglas aprobadas.
- [ ] Integrar acumulación, canje y reversos con ventas/pedidos según el momento aprobado.
- [ ] Implementar consulta del cliente y verificar concurrencia, idempotencia y escenarios negativos.

**Salida:** fidelización activa solo después de costes y reglas aprobados, con movimientos auditables.

### Fase 6 — App y Wallet

- [ ] Elegir modalidad móvil aprobada: nativa Android/iOS, multiplataforma o PWA.
- [ ] Implementar la modalidad aprobada sobre la API y reglas compartidas; verificar plataformas, tiendas y mantenimiento.
- [ ] Diseñar y, si se aprueba, integrar tarjetas de Google Wallet y Apple Wallet con identificador opaco/QR y saldo no autoritativo.
- [ ] Obtener cuentas de emisor, certificados y elegibilidad necesarios antes de publicación.

**Salida:** app y Wallet ejercitadas realmente solo si fueron aprobadas y preparadas para operación.

### Fase 7 — Piloto y operación

- [ ] Probar con la dueña y el usuario en condiciones representativas.
- [ ] Probar respaldos y restauración, control de acceso y recuperación ante fallos.
- [ ] Documentar uso, soporte y corrección de ventas, pedidos y puntos.
- [ ] Acordar indicadores y resolver incidencias antes del lanzamiento.

**Salida:** aprobación del negocio para operar con datos reales.

El orden es una propuesta basada en dependencias. Las prioridades y fechas quedan por acordar; no hay estimaciones comprometidas.

## 8. Seguridad, datos y límites de producción

- Recopilar solo los datos personales necesarios y acordar consentimiento, privacidad y retención.
- Proteger credenciales; no guardarlas en Git ni en este documento.
- Autorizar operaciones sensibles en servidor; auditar ajustes, anulaciones y canjes.
- Separar pruebas de producción. No usar datos reales de clientes en fixtures o demostraciones.
- Probar respaldos y restauración antes de depender del sistema para el negocio.
- No asumir que una captura de pantalla de pago demuestra un pago válido.
- Solo se dispone de cámara de celular; no hay terminal de tarjetas ni lector dedicado. El POS registra efectivo o transferencia, no procesa pagos bancarios.
- Escanear un QR identifica al participante, no paga ni genera puntos por sí solo. Validar saldo e identidad en backend antes de canjes.
- Prever consentimiento/HTTPS para cámara y alternativa manual; por defecto las confirmaciones de puntos y canjes requieren conexión.
- No realizar despliegues, compras de servicios, publicación en tiendas ni cambios sobre ventas reales sin autorización específica.

## 9. Protocolo para agentes delegados

1. Leer este documento, las instrucciones del repositorio y el encargo actual.
2. Inspeccionar el código y estado Git antes de editar; preservar cambios ajenos.
3. Confirmar objetivo, archivos permitidos, dependencias y aceptación del encargo.
4. Si una decisión pendiente afecta la tarea, reportarla; no inventar reglas, precios, servicios o requisitos.
5. Implementar solo el alcance autorizado, en unidades pequeñas y comprobables.
6. Para código, crear pruebas de comportamiento y ejecutar los checks reales del proyecto.
7. Reportar archivos cambiados, verificación ejecutada, resultados y bloqueos.
8. No hacer commit, push, despliegue ni refactorizaciones fuera de alcance salvo autorización.
9. Actualizar este documento solo con decisiones aprobadas; distinguir el avance verificado de lo planeado.

Modelo de encargo:

- Objetivo:
- Requisitos/decisiones aprobados:
- Alcance y archivos permitidos:
- Fuera de alcance:
- Dependencias:
- Criterios de aceptación:
- Pruebas y evidencia requeridas:
- Preguntas bloqueantes:

## 10. Próxima conversación

Priorizar estas preguntas antes de seleccionar tecnologías o activar fidelización:

1. ¿Cuál es el cálculo de costes aprobado y qué datos faltan para realizarlo?
2. ¿Cómo pasan los pedidos a venta, cuándo se confirma cada estado y cómo se verifica una transferencia?
3. ¿Qué cobertura, costo, proveedor y programación tienen los envíos?
4. ¿Cómo se resolverán nomenclatura comercial, inventario y disponibilidad de componentes?
5. ¿Qué login normal, vinculación de Google, recuperación y permisos se aprobarán?
6. ¿Qué requisitos de distribución, certificados y cuentas de emisor aplican a Wallet y a una futura app iOS?
7. ¿Qué modalidad móvil se elegirá: nativa, multiplataforma o PWA, y con qué presupuesto/mantenimiento?
8. ¿Qué inventario, promociones temporales, cupones, descuentos y profundidad de composición se requieren?
9. ¿Cuáles son prioridades, plazo y forma de colaboración?

## 11. Registro inicial y ubicación

- Confirmado: contexto del negocio y objetivos de landing, puntos, POS, web y app.
- Confirmado: operación actual registrada en un chat de WhatsApp con nombre de la persona, tipo y cantidad de brownies y medio de pago; pedidos recibidos por WhatsApp e Instagram.
- Confirmado: moneda quetzales (Q / GTQ) y catálogo: Simple Q10/Q60, M&M Q15/Q75, Snicker/Snickers Q17/Q80, Almendra Q15/Q70, Mixta Q85 por caja de 6.
- Confirmado: la mixta se compone de 2 Snicker + 3 M&M + 1 almendra o simple; precio Q85 en ambos casos y elección limitada, no libre.
- Confirmado: se venden brownies disponibles y preparados por encargo; hay envíos para personas en Guatemala, limitados en esa modalidad a cajas de 6, mixtas o de un tipo, con pago al pedir o al recibir; fuera de envíos hay individuales en la universidad.
- Confirmado: el POS lo usarán la dueña y el usuario desde celular y web; interfaz móvil responsive y web son necesidades confirmadas.
- Confirmado: pedidos mediante web/app y participación en puntos por esos canales forman parte del alcance de la primera versión propuesta; la emisión efectiva de puntos depende de reglas aprobadas.
- Confirmado: ofrecer login normal y opción “Continuar con Google”; el cliente inicia sesión para pedir por web/app y participar en puntos; ventas presenciales pueden registrarse sin cuenta.
- Confirmado: solo hay cámara de celular, efectivo y transferencia; no hay terminal de tarjetas ni lector dedicado.
- Confirmado: el catálogo debe admitir productos individuales y compuestos extensibles; contenerizar por separado frontend web, backend y base de datos.
- Propuesta a validar: diseño técnico de composición, composición con suma exacta de 6 para cajas actuales, accesos individuales para dos operadores y API compartida.
- Alcance solicitado en ideación, pendiente de fases y operación: tarjetas de fidelización en Google Wallet y Apple Wallet.
- Inspección inicial: únicamente README.md, con el título `# Bubus-bakery`; no había AGENTS.md, CLAUDE.md, plan previo, código ni manifiestos. Rama main siguiendo origin/main, árbol limpio antes de esta documentación.
- Pendiente: cálculo externo de costes y reglas de puntos, etiqueta comercial Snicker/Snickers si corresponde, cobertura/costo/proveedor/programación de envíos, estados de pedido/pago/entrega, comprobación de transferencias, mecanismo de login normal, vinculación/One Tap, permisos/dispositivos/SO, Wallet, modalidad móvil, inventario, promociones y forma de colaboración.
- Ubicación canónica prevista para esta entrega: `docs/PLAN_DE_ACCION.md`, referenciada por `AGENTS.md` en la raíz.
- Estado del producto: planificación; no se ha implementado la landing, puntos, POS ni app. La creación del plan no autoriza su implementación.

## Sources

[1] [Google Wallet — Loyalty cards](https://developers.google.com/wallet/retail/loyalty-cards)
[2] [Apple Wallet](https://developer.apple.com/wallet)
[3] [Google Identity Services — Overview](https://developers.google.com/identity/gsi/web/guides/overview)
