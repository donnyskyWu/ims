-- ASSET 穿透层级与查询审计（#65 · E2E-S5-03/04）
CREATE TABLE IF NOT EXISTS ims_asset_hierarchy (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  asset_id BIGINT NOT NULL,
  parent_asset_id BIGINT NULL,
  realname_id BIGINT NOT NULL DEFAULT 0,
  level INT NOT NULL DEFAULT 1,
  path VARCHAR(512) NOT NULL DEFAULT '',
  deleted INT NOT NULL DEFAULT 0,
  tenant_id BIGINT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_asset_hierarchy_asset (tenant_id, asset_id),
  KEY idx_asset_hierarchy_parent (parent_asset_id),
  KEY idx_asset_hierarchy_realname (realname_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS ims_asset_trace (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  trace_type VARCHAR(16) NOT NULL DEFAULT 'forward',
  asset_id BIGINT NOT NULL DEFAULT 0,
  realname_id BIGINT NOT NULL DEFAULT 0,
  node_chain TEXT,
  query_user_id BIGINT NOT NULL DEFAULT 0,
  tenant_id BIGINT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_asset_trace_asset (asset_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
