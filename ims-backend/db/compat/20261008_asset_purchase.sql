-- ASSET 采购批量入台账（#68 · E2E-S5-01）
-- 已有 ims 库：本文件，或重启 API（init_db 会补 purchase_batch_no 并 create_all 批次表）

ALTER TABLE ims_asset_ledger ADD COLUMN purchase_batch_no VARCHAR(32) NOT NULL DEFAULT '';
CREATE INDEX idx_asset_ledger_purchase_batch ON ims_asset_ledger (purchase_batch_no);

CREATE TABLE IF NOT EXISTS ims_asset_purchase_batch (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  batch_no VARCHAR(32) NOT NULL,
  file_name VARCHAR(128) NOT NULL DEFAULT '',
  total_count INT NOT NULL DEFAULT 0,
  success_count INT NOT NULL DEFAULT 0,
  fail_count INT NOT NULL DEFAULT 0,
  partial INT NOT NULL DEFAULT 0,
  error_detail TEXT NULL,
  creator BIGINT NOT NULL DEFAULT 0,
  deleted INT NOT NULL DEFAULT 0,
  tenant_id BIGINT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_asset_purchase_batch (batch_no),
  KEY idx_asset_purchase_batch_tenant (tenant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
