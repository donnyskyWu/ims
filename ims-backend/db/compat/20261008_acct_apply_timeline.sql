-- ACCT-001 领用申请 + 时间线（切片 #47）
CREATE TABLE IF NOT EXISTS ims_acct_apply (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  apply_no VARCHAR(32) NOT NULL,
  account_id BIGINT NOT NULL,
  account_no VARCHAR(64) NOT NULL DEFAULT '',
  platform VARCHAR(32) NOT NULL DEFAULT '',
  applicant_user_id BIGINT NOT NULL,
  purpose VARCHAR(256) NOT NULL DEFAULT '',
  plan_start VARCHAR(32) NOT NULL DEFAULT '',
  plan_end VARCHAR(32) NOT NULL DEFAULT '',
  apply_status VARCHAR(32) NOT NULL DEFAULT 'PENDING_APPROVAL',
  handover_json TEXT,
  tenant_id BIGINT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_apply_no (apply_no),
  KEY idx_acct_apply_account (account_id),
  KEY idx_acct_apply_applicant (applicant_user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS ims_acct_timeline_event (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  account_id BIGINT NOT NULL,
  event_type VARCHAR(32) NOT NULL,
  ref_no VARCHAR(32) NOT NULL DEFAULT '',
  ref_id BIGINT NOT NULL DEFAULT 0,
  operator_user_id BIGINT NOT NULL DEFAULT 0,
  snapshot_summary VARCHAR(512) NOT NULL DEFAULT '',
  remark VARCHAR(256) NOT NULL DEFAULT '',
  tenant_id BIGINT NOT NULL DEFAULT 0,
  event_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_acct_tl_account (account_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
