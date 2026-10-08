-- ACCT-004 月度账实核对（切片 #64 · 1026）
CREATE TABLE IF NOT EXISTS ims_acct_recharge_verify (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  verify_no VARCHAR(32) NOT NULL,
  month VARCHAR(7) NOT NULL,
  account_id BIGINT NOT NULL DEFAULT 0,
  account_no VARCHAR(64) NOT NULL DEFAULT '',
  total_recharge DOUBLE NOT NULL DEFAULT 0,
  platform_consumed DOUBLE NOT NULL DEFAULT 0,
  diff_amount DOUBLE NOT NULL DEFAULT 0,
  diff_rate DOUBLE NOT NULL DEFAULT 0,
  status VARCHAR(16) NOT NULL DEFAULT 'MATCHED',
  work_order_id BIGINT NOT NULL DEFAULT 0,
  operator_user_id BIGINT NOT NULL DEFAULT 0,
  tenant_id BIGINT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_acct_recharge_verify_no (verify_no),
  KEY idx_acct_recharge_verify_month (month),
  KEY idx_acct_recharge_verify_account (account_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
