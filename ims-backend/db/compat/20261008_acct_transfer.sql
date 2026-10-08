-- ACCT-002 账号流转（切片 #60）
CREATE TABLE IF NOT EXISTS ims_acct_transfer (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  transfer_no VARCHAR(32) NOT NULL,
  account_id BIGINT NOT NULL,
  account_no VARCHAR(64) NOT NULL DEFAULT '',
  from_user_id BIGINT NOT NULL,
  to_user_id BIGINT NOT NULL DEFAULT 0,
  transfer_type VARCHAR(16) NOT NULL DEFAULT 'TRANSFER',
  reason_type VARCHAR(32) NOT NULL DEFAULT '',
  remark VARCHAR(512) NOT NULL DEFAULT '',
  status VARCHAR(32) NOT NULL DEFAULT 'PENDING_CONFIRM',
  effective_at DATETIME NULL,
  tenant_id BIGINT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_acct_transfer_no (transfer_no),
  KEY idx_acct_transfer_account (account_id),
  KEY idx_acct_transfer_from (from_user_id),
  KEY idx_acct_transfer_to (to_user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
