import { useEffect, useMemo, useState, type FormEvent } from "react";
import { fetchCatalog } from "./api";
import { getSession, login, logout, register } from "./auth";
import type { AuthUser } from "./auth";
import { createOrder, createSale, listOperatorOrders, updateOrder } from "./orders";
import type { OrderLine, OrderRecord } from "./orders";
import type { Product } from "./types";

type Filter = "todos" | "individual" | "caja";

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

function CustomerWorkspace({ products }: { products: Product[] }) {
  const boxes = products.filter((product) => product.presentation === "caja6");
  const [slug, setSlug] = useState(boxes[0]?.slug ?? "");
  const [choice, setChoice] = useState("almendra");
  const [quantity, setQuantity] = useState(1);
  const [contactReference, setContactReference] = useState("");
  const [paymentIntent, setPaymentIntent] = useState<"NO_DEFINIDO" | "AL_PEDIR" | "AL_RECIBIR">("NO_DEFINIDO");
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const selected = boxes.find((product) => product.slug === slug);
  async function submit(event: FormEvent) {
    event.preventDefault(); setError(null); setResult(null);
    const options = selected?.optionGroups.length ? { [selected.optionGroups[0].code]: choice } : {};
    try { const order = await createOrder([{ slug, quantity, options }], contactReference, paymentIntent); setResult(`Solicitud #${order.id} enviada para confirmación.`); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "No pudimos enviar la solicitud."); }
  }
  return <section className="workspace customer-workspace" aria-label="Solicitar envío"><div><p className="eyebrow">SOLICITUD WEB</p><h2>Solicita una caja.</h2><p>La dueña confirmará cobertura, envío y total final. Esta solicitud no es un cobro ni crea puntos.</p></div><form className="workspace-form" onSubmit={submit}><label>Caja<select value={slug} onChange={(event) => setSlug(event.target.value)}>{boxes.map((product) => <option key={product.slug} value={product.slug}>{product.name} · {formatPrice(product.priceCents)}</option>)}</select></label>{selected?.optionGroups.length ? <label>Elección<select value={choice} onChange={(event) => setChoice(event.target.value)}>{selected.optionGroups[0].options.map((option) => <option key={option.product} value={option.product}>{option.product === "almendra" ? "Almendra" : "Simple"}</option>)}</select></label> : null}<label>Cantidad<input type="number" min="1" max="50" value={quantity} onChange={(event) => setQuantity(Number(event.target.value))} /></label><label>Referencia de contacto (opcional)<input value={contactReference} maxLength={120} onChange={(event) => setContactReference(event.target.value)} placeholder="Ej. WhatsApp" /></label><label>Intención de pago (sin cobro)<select value={paymentIntent} onChange={(event) => setPaymentIntent(event.target.value as "NO_DEFINIDO" | "AL_PEDIR" | "AL_RECIBIR")}><option value="NO_DEFINIDO">Aún no decidido</option><option value="AL_PEDIR">Al pedir</option><option value="AL_RECIBIR">Al recibir</option></select></label><button className="primary-button" type="submit">Enviar solicitud</button>{result && <p className="state" role="status">{result}</p>}{error && <p className="state state--error" role="alert">{error}</p>}</form></section>;
}

function OperatorWorkspace({ products }: { products: Product[] }) {
  const [orders, setOrders] = useState<OrderRecord[]>([]);
  const [slug, setSlug] = useState(products[0]?.slug ?? "");
  const [quantity, setQuantity] = useState(1);
  const [method, setMethod] = useState<"efectivo" | "transferencia">("efectivo");
  const [customerName, setCustomerName] = useState("");
  const [customerEmail, setCustomerEmail] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  async function refresh() { try { setOrders((await listOperatorOrders()).orders); } catch { setError("No pudimos cargar las solicitudes."); } }
  useEffect(() => { refresh(); }, []);
  async function registerSale(event: FormEvent) { event.preventDefault(); setError(null); setMessage(null); try { const sale = await createSale([{ slug, quantity }], method, customerName, customerEmail, confirmed); setMessage(`Venta #${(sale as { id: number }).id} registrada.`); setConfirmed(false); } catch (reason) { setError(reason instanceof Error ? reason.message : "No pudimos registrar la venta."); } }
  async function changeStatus(order: OrderRecord, status: string) { try { await updateOrder(order.id, status); await refresh(); } catch (reason) { setError(reason instanceof Error ? reason.message : "No pudimos actualizar la solicitud."); } }
  return <section className="workspace operator-workspace" aria-label="Panel de operador"><div><p className="eyebrow">OPERACIÓN INTERNA</p><h2>Registro de ventas.</h2><p>Confirma recepción del efectivo o transferencia. No se procesan tarjetas, devoluciones ni puntos.</p></div><div className="operator-columns"><div><h3>Solicitudes web</h3>{orders.length === 0 ? <p className="muted">No hay solicitudes.</p> : orders.map((order) => <article className="operator-order" key={order.id}><strong>#{order.id} · {order.status}</strong><span>{formatPrice(order.subtotalCents)} · total final pendiente</span>{order.status === "POR_CONFIRMAR" && <div><button className="text-button" onClick={() => changeStatus(order, "CONFIRMADA")}>Confirmar solicitud</button><button className="text-button danger" onClick={() => changeStatus(order, "CANCELADA")}>Cancelar</button></div>}</article>)}</div><form className="workspace-form" onSubmit={registerSale}><h3>Venta presencial</h3><label>Producto<select value={slug} onChange={(event) => setSlug(event.target.value)}>{products.map((product) => <option key={product.slug} value={product.slug}>{product.name} · {formatPrice(product.priceCents)}</option>)}</select></label><label>Cantidad<input type="number" min="1" max="50" value={quantity} onChange={(event) => setQuantity(Number(event.target.value))} /></label><label>Cliente (opcional)<input value={customerName} maxLength={120} onChange={(event) => setCustomerName(event.target.value)} /></label><label>Correo de miembro (opcional)<input type="email" value={customerEmail} onChange={(event) => setCustomerEmail(event.target.value)} /></label><label>Medio<select value={method} onChange={(event) => setMethod(event.target.value as "efectivo" | "transferencia")}><option value="efectivo">Efectivo</option><option value="transferencia">Transferencia</option></select></label><label className="check-label"><input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} /> Confirmo que recibí el pago</label><button className="primary-button" type="submit">Registrar venta</button>{message && <p className="state" role="status">{message}</p>}{error && <p className="state state--error" role="alert">{error}</p>}</form></div></section>;
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
    {authUser?.role === "customer" && !loading && !error && <CustomerWorkspace products={products} />}
    {authUser?.role === "operator" && !loading && !error && <OperatorWorkspace products={products} />}
    <main>
      <section className="hero" id="inicio"><div className="hero__copy"><p className="eyebrow">BROWNIES HECHOS CON CARIÑO</p><h1>Un pequeño cuadrado.<br /><em>Mucha felicidad.</em></h1><p className="hero__lead">Brownies con centro suave, bordes intensos y una razón sencilla para hacer especial cualquier día.</p><a className="primary-button" href="#catalogo">Descubre el catálogo <span>↓</span></a></div><div className="hero__visual"><BrownieArtwork variant="hero" /><span className="stamp">100%<br />brownie</span><p>Hechos para compartir</p></div></section>
      <section className="catalog-section" id="catalogo"><div className="section-heading"><div><p className="eyebrow">ELIGE TU FAVORITO</p><h2>Encuentra tu brownie.</h2></div><p className="section-note">Catálogo base en quetzales.<br />Consulta las opciones de cada caja.</p></div><div className="filters" role="group" aria-label="Filtrar catálogo"><button className={filter === "todos" ? "filter-button active" : "filter-button"} onClick={() => setFilter("todos")}>Todos</button><button className={filter === "individual" ? "filter-button active" : "filter-button"} onClick={() => setFilter("individual")}>Brownies individuales</button><button className={filter === "caja" ? "filter-button active" : "filter-button"} onClick={() => setFilter("caja")}>Cajas de 6</button></div>{loading && <p className="state" role="status">Cargando catálogo…</p>}{error && <p className="state state--error" role="alert">{error}</p>}{!loading && !error && filteredProducts.length === 0 && <p className="state">No hay productos para este filtro.</p>}<div className="product-grid">{filteredProducts.map((product) => <ProductCard key={product.slug} product={product} selected={selected === product.slug} onSelect={() => setSelected(selected === product.slug ? null : product.slug)} />)}</div></section>
      <section className="story-section" id="historia"><div className="story-card"><p className="eyebrow">HECHOS EN PEQUEÑOS LOTES</p><h2>Un brownie sencillo.<br /><em>Mucho cuidado detrás.</em></h2><p>Esta primera entrega presenta el catálogo aprobado y sus opciones reales. Los pedidos y la operación interna se incorporarán en fases posteriores.</p><a className="text-button" href="#contacto">Conoce el alcance <span>→</span></a></div><div className="care-list"><div><strong>01</strong><h3>Recetas claras</h3><p>Ingredientes y combinaciones visibles en el catálogo.</p></div><div><strong>02</strong><h3>Precios en GTQ</h3><p>Importes exactos recibidos del negocio.</p></div><div><strong>03</strong><h3>Sin promesas inventadas</h3><p>La información pendiente queda fuera de esta entrega.</p></div></div></section>
    </main>
    <footer id="contacto"><div className="brand"><span>bubu's</span><small>BAKERY</small></div><p>Catálogo inicial · Guatemala</p><p>Pedidos y contacto: próximos módulos</p></footer>
  </div>;
}
