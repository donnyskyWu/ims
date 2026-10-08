-- IMS 自建 AUTH 表。只建 ims_*，不改现网用户主表。
CREATE TABLE IF NOT EXISTS ims_auth_user_mapping (
  id BIGINT NOT NULL,
  tenant_id BIGINT NOT NULL DEFAULT 0,
  user_id BIGINT NOT NULL,
  dingtalk_user_id VARCHAR(64) NOT NULL,
  union_id VARCHAR(64) NULL,
  dept_ids JSON NULL,
  sync_status VARCHAR(16) NOT NULL DEFAULT 'SUCCESS',
  last_sync_time DATETIME NULL,
  creator VARCHAR(64) NULL,
  create_time DATETIME NULL,
  updater VARCHAR(64) NULL,
  update_time DATETIME NULL,
  deleted TINYINT NOT NULL DEFAULT 0,
  PRIMARY KEY (id),
  UNIQUE KEY uk_tenant_ding (tenant_id, dingtalk_user_id)
);

CREATE TABLE IF NOT EXISTS ims_auth_user_dept (
  user_id BIGINT NOT NULL,
  dept_id BIGINT NOT NULL,
  tenant_id BIGINT NOT NULL DEFAULT 0,
  creator VARCHAR(64) NULL,
  create_time DATETIME NULL,
  updater VARCHAR(64) NULL,
  update_time DATETIME NULL,
  deleted TINYINT NOT NULL DEFAULT 0,
  PRIMARY KEY (user_id, dept_id),
  KEY idx_dept_user (dept_id, user_id)
);

CREATE TABLE IF NOT EXISTS ims_auth_org_event (
  id BIGINT NOT NULL,
  tenant_id BIGINT NOT NULL DEFAULT 0,
  dingtalk_event_id VARCHAR(64) NOT NULL,
  event_type VARCHAR(32) NOT NULL,
  idempotency_key VARCHAR(128) NOT NULL,
  payload_json JSON NULL,
  sync_status VARCHAR(16) NOT NULL,
  retry_count INT NOT NULL DEFAULT 0,
  next_retry_at DATETIME NULL,
  dead_letter TINYINT NOT NULL DEFAULT 0,
  creator VARCHAR(64) NULL,
  create_time DATETIME NULL,
  updater VARCHAR(64) NULL,
  update_time DATETIME NULL,
  deleted TINYINT NOT NULL DEFAULT 0,
  PRIMARY KEY (id),
  UNIQUE KEY uk_idem (idempotency_key)
);

CREATE TABLE IF NOT EXISTS ims_position_template (
  id BIGINT NOT NULL,
  tenant_id BIGINT NOT NULL DEFAULT 0,
  template_name VARCHAR(64) NOT NULL,
  dingtalk_position VARCHAR(64) NOT NULL,
  version INT NOT NULL,
  status VARCHAR(16) NOT NULL,
  grant_role_ids JSON NULL,
  applied_user_count INT NOT NULL DEFAULT 0,
  creator VARCHAR(64) NULL,
  create_time DATETIME NULL,
  updater VARCHAR(64) NULL,
  update_time DATETIME NULL,
  deleted TINYINT NOT NULL DEFAULT 0,
  PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS ims_user_scope (
  id BIGINT NOT NULL,
  tenant_id BIGINT NOT NULL DEFAULT 0,
  user_id BIGINT NOT NULL,
  scope_type VARCHAR(16) NOT NULL,
  scope_value VARCHAR(64) NOT NULL,
  creator VARCHAR(64) NULL,
  create_time DATETIME NULL,
  updater VARCHAR(64) NULL,
  update_time DATETIME NULL,
  deleted TINYINT NOT NULL DEFAULT 0,
  PRIMARY KEY (id),
  KEY idx_scope (scope_type, scope_value),
  KEY idx_user (user_id)
);
