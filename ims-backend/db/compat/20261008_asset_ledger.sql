-- ASSET 台账生命周期（#63 · E2E-S5-02）
CREATE TABLE IF NOT EXISTS ims_asset_ledger (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  asset_code VARCHAR(64) NOT NULL DEFAULT '',
  asset_name VARCHAR(128) NOT NULL DEFAULT '',
  asset_type VARCHAR(32) NOT NULL DEFAULT 'OFFICE',
  spec VARCHAR(128) NOT NULL DEFAULT '',
  status VARCHAR(32) NOT NULL DEFAULT 'PENDING_REVIEW',
  owner_user_id BIGINT NULL,
  purchase_date VARCHAR(10) NOT NULL DEFAULT '',
  used_at DATETIME NULL,
  subject_id BIGINT NOT NULL DEFAULT 0,
  creator BIGINT NOT NULL DEFAULT 0,
  updater BIGINT NOT NULL DEFAULT 0,
  deleted INT NOT NULL DEFAULT 0,
  tenant_id BIGINT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_asset_ledger_code (tenant_id, asset_code),
  KEY idx_asset_ledger_type (asset_type),
  KEY idx_asset_ledger_status (status),
  KEY idx_asset_ledger_owner (owner_user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS ims_asset_lifecycle (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  asset_id BIGINT NOT NULL,
  event_type VARCHAR(16) NOT NULL DEFAULT 'REGISTER',
  from_status VARCHAR(32) NOT NULL DEFAULT '',
  to_status VARCHAR(32) NOT NULL DEFAULT '',
  actor_user_id BIGINT NOT NULL DEFAULT 0,
  owner_user_id BIGINT NULL,
  remark VARCHAR(256) NOT NULL DEFAULT '',
  deleted INT NOT NULL DEFAULT 0,
  tenant_id BIGINT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_asset_lifecycle_asset (asset_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
