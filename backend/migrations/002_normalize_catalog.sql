ALTER TABLE products ADD COLUMN IF NOT EXISTS price_cents INTEGER;
ALTER TABLE products ADD COLUMN IF NOT EXISTS category VARCHAR(60);
ALTER TABLE products ADD COLUMN IF NOT EXISTS presentation VARCHAR(40);

-- Migración explícita de los cinco registros iniciales: solo completa campos
-- normalizados vacíos con el valor vigente; no reemplaza cambios existentes.
UPDATE products
SET price_cents = CASE WHEN slug = 'mixta' THEN box6_price_cents ELSE individual_price_cents END
WHERE price_cents IS NULL;
UPDATE products SET category = 'brownie' WHERE category IS NULL;
UPDATE products
SET presentation = CASE WHEN slug = 'mixta' THEN 'caja6' ELSE 'individual' END
WHERE presentation IS NULL;

INSERT INTO products (slug, name, kind, description, price_cents, category, presentation, active)
VALUES
  ('simple-caja-6', 'Caja de 6 Simple', 'composite', 'Seis brownies Simple.', 6000, 'brownie', 'caja6', TRUE),
  ('m-and-m-caja-6', 'Caja de 6 M&M', 'composite', 'Seis brownies M&M.', 7500, 'brownie', 'caja6', TRUE),
  ('snickers-caja-6', 'Caja de 6 Snickers', 'composite', 'Seis brownies Snickers.', 8000, 'brownie', 'caja6', TRUE),
  ('almendra-caja-6', 'Caja de 6 Almendra', 'composite', 'Seis brownies de almendra.', 7000, 'brownie', 'caja6', TRUE),
  ('mixta-caja-6', 'Caja mixta', 'composite', 'Seis brownies con una elección limitada.', 8500, 'brownie', 'caja6', TRUE)
ON CONFLICT (slug) DO NOTHING;

INSERT INTO product_components (parent_id, child_id, quantity)
SELECT parent.id, child.id, 6
FROM products parent JOIN products child ON child.slug = replace(parent.slug, '-caja-6', '')
WHERE parent.slug IN ('simple-caja-6', 'm-and-m-caja-6', 'snickers-caja-6', 'almendra-caja-6')
  AND NOT EXISTS (SELECT 1 FROM product_components existing WHERE existing.parent_id = parent.id);

INSERT INTO product_components (parent_id, child_id, quantity)
SELECT parent.id, child.id, wanted.quantity
FROM (VALUES ('mixta-caja-6', 'snickers', 2), ('mixta-caja-6', 'm-and-m', 3)) AS wanted(parent_slug, child_slug, quantity)
JOIN products parent ON parent.slug = wanted.parent_slug
JOIN products child ON child.slug = wanted.child_slug
WHERE NOT EXISTS (SELECT 1 FROM product_components existing WHERE existing.parent_id = parent.id);

INSERT INTO option_groups (product_id, code, label, min_selections, max_selections)
SELECT product.id, 'sixth-brownie', 'Elige el sexto brownie', 1, 1
FROM products product
WHERE product.slug = 'mixta-caja-6'
  AND NOT EXISTS (SELECT 1 FROM option_groups existing WHERE existing.product_id = product.id AND existing.code = 'sixth-brownie');

INSERT INTO options (group_id, product_id, quantity)
SELECT groups.id, product.id, 1
FROM option_groups groups
JOIN products parent ON parent.id = groups.product_id
JOIN products product ON product.slug IN ('almendra', 'simple')
WHERE parent.slug = 'mixta-caja-6'
  AND groups.code = 'sixth-brownie'
  AND NOT EXISTS (SELECT 1 FROM options existing WHERE existing.group_id = groups.id AND existing.product_id = product.id);
