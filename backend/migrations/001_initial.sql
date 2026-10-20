CREATE TABLE IF NOT EXISTS products (
  id BIGSERIAL PRIMARY KEY,
  slug VARCHAR(80) NOT NULL UNIQUE,
  name VARCHAR(120) NOT NULL,
  kind VARCHAR(20) NOT NULL,
  description VARCHAR(500) NOT NULL,
  individual_price_cents INTEGER,
  box6_price_cents INTEGER,
  active BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE TABLE IF NOT EXISTS product_components (
  id BIGSERIAL PRIMARY KEY,
  parent_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  child_id BIGINT NOT NULL REFERENCES products(id),
  quantity INTEGER NOT NULL CHECK (quantity > 0),
  UNIQUE (parent_id, child_id)
);
CREATE TABLE IF NOT EXISTS option_groups (
  id BIGSERIAL PRIMARY KEY,
  product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  code VARCHAR(80) NOT NULL,
  label VARCHAR(160) NOT NULL,
  min_selections INTEGER NOT NULL,
  max_selections INTEGER NOT NULL,
  UNIQUE (product_id, code)
);
CREATE TABLE IF NOT EXISTS options (
  id BIGSERIAL PRIMARY KEY,
  group_id BIGINT NOT NULL REFERENCES option_groups(id) ON DELETE CASCADE,
  product_id BIGINT NOT NULL REFERENCES products(id),
  quantity INTEGER NOT NULL CHECK (quantity > 0),
  UNIQUE (group_id, product_id)
);
