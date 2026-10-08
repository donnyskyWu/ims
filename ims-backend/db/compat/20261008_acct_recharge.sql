-- ACCT-004 冲话费登记（切片 #58）
CREATE TABLE IF NOT EXISTS ims_acct_recharge (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  account_id BIGINT NOT NULL,
  account_no VARCHAR(64) NOT NULL DEFAULT '',
  amount DOUBLE NOT NULL DEFAULT 0,
  channel VARCHAR(64) NOT NULL DEFAULT '',
  voucher_url VARCHAR(512) NOT NULL DEFAULT '',
  recharge_date VARCHAR(16) NOT NULL DEFAULT '',
  verify_status VARCHAR(16) NOT NULL DEFAULT 'UNVERIFIED',
  verify_diff DOUBLE NULL,
  operator_user_id BIGINT NOT NULL DEFAULT 0,
  client_token VARCHAR(64) NOT NULL,
  remark VARCHAR(256) NOT NULL DEFAULT '',
  tenant_id BIGINT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_acct_recharge_token (client_token),
  KEY idx_acct_recharge_account (account_id),
  KEY idx_acct_recharge_operator (operator_user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
