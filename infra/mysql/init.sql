-- ============================================================
-- SMV Trades Database — Bootstrap Schema (v0 baseline)
-- Runs automatically on first MySQL container start.
-- All future changes go through Alembic migrations.
-- ============================================================

CREATE TABLE IF NOT EXISTS trades (
  id                BIGINT AUTO_INCREMENT PRIMARY KEY,
  user_id           VARCHAR(64)   NOT NULL,
  ticker            VARCHAR(10)   NOT NULL,
  action            ENUM('BUY','SELL') NOT NULL,
  order_type        ENUM('MARKET','LIMIT','STOP') DEFAULT 'MARKET',
  status            ENUM('PENDING','FILLED','CANCELLED','REJECTED') DEFAULT 'PENDING',
  quantity          DECIMAL(12,4) NOT NULL,
  target_price      DECIMAL(12,4),              -- limit/stop price (NULL for market)
  exec_price        DECIMAL(12,4),              -- actual fill price (NULL until filled)
  total_value       DECIMAL(16,4) GENERATED ALWAYS AS (quantity * exec_price) STORED,
  fees              DECIMAL(10,4) DEFAULT 0,    -- broker commissions
  paper_flag        BOOLEAN       NOT NULL DEFAULT TRUE,
  source_workflow   VARCHAR(32),                -- which agent workflow triggered this
  external_order_id VARCHAR(64),                -- IBKR order ID for reconciliation
  confidence        TINYINT,                    -- LLM confidence 0-100
  reasoning         TEXT,                       -- LLM reasoning snapshot
  created_at        TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
  updated_at        TIMESTAMP     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_user_ticker (user_id, ticker),
  INDEX idx_ticker_time (ticker, created_at DESC),
  INDEX idx_status (status),
  INDEX idx_paper (paper_flag),
  INDEX idx_external (external_order_id)
);

-- Summary view for the "previously traded" / "recurring" badge
-- Only counts FILLED orders for accurate trade history
CREATE OR REPLACE VIEW trade_history_summary AS
SELECT ticker,
       COUNT(*) AS total_trades,
       MIN(created_at) AS first_trade,
       MAX(created_at) AS last_trade,
       SUM(CASE WHEN action = 'BUY' THEN quantity ELSE 0 END) AS total_bought,
       SUM(CASE WHEN action = 'SELL' THEN quantity ELSE 0 END) AS total_sold
FROM trades
WHERE status = 'FILLED'
GROUP BY ticker;
