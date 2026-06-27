CREATE TABLE IF NOT EXISTS customers (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  email TEXT NOT NULL,
  tier TEXT NOT NULL CHECK (tier IN ('standard','gold','platinum')),
  region TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS inventory (
  sku TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  quantity INTEGER NOT NULL CHECK (quantity >= 0),
  reorder_level INTEGER NOT NULL CHECK (reorder_level >= 0),
  unit_price NUMERIC(12,2) NOT NULL CHECK (unit_price > 0),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sales (
  id TEXT PRIMARY KEY,
  customer_id TEXT NOT NULL REFERENCES customers(id),
  sku TEXT NOT NULL REFERENCES inventory(sku),
  quantity INTEGER NOT NULL CHECK (quantity > 0),
  total NUMERIC(12,2) NOT NULL CHECK (total > 0),
  status TEXT NOT NULL CHECK (status IN ('confirmed','cancelled')),
  idempotency_key TEXT NOT NULL UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS support_tickets (
  id TEXT PRIMARY KEY,
  customer_id TEXT NOT NULL REFERENCES customers(id),
  subject TEXT NOT NULL,
  description TEXT NOT NULL,
  priority TEXT NOT NULL CHECK (priority IN ('low','normal','high','critical')),
  status TEXT NOT NULL CHECK (status IN ('open','in_progress','resolved')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sales_customer_created ON sales(customer_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tickets_customer_status ON support_tickets(customer_id, status);

INSERT INTO customers (id,name,email,tier,region) VALUES
  ('cus_1001','Ana Silva','ana.silva@example.com','gold','BR-SP'),
  ('cus_1002','Carlos Lima','carlos.lima@example.com','standard','BR-RJ')
ON CONFLICT (id) DO NOTHING;

INSERT INTO inventory (sku,name,quantity,reorder_level,unit_price) VALUES
  ('SKU-RED-01','Red Running Shoe',50,10,129.90),
  ('SKU-BAG-02','Urban Backpack',25,5,89.50)
ON CONFLICT (sku) DO NOTHING;
