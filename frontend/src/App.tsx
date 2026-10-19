import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { fetchCatalog } from "./api";
import { getSession, login, logout, register } from "./auth";
import type { AuthUser } from "./auth";
import { ApiError, createOrder, createSale, listOperatorOrders, updateOrder } from "./orders";
import type { OrderLine, OrderRecord } from "./orders";
import type { Product } from "./types";

type Filter = "todos" | "individual" | "caja";
type PendingOperation<T> = { key: string; payload: T };
type OrderPayload = { items: OrderLine[]; contactReference: string; paymentIntent: "NO_DEFINIDO" | "AL_PEDIR" | "AL_RECIBIR" };
type SalePayload = { items: OrderLine[]; paymentMethod: "efectivo" | "transferencia"; customerName: string; customerEmail: string; reference: string; receivedConfirmed: boolean };

// Una operación con resultado desconocido se persiste para que recargar o desmontar nunca genere una clave nueva.
function pendingStorageKey(kind: "solicitud" | "venta", userEmail: string) { return `bubus:operacion-pendiente:${kind}:${userEmail}`; }
function readPending<T>(storageKey: string): PendingOperation<T> | null {
  try { const raw = localStorage.getItem(storageKey); return raw ? JSON.parse(raw) as PendingOperation<T> : null; } catch { return null; }
}
function writePending<T>(storageKey: string, operation: PendingOperation<T> | null) {
  try { if (operation) localStorage.setItem(storageKey, JSON.stringify(operation)); else localStorage.removeItem(storageKey); } catch { /* sin almacenamiento disponible, la operación vive solo en memoria */ }
}
// 4xx (salvo 408/429) significa que el servidor no creó la operación; red caída o 5xx dejan el resultado desconocido.
function isDefinitiveRejection(reason: unknown) { return reason instanceof ApiError && reason.status >= 400 && reason.status < 500 && reason.status !== 408 && reason.status !== 429; }

function formatPrice(cents: number) {
  return `Q${(cents / 100).toFixed(2)}`;
}

function BrownieArtwork({ variant }: { variant: string }) {
  const source = variant === "hero" ? "/assets/brownies-stack.jpg" : "/assets/brownie-single.jpg";
  return <div className={`brownie-art brownie-art--${variant}`} aria-hidden="true"><img src={source} alt="" /></div>;
}

function ProductCard({ product, selected, onSelect }: { product: Product; selected: boolean; onSelect: () => void }) {
  return <article className={`product-card ${selected ? "product-card--selected" : ""}`}>
    <div className="product-card__image"><BrownieArtwork variant={product.presentation === "caja6" ? "box" : product.slug} /><span className="product-tag">{product.presentation === "caja6" ? "Caja de 6" : "Individual"}</span></div>
    <div className="product-card__body">
      <p className="eyebrow">{product.kind === "composite" ? "Para compartir" : "Individual o caja"}</p>
      <h3>{product.name}</h3>
      <p>{product.description}</p>
      <div className="product-card__footer"><div className="price-stack"><strong>{formatPrice(product.priceCents)} <small>{product.presentation === "caja6" ? "caja de 6" : "individual"}</small></strong></div><button className="text-button" onClick={onSelect} aria-expanded={selected}>{selected ? "Ocultar composición" : "Ver composición"}</button></div>
      {selected && <ProductOptions product={product} />}
    </div>
  </article>;
}

function ProductOptions({ product }: { product: Product }) {
  return <div className="product-options" aria-label={`Opciones de ${product.name}`}>
    <span>Precio: {formatPrice(product.priceCents)} · {product.presentation === "caja6" ? "caja de 6" : "individual"}</span>
    {product.composition.length > 0 && <p>Incluye {product.composition.map((item) => `${item.quantity} ${item.product === "snickers" ? "Snickers" : item.product === "m-and-m" ? "M&M" : item.product}`).join(" + ")}.</p>}
    {product.optionGroups.map((group) => <fieldset key={group.code}><legend>{group.label}</legend>{group.options.map((option) => <label key={option.product}><input type="radio" name={group.code} value={option.product} defaultChecked={option.product === "almendra"} /> {option.product === "almendra" ? "Almendra" : "Simple"}</label>)}</fieldset>)}
    <small>Esta vista muestra opciones del catálogo; todavía no crea pedidos.</small>
  </div>;
}

function AuthPanel({ onClose, onUser }: { onClose: () => void; onUser: (user: AuthUser | null) => void }) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [user, setUser] = useState<AuthUser | null>(null);
  const [fields, setFields] = useState({ email: "", password: "", name: "" });
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => { getSession().then((current) => { setUser(current); onUser(current); }).catch(() => setMessage("No pudimos consultar tu sesión.")); }, [onUser]);
  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setMessage(null);
    try {
      const result = mode === "login" ? await login({ email: fields.email, password: fields.password }) : await register(fields);
      setUser(result.user); onUser(result.user);
    } catch (error) { setMessage(error instanceof Error ? error.message : "No pudimos completar la solicitud."); }
    finally { setBusy(false); }
  }
  async function signOut() { await logout(); setUser(null); onUser(null); }
  return <section className="auth-panel" aria-label="Acceso de clientes">
    <div className="auth-panel__heading"><div><p className="eyebrow">CUENTA DE CLIENTE</p><h2>{user ? `Hola, ${user.name}` : mode === "login" ? "Bienvenido de nuevo." : "Crea tu cuenta."}</h2></div><button className="close-button" onClick={onClose} aria-label="Cerrar acceso">×</button></div>
    {user ? <div className="auth-success" role="status"><p>Sesión activa para {user.email}.</p><p className="muted">Tu correo aún no está verificado. La verificación y recuperación estarán disponibles cuando exista un proveedor de correo.</p><button className="outline-button" onClick={signOut}>Cerrar sesión</button></div> : <>
      <div className="auth-tabs" role="tablist" aria-label="Tipo de acceso"><button className={mode === "login" ? "active" : ""} onClick={() => setMode("login")} role="tab" aria-selected={mode === "login"}>Iniciar sesión</button><button className={mode === "register" ? "active" : ""} onClick={() => setMode("register")} role="tab" aria-selected={mode === "register"}>Crear cuenta</button></div>
      <form onSubmit={submit} className="auth-form">
        {mode === "register" && <label>Nombre<input required value={fields.name} onChange={(event) => setFields({ ...fields, name: event.target.value })} autoComplete="name" /></label>}
        <label>Correo electrónico<input required type="email" value={fields.email} onChange={(event) => setFields({ ...fields, email: event.target.value })} autoComplete="email" /></label>
        <label>Contraseña<input required minLength={12} type="password" value={fields.password} onChange={(event) => setFields({ ...fields, password: event.target.value })} autoComplete={mode === "login" ? "current-password" : "new-password"} /></label>
        {message && <p className="state state--error" role="alert">{message}</p>}
        <button className="primary-button auth-submit" disabled={busy}>{busy ? "Procesando…" : mode === "login" ? "Iniciar sesión" : "Crear cuenta"}</button>
      </form>
      <button className="google-button" disabled title="Google no está configurado todavía">Continuar con Google <span>(próximamente)</span></button>
      <p className="muted">No enviaremos correos ni mostraremos recuperación hasta configurar un proveedor seguro.</p>
    </>}
  </section>;
}

function CustomerWorkspace({ products, userEmail }: { products: Product[]; userEmail: string }) {
  const storageKey = pendingStorageKey("solicitud", userEmail);
  const [restored] = useState(() => readPending<OrderPayload>(storageKey));
  const boxes = products.filter((product) => product.presentation === "caja6");
  const [slug, setSlug] = useState(boxes[0]?.slug ?? "");
  const [choice, setChoice] = useState("");
  const [quantity, setQuantity] = useState(1);
  const [contactReference, setContactReference] = useState("");
  const [paymentIntent, setPaymentIntent] = useState<"NO_DEFINIDO" | "AL_PEDIR" | "AL_RECIBIR">("NO_DEFINIDO");
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(restored ? "Hay una solicitud con resultado desconocido. Reinténtala o recupera su resultado antes de crear otra." : null);
  const [busy, setBusy] = useState(false);
  const [pending, setPending] = useState<PendingOperation<OrderPayload> | null>(restored);
  const [uncertain, setUncertain] = useState(Boolean(restored));
  // Refs síncronos: el estado de React no se actualiza entre dos submits del mismo turno.
  const inFlight = useRef(false);
  const pendingRef = useRef<typeof pending>(restored);
  const selected = boxes.find((product) => product.slug === slug);
  const optionGroup = selected?.optionGroups[0];
  const validChoice = optionGroup?.options.some((option) => option.product === choice) ? choice : optionGroup?.options[0]?.product ?? "";
  useEffect(() => {
    if (optionGroup && !optionGroup.options.some((option) => option.product === choice)) setChoice(optionGroup.options[0]?.product ?? "");
    if (!optionGroup) setChoice("");
  }, [slug, optionGroup, choice]);
  async function submit(event: FormEvent) {
    event.preventDefault(); if (inFlight.current) return; inFlight.current = true; setError(null); setResult(null); setBusy(true);
    const operation = pendingRef.current ?? { key: crypto.randomUUID(), payload: { items: [{ slug, quantity, options: optionGroup ? { [optionGroup.code]: validChoice } : {} }], contactReference, paymentIntent } };
    pendingRef.current = operation; writePending(storageKey, operation); setPending(operation);
    try { const order = await createOrder(operation.payload.items, operation.payload.contactReference, operation.payload.paymentIntent, operation.key); setResult(`Solicitud #${order.id} enviada para confirmación.`); release(); }
    catch (reason) {
      const message = reason instanceof Error ? reason.message : "No pudimos enviar la solicitud.";
      if (isDefinitiveRejection(reason)) { release(); setError(`${message} La solicitud no se creó; revisa los datos y envíala de nuevo.`); }
      else { setError(`${message} Conservamos los datos enviados. Reintenta o recupera el resultado antes de crear otra solicitud.`); setUncertain(true); }
    }
    finally { inFlight.current = false; setBusy(false); }
  }
  function release() { pendingRef.current = null; writePending(storageKey, null); setPending(null); setUncertain(false); }
  // Con una operación pendiente (en curso o incierta) el formulario muestra el payload enviado, no el borrador.
  const locked = Boolean(pending);
  const retryable = Boolean(pending && uncertain);
  const shownLine = pending?.payload.items[0];
  const shownGroup = shownLine ? boxes.find((product) => product.slug === shownLine.slug)?.optionGroups[0] : optionGroup;
  const shownChoice = shownLine ? (shownGroup && shownLine.options?.[shownGroup.code]) ?? "" : validChoice;
  return <section className="workspace customer-workspace" aria-label="Solicitar envío"><div><p className="eyebrow">SOLICITUD WEB</p><h2>Solicita una caja.</h2><p>La dueña confirmará cobertura, envío y total final. Esta solicitud no es un cobro ni crea puntos.</p></div><form className="workspace-form" onSubmit={submit}><label>Caja<select disabled={locked} value={shownLine?.slug ?? slug} onChange={(event) => setSlug(event.target.value)}>{boxes.map((product) => <option key={product.slug} value={product.slug}>{product.name} · {formatPrice(product.priceCents)}</option>)}</select></label>{shownGroup ? <label>Elección<select disabled={locked} value={shownChoice} onChange={(event) => setChoice(event.target.value)}>{shownGroup.options.map((option) => <option key={option.product} value={option.product}>{option.product === "almendra" ? "Almendra" : "Simple"}</option>)}</select></label> : null}<label>Cantidad<input disabled={locked} type="number" min="1" max="50" value={shownLine?.quantity ?? quantity} onChange={(event) => setQuantity(Number(event.target.value))} /></label><label>Referencia de contacto (opcional)<input disabled={locked} value={pending?.payload.contactReference ?? contactReference} maxLength={120} onChange={(event) => setContactReference(event.target.value)} placeholder="Ej. WhatsApp" /></label><label>Intención de pago (sin cobro)<select disabled={locked} value={pending?.payload.paymentIntent ?? paymentIntent} onChange={(event) => setPaymentIntent(event.target.value as "NO_DEFINIDO" | "AL_PEDIR" | "AL_RECIBIR")}><option value="NO_DEFINIDO">Aún no decidido</option><option value="AL_PEDIR">Al pedir</option><option value="AL_RECIBIR">Al recibir</option></select></label><button className="primary-button" type="submit" disabled={busy}>{busy ? "Enviando…" : retryable ? "Reintentar solicitud" : "Enviar solicitud"}</button>{retryable && <button type="button" className="outline-button" onClick={() => void submit(new Event("submit") as unknown as FormEvent)}>Recuperar resultado</button>}{result && <p className="state" role="status">{result}</p>}{error && <p className="state state--error" role="alert">{error}</p>}</form></section>;
}

function OperatorWorkspace({ products, userEmail }: { products: Product[]; userEmail: string }) {
  const storageKey = pendingStorageKey("venta", userEmail);
  const [restored] = useState(() => readPending<SalePayload>(storageKey));
  const [orders, setOrders] = useState<OrderRecord[]>([]);
  const [slug, setSlug] = useState(products[0]?.slug ?? "");
  const [quantity, setQuantity] = useState(1);
  const [method, setMethod] = useState<"efectivo" | "transferencia">("efectivo");
  const [customerName, setCustomerName] = useState("");
  const [customerEmail, setCustomerEmail] = useState("");
  const [reference, setReference] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [saleOptions, setSaleOptions] = useState<Record<string, string>>(() => Object.fromEntries((products[0]?.optionGroups ?? []).map((group) => [group.code, group.options[0]?.product ?? ""])));
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(restored ? "Hay una venta con resultado desconocido. Reinténtala o recupera su resultado antes de registrar otra." : null);
  const [busy, setBusy] = useState(false);
  const [pending, setPending] = useState<PendingOperation<SalePayload> | null>(restored);
  const [uncertain, setUncertain] = useState(Boolean(restored));
  const inFlight = useRef(false);
  const pendingRef = useRef<typeof pending>(restored);
  const selectedProduct = products.find((product) => product.slug === slug);

  async function refresh() { try { setOrders((await listOperatorOrders()).orders); } catch { setError("No pudimos cargar las solicitudes."); } }
  useEffect(() => { refresh(); }, []);
  function selectProduct(value: string) {
    const product = products.find((item) => item.slug === value);
    setSlug(value);
    setSaleOptions(Object.fromEntries((product?.optionGroups ?? []).map((group) => [group.code, group.options[0]?.product ?? ""])));
  }
  async function registerSale(event: FormEvent) {
    event.preventDefault(); if (inFlight.current) return; inFlight.current = true; setError(null); setMessage(null); setBusy(true);
    const operation = pendingRef.current ?? { key: crypto.randomUUID(), payload: { items: [{ slug, quantity, options: saleOptions }], paymentMethod: method, customerName, customerEmail, reference, receivedConfirmed: confirmed } };
    pendingRef.current = operation; writePending(storageKey, operation); setPending(operation);
    try {
      const sale = await createSale(operation.payload.items, operation.payload.paymentMethod, operation.payload.customerName, operation.payload.customerEmail, operation.payload.reference, operation.payload.receivedConfirmed, operation.key);
      setMessage(`Venta #${(sale as { id: number }).id} registrada.`); setConfirmed(false); release();
    } catch (reason) {
      const text = reason instanceof Error ? reason.message : "No pudimos registrar la venta.";
      if (isDefinitiveRejection(reason)) { release(); setError(`${text} La venta no se registró; revisa los datos y regístrala de nuevo.`); }
      else { setError(`${text} Conservamos los datos enviados. Reintenta o recupera el resultado antes de registrar otra venta.`); setUncertain(true); }
    } finally { inFlight.current = false; setBusy(false); }
  }
  function release() { pendingRef.current = null; writePending(storageKey, null); setPending(null); setUncertain(false); }
  const locked = Boolean(pending);
  const retryable = Boolean(pending && uncertain);
  const shown = pending?.payload;
  const shownLine = shown?.items[0];
  const shownProduct = shownLine ? products.find((product) => product.slug === shownLine.slug) : selectedProduct;
  const shownOptions = shownLine ? shownLine.options ?? {} : saleOptions;
  async function changeStatus(order: OrderRecord, status: string) { try { await updateOrder(order.id, status); await refresh(); } catch (reason) { setError(reason instanceof Error ? reason.message : "No pudimos actualizar la solicitud."); } }
  return <section className="workspace operator-workspace" aria-label="Panel de operador">
    <div><p className="eyebrow">OPERACIÓN INTERNA</p><h2>Registro de ventas.</h2><p>Confirma recepción del efectivo o transferencia. No se procesan tarjetas, devoluciones ni puntos.</p></div>
    <div className="operator-columns">
      <div><h3>Solicitudes web</h3>{orders.length === 0 ? <p className="muted">No hay solicitudes.</p> : orders.map((order) => <article className="operator-order" key={order.id}>
        <strong>#{order.id} · {order.status}</strong>
        {order.customer && <p><strong>{order.customer.name}</strong> · {order.customer.email}<br />Contacto: {order.customer.contactReference || "No indicado"}</p>}
        <p>Pago: {order.paymentIntent} · Estado pago: {order.paymentStatus} · Entrega: {order.deliveryStatus}</p>
        {order.items.map((item) => <p key={`${order.id}-${item.slug}`}>{item.quantity} × {item.name} · {formatPrice(item.unitPriceCents)}{item.composition?.length ? ` · ${item.composition.map((part) => `${part.quantity} ${part.product}`).join(" + ")}` : ""}{item.selectedOptions?.length ? ` · Elección: ${item.selectedOptions.map((option) => option.product).join(", ")}` : ""}</p>)}
        <span>Subtotal {formatPrice(order.subtotalCents)} · Envío {order.shippingAmountCents === null ? "pendiente" : formatPrice(order.shippingAmountCents)} · Total final {order.totalFinalCents === null ? "pendiente" : formatPrice(order.totalFinalCents)}</span>
        {order.status === "POR_CONFIRMAR" && <div><button className="text-button" onClick={() => changeStatus(order, "CONFIRMADA")}>Confirmar solicitud</button><button className="text-button danger" onClick={() => changeStatus(order, "CANCELADA")}>Cancelar</button></div>}
      </article>)}</div>
      <form className="workspace-form" onSubmit={registerSale}><h3>Venta presencial</h3>
        <label>Producto<select disabled={locked} value={shownLine?.slug ?? slug} onChange={(event) => selectProduct(event.target.value)}>{products.map((product) => <option key={product.slug} value={product.slug}>{product.name} · {formatPrice(product.priceCents)}</option>)}</select></label>
        {shownProduct?.optionGroups.map((group) => <fieldset disabled={locked} key={group.code}><legend>{group.label}</legend>{group.options.map((option) => <label key={option.product}><input type="radio" name={`sale-${group.code}`} checked={shownOptions[group.code] === option.product} onChange={() => setSaleOptions((current) => ({ ...current, [group.code]: option.product }))} /> {option.product}</label>)}</fieldset>)}
        <label>Cantidad<input disabled={locked} type="number" min="1" max="50" value={shownLine?.quantity ?? quantity} onChange={(event) => setQuantity(Number(event.target.value))} /></label><label>Cliente (opcional)<input disabled={locked} value={shown?.customerName ?? customerName} maxLength={120} onChange={(event) => setCustomerName(event.target.value)} /></label><label>Correo de miembro (opcional)<input disabled={locked} type="email" value={shown?.customerEmail ?? customerEmail} maxLength={320} onChange={(event) => setCustomerEmail(event.target.value)} /></label><label>Referencia interna (opcional)<input disabled={locked} value={shown?.reference ?? reference} maxLength={120} onChange={(event) => setReference(event.target.value)} /></label><label>Medio<select disabled={locked} value={shown?.paymentMethod ?? method} onChange={(event) => setMethod(event.target.value as "efectivo" | "transferencia")}><option value="efectivo">Efectivo</option><option value="transferencia">Transferencia</option></select></label><label className="check-label"><input disabled={locked} type="checkbox" checked={shown?.receivedConfirmed ?? confirmed} onChange={(event) => setConfirmed(event.target.checked)} /> Confirmo que recibí el pago</label><button className="primary-button" type="submit" disabled={busy}>{busy ? "Registrando…" : retryable ? "Reintentar venta" : "Registrar venta"}</button>{retryable && <button type="button" className="outline-button" onClick={() => void registerSale(new Event("submit") as unknown as FormEvent)}>Recuperar resultado</button>}{message && <p className="state" role="status">{message}</p>}{error && <p className="state state--error" role="alert">{error}</p>}
      </form>
    </div>
  </section>;
}

export default function App() {
  const [products, setProducts] = useState<Product[]>([]);
  const [filter, setFilter] = useState<Filter>("todos");
  const [selected, setSelected] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAuth, setShowAuth] = useState(false);
  const [authUser, setAuthUser] = useState<AuthUser | null>(null);

  useEffect(() => {
    fetchCatalog().then((data) => setProducts(data.products)).catch(() => setError("No pudimos cargar el catálogo. Intenta nuevamente más tarde.")).finally(() => setLoading(false));
  }, []);

  const filteredProducts = useMemo(() => products.filter((product) => filter === "todos" || (filter === "caja" ? product.presentation === "caja6" : product.presentation === "individual")), [filter, products]);

  return <div className="site-shell">
    <header className="topbar"><a className="brand" href="#inicio" aria-label="Bubu's bakery, inicio"><span>bubu's</span><small>BAKERY</small></a><nav aria-label="Navegación principal"><a href="#catalogo">Catálogo</a><a href="#historia">Nuestra historia</a><a href="#contacto">Visítanos</a></nav><div className="topbar__actions"><button className="outline-button" onClick={() => setShowAuth(true)}>Iniciar sesión</button><a className="primary-button" href="#catalogo">Ver brownies</a></div></header>
    {showAuth && <AuthPanel onClose={() => setShowAuth(false)} onUser={setAuthUser} />}
    {authUser?.role === "customer" && !loading && !error && <CustomerWorkspace key={authUser.email} products={products} userEmail={authUser.email} />}
    {authUser?.role === "operator" && !loading && !error && <OperatorWorkspace key={authUser.email} products={products} userEmail={authUser.email} />}
    <main>
      <section className="hero" id="inicio"><div className="hero__copy"><p className="eyebrow">BROWNIES HECHOS CON CARIÑO</p><h1>Un pequeño cuadrado.<br /><em>Mucha felicidad.</em></h1><p className="hero__lead">Brownies con centro suave, bordes intensos y una razón sencilla para hacer especial cualquier día.</p><a className="primary-button" href="#catalogo">Descubre el catálogo <span>↓</span></a></div><div className="hero__visual"><BrownieArtwork variant="hero" /><span className="stamp">100%<br />brownie</span><p>Hechos para compartir</p></div></section>
      <section className="catalog-section" id="catalogo"><div className="section-heading"><div><p className="eyebrow">ELIGE TU FAVORITO</p><h2>Encuentra tu brownie.</h2></div><p className="section-note">Catálogo base en quetzales.<br />Consulta las opciones de cada caja.</p></div><div className="filters" role="group" aria-label="Filtrar catálogo"><button className={filter === "todos" ? "filter-button active" : "filter-button"} onClick={() => setFilter("todos")}>Todos</button><button className={filter === "individual" ? "filter-button active" : "filter-button"} onClick={() => setFilter("individual")}>Brownies individuales</button><button className={filter === "caja" ? "filter-button active" : "filter-button"} onClick={() => setFilter("caja")}>Cajas de 6</button></div>{loading && <p className="state" role="status">Cargando catálogo…</p>}{error && <p className="state state--error" role="alert">{error}</p>}{!loading && !error && filteredProducts.length === 0 && <p className="state">No hay productos para este filtro.</p>}<div className="product-grid">{filteredProducts.map((product) => <ProductCard key={product.slug} product={product} selected={selected === product.slug} onSelect={() => setSelected(selected === product.slug ? null : product.slug)} />)}</div></section>
      <section className="story-section" id="historia"><div className="story-card"><p className="eyebrow">HECHOS EN PEQUEÑOS LOTES</p><h2>Un brownie sencillo.<br /><em>Mucho cuidado detrás.</em></h2><p>Esta entrega presenta el catálogo aprobado, solicitudes web y operación interna. Los módulos diferidos permanecen claramente fuera de alcance.</p><a className="text-button" href="#contacto">Conoce el alcance <span>→</span></a></div><div className="care-list"><div><strong>01</strong><h3>Recetas claras</h3><p>Ingredientes y combinaciones visibles en el catálogo.</p></div><div><strong>02</strong><h3>Precios en GTQ</h3><p>Importes exactos recibidos del negocio.</p></div><div><strong>03</strong><h3>Sin promesas inventadas</h3><p>La información pendiente queda fuera de esta entrega.</p></div></div></section>
    </main>
    <footer id="contacto"><div className="brand"><span>bubu's</span><small>BAKERY</small></div><p>Catálogo inicial · Guatemala</p><p>Solicitudes web y operación interna disponibles; cobertura y total final pendientes de confirmación.</p></footer>
  </div>;
}
