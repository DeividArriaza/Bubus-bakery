ALTER TABLE orders ADD COLUMN IF NOT EXISTS idempotency_intent_json TEXT;
ALTER TABLE sales ADD COLUMN IF NOT EXISTS idempotency_intent_json TEXT;
