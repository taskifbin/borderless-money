-- xPay — PostgreSQL schema (production store)
-- The demo uses the in-memory/SQLite store (app/services/store.py); this is
-- the production schema with the incentive + RegTech columns explicit.

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS users (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  external_ref  VARCHAR(64) UNIQUE,           -- e.g. 'usr_uae_001'
  full_name     VARCHAR(120) NOT NULL,
  country       VARCHAR(2),                   -- 'AE', 'BD'
  kyc_tier      SMALLINT DEFAULT 0,
  created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS transactions (
  id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  external_ref              VARCHAR(64) UNIQUE,  -- e.g. 'tx-20261024-...'
  sender_id                 UUID REFERENCES users(id),
  amount_source             DECIMAL(15,2) NOT NULL,
  currency_source           VARCHAR(3) NOT NULL,
  fx_rate_applied           DECIMAL(15,6),
  fee_deducted              DECIMAL(10,2),
  govt_incentive_2_5_pct    DECIMAL(15,2),       -- 🌟 explicitly tracked
  true_net_receive_bdt      DECIMAL(15,2),       -- 🌟 the optimized metric
  route_selected            VARCHAR(80),         -- 'STELLAR_HYBRID', 'SWIFT', ...
  payout_method             VARCHAR(20),         -- 'BKASH', 'NAGAD', 'BANK'
  recipient_name            VARCHAR(120),
  recipient_handle          VARCHAR(80),
  stellar_hash              VARCHAR(64),
  iso_20022_msg_id          VARCHAR(16),
  status                    VARCHAR(24) NOT NULL DEFAULT 'PENDING',
      -- 'PENDING', 'COMPLIANCE_REVIEW', 'BLOCKED', 'COMPLETED', 'FAILED'
  breakdown                 JSONB,               -- full True Net Receive breakdown
  created_at                TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS regtech_logs (
  id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  transaction_id         UUID REFERENCES transactions(id),
  graph_nodes_evaluated  JSONB,                  -- ["sender:…", "recipient:…", …]
  gnn_risk_score         DECIMAL(5,4),           -- 0.0000 – 1.0000
  risk_band              VARCHAR(8),             -- 'LOW' | 'MEDIUM' | 'HIGH'
  ofac_match_status      VARCHAR(24),            -- 'CLEAR','FUZZY_MATCH_REVIEW','BLOCKED'
  ofac_best_match        JSONB,                  -- {"name": …, "similarity": …}
  engine                 VARCHAR(40),            -- 'pyg-gcn' | 'heuristic-stand-in'
  ai_explanation         TEXT,                   -- plain-language reasoning
  decision               VARCHAR(24),            -- final gate decision
  checked_at             TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_transactions_sender ON transactions(sender_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_regtech_tx ON regtech_logs(transaction_id);

-- Demo seed: the locked UAE -> bKash scenario sender
-- INSERT INTO users (external_ref, full_name, country, kyc_tier)
-- VALUES ('usr_uae_001', 'Mohammed Rafiq', 'AE', 2);
