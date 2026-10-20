-- Conserva el registro histórico de la primera demo, pero evita dos productos
-- vendibles para la misma caja tras normalizar su slug/presentación.
UPDATE products
SET active = FALSE
WHERE slug = 'mixta'
  AND EXISTS (SELECT 1 FROM products canonical WHERE canonical.slug = 'mixta-caja-6');
