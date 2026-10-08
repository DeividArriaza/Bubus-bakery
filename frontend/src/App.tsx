import { useEffect, useMemo, useState, type FormEvent } from "react";
import { fetchCatalog } from "./api";
import { getSession, login, logout, register } from "./auth";
import type { AuthUser } from "./auth";
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

function AuthPanel({ onClose }: { onClose: () => void }) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [user, setUser] = useState<AuthUser | null>(null);
  const [fields, setFields] = useState({ email: "", password: "", name: "" });
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => { getSession().then(setUser).catch(() => setMessage("No pudimos consultar tu sesión.")); }, []);
  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setMessage(null);
    try {
      const result = mode === "login" ? await login({ email: fields.email, password: fields.password }) : await register(fields);
      setUser(result.user);
    } catch (error) { setMessage(error instanceof Error ? error.message : "No pudimos completar la solicitud."); }
    finally { setBusy(false); }
  }
  async function signOut() { await logout(); setUser(null); }
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

export default function App() {
  const [products, setProducts] = useState<Product[]>([]);
  const [filter, setFilter] = useState<Filter>("todos");
  const [selected, setSelected] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAuth, setShowAuth] = useState(false);

  useEffect(() => {
    fetchCatalog().then((data) => setProducts(data.products)).catch(() => setError("No pudimos cargar el catálogo. Intenta nuevamente más tarde.")).finally(() => setLoading(false));
  }, []);

  const filteredProducts = useMemo(() => products.filter((product) => filter === "todos" || (filter === "caja" ? product.presentation === "caja6" : product.presentation === "individual")), [filter, products]);

  return <div className="site-shell">
    <header className="topbar"><a className="brand" href="#inicio" aria-label="Bubu's bakery, inicio"><span>bubu's</span><small>BAKERY</small></a><nav aria-label="Navegación principal"><a href="#catalogo">Catálogo</a><a href="#historia">Nuestra historia</a><a href="#contacto">Visítanos</a></nav><div className="topbar__actions"><button className="outline-button" onClick={() => setShowAuth(true)}>Iniciar sesión</button><a className="primary-button" href="#catalogo">Ver brownies</a></div></header>
    {showAuth && <AuthPanel onClose={() => setShowAuth(false)} />}
    <main>
      <section className="hero" id="inicio"><div className="hero__copy"><p className="eyebrow">BROWNIES HECHOS CON CARIÑO</p><h1>Un pequeño cuadrado.<br /><em>Mucha felicidad.</em></h1><p className="hero__lead">Brownies con centro suave, bordes intensos y una razón sencilla para hacer especial cualquier día.</p><a className="primary-button" href="#catalogo">Descubre el catálogo <span>↓</span></a></div><div className="hero__visual"><BrownieArtwork variant="hero" /><span className="stamp">100%<br />brownie</span><p>Hechos para compartir</p></div></section>
      <section className="catalog-section" id="catalogo"><div className="section-heading"><div><p className="eyebrow">ELIGE TU FAVORITO</p><h2>Encuentra tu brownie.</h2></div><p className="section-note">Catálogo base en quetzales.<br />Consulta las opciones de cada caja.</p></div><div className="filters" role="group" aria-label="Filtrar catálogo"><button className={filter === "todos" ? "filter-button active" : "filter-button"} onClick={() => setFilter("todos")}>Todos</button><button className={filter === "individual" ? "filter-button active" : "filter-button"} onClick={() => setFilter("individual")}>Brownies individuales</button><button className={filter === "caja" ? "filter-button active" : "filter-button"} onClick={() => setFilter("caja")}>Cajas de 6</button></div>{loading && <p className="state" role="status">Cargando catálogo…</p>}{error && <p className="state state--error" role="alert">{error}</p>}{!loading && !error && filteredProducts.length === 0 && <p className="state">No hay productos para este filtro.</p>}<div className="product-grid">{filteredProducts.map((product) => <ProductCard key={product.slug} product={product} selected={selected === product.slug} onSelect={() => setSelected(selected === product.slug ? null : product.slug)} />)}</div></section>
      <section className="story-section" id="historia"><div className="story-card"><p className="eyebrow">HECHOS EN PEQUEÑOS LOTES</p><h2>Un brownie sencillo.<br /><em>Mucho cuidado detrás.</em></h2><p>Esta primera entrega presenta el catálogo aprobado y sus opciones reales. Los pedidos y la operación interna se incorporarán en fases posteriores.</p><a className="text-button" href="#contacto">Conoce el alcance <span>→</span></a></div><div className="care-list"><div><strong>01</strong><h3>Recetas claras</h3><p>Ingredientes y combinaciones visibles en el catálogo.</p></div><div><strong>02</strong><h3>Precios en GTQ</h3><p>Importes exactos recibidos del negocio.</p></div><div><strong>03</strong><h3>Sin promesas inventadas</h3><p>La información pendiente queda fuera de esta entrega.</p></div></div></section>
    </main>
    <footer id="contacto"><div className="brand"><span>bubu's</span><small>BAKERY</small></div><p>Catálogo inicial · Guatemala</p><p>Pedidos y contacto: próximos módulos</p></footer>
  </div>;
}
