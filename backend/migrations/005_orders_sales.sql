CREATE TABLE IF NOT EXISTS orders (
  id BIGSERIAL PRIMARY KEY,
  customer_id BIGINT NOT NULL REFERENCES users(id),
  fulfillment VARCHAR(20) NOT NULL CHECK (fulfillment = 'envio'),
  status VARCHAR(30) NOT NULL DEFAULT 'POR_CONFIRMAR',
  payment_status VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE',
  delivery_status VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE',
  subtotal_cents INTEGER NOT NULL CHECK (subtotal_cents >= 0),
  shipping_amount_cents INTEGER,
  total_final_cents INTEGER,
  contact_reference VARCHAR(120),
  idempotency_key VARCHAR(100) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (customer_id, idempotency_key)
);

CREATE TABLE IF NOT EXISTS order_items (
  id BIGSERIAL PRIMARY KEY,
  order_id BIGINT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  product_id BIGINT NOT NULL REFERENCES products(id),
  product_slug VARCHAR(80) NOT NULL,
  product_name VARCHAR(120) NOT NULL,
  unit_price_cents INTEGER NOT NULL CHECK (unit_price_cents >= 0),
  quantity INTEGER NOT NULL CHECK (quantity > 0),
  snapshot_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sales (
  id BIGSERIAL PRIMARY KEY,
  actor_id BIGINT NOT NULL REFERENCES users(id),
  customer_id BIGINT REFERENCES users(id),
  payment_method VARCHAR(20) NOT NULL CHECK (payment_method IN ('EFECTIVO', 'TRANSFERENCIA')),
  payment_status VARCHAR(20) NOT NULL DEFAULT 'RECIBIDO',
  subtotal_cents INTEGER NOT NULL CHECK (subtotal_cents >= 0),
  customer_name VARCHAR(120),
  idempotency_key VARCHAR(100) NOT NULL,
  received_confirmed_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (actor_id, idempotency_key)
);

CREATE TABLE IF NOT EXISTS sale_items (
  id BIGSERIAL PRIMARY KEY,
  sale_id BIGINT NOT NULL REFERENCES sales(id) ON DELETE CASCADE,
  product_id BIGINT NOT NULL REFERENCES products(id),
  product_slug VARCHAR(80) NOT NULL,
  product_name VARCHAR(120) NOT NULL,
  unit_price_cents INTEGER NOT NULL CHECK (unit_price_cents >= 0),
  quantity INTEGER NOT NULL CHECK (quantity > 0),
  snapshot_json TEXT NOT NULL
);
