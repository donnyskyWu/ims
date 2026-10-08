CREATE TABLE IF NOT EXISTS ims_sys_role (
  id BIGINT NOT NULL,
  tenant_id BIGINT NOT NULL DEFAULT 0,
  role_name VARCHAR(64) NOT NULL,
  data_scope VARCHAR(16) NOT NULL DEFAULT 'SELF',
  dingtalk_position VARCHAR(64) NULL,
  source VARCHAR(16) NOT NULL DEFAULT 'MANUAL',
  status VARCHAR(20) NOT NULL DEFAULT 'ENABLED',
  creator VARCHAR(64) NULL,
  create_time DATETIME NULL,
  updater VARCHAR(64) NULL,
  update_time DATETIME NULL,
  deleted TINYINT NOT NULL DEFAULT 0,
  PRIMARY KEY (id),
  UNIQUE KEY uk_ding_pos (tenant_id, dingtalk_position)
);

CREATE TABLE IF NOT EXISTS ims_sys_role_menu (
  id BIGINT NOT NULL,
  tenant_id BIGINT NOT NULL DEFAULT 0,
  role_id BIGINT NOT NULL,
  menu_id BIGINT NOT NULL,
  perm_code VARCHAR(128) NULL,
  creator VARCHAR(64) NULL,
  create_time DATETIME NULL,
  updater VARCHAR(64) NULL,
  update_time DATETIME NULL,
  deleted TINYINT NOT NULL DEFAULT 0,
  PRIMARY KEY (id),
  UNIQUE KEY uk_role_menu (role_id, menu_id)
);

CREATE TABLE IF NOT EXISTS ims_role_perm_detail (
  id BIGINT NOT NULL,
  tenant_id BIGINT NOT NULL DEFAULT 0,
  role_id BIGINT NOT NULL,
  module_code VARCHAR(64) NOT NULL,
  perm_code VARCHAR(128) NOT NULL,
  perm_level VARCHAR(8) NOT NULL,
  creator VARCHAR(64) NULL,
  create_time DATETIME NULL,
  updater VARCHAR(64) NULL,
  update_time DATETIME NULL,
  deleted TINYINT NOT NULL DEFAULT 0,
  PRIMARY KEY (id),
  UNIQUE KEY uk_role_perm (role_id, perm_code)
);

CREATE TABLE IF NOT EXISTS ims_sys_user_role (
  id BIGINT NOT NULL,
  tenant_id BIGINT NOT NULL DEFAULT 0,
  user_id BIGINT NOT NULL,
  role_id BIGINT NOT NULL,
  creator VARCHAR(64) NULL,
  create_time DATETIME NULL,
  updater VARCHAR(64) NULL,
  update_time DATETIME NULL,
  deleted TINYINT NOT NULL DEFAULT 0,
  PRIMARY KEY (id),
  UNIQUE KEY uk_user_role (user_id, role_id)
);

CREATE TABLE IF NOT EXISTS ims_sys_menu (
  id BIGINT NOT NULL,
  tenant_id BIGINT NOT NULL DEFAULT 0,
  parent_id BIGINT NOT NULL DEFAULT 0,
  menu_type VARCHAR(16) NOT NULL,
  route VARCHAR(128) NULL,
  name VARCHAR(64) NOT NULL,
  perm_code VARCHAR(128) NULL,
  visible TINYINT NOT NULL DEFAULT 1,
  creator VARCHAR(64) NULL,
  create_time DATETIME NULL,
  updater VARCHAR(64) NULL,
  update_time DATETIME NULL,
  deleted TINYINT NOT NULL DEFAULT 0,
  PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS ims_sys_dict_type (
  id BIGINT NOT NULL,
  tenant_id BIGINT NOT NULL DEFAULT 0,
  dict_type VARCHAR(64) NOT NULL,
  type_name VARCHAR(64) NOT NULL,
  creator VARCHAR(64) NULL,
  create_time DATETIME NULL,
  updater VARCHAR(64) NULL,
  update_time DATETIME NULL,
  deleted TINYINT NOT NULL DEFAULT 0,
  PRIMARY KEY (id),
  UNIQUE KEY uk_dict_type (tenant_id, dict_type)
);

CREATE TABLE IF NOT EXISTS ims_sys_dict_data (
  id BIGINT NOT NULL,
  tenant_id BIGINT NOT NULL DEFAULT 0,
  dict_type VARCHAR(64) NOT NULL,
  dict_label VARCHAR(64) NOT NULL,
  dict_value VARCHAR(64) NOT NULL,
  sort INT NOT NULL DEFAULT 0,
  status VARCHAR(16) NOT NULL,
  creator VARCHAR(64) NULL,
  create_time DATETIME NULL,
  updater VARCHAR(64) NULL,
  update_time DATETIME NULL,
  deleted TINYINT NOT NULL DEFAULT 0,
  PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS ims_sys_param (
  id BIGINT NOT NULL,
  tenant_id BIGINT NOT NULL DEFAULT 0,
  param_key VARCHAR(128) NOT NULL,
  param_value VARCHAR(512) NOT NULL,
  remark VARCHAR(255) NULL,
  creator VARCHAR(64) NULL,
  create_time DATETIME NULL,
  updater VARCHAR(64) NULL,
  update_time DATETIME NULL,
  deleted TINYINT NOT NULL DEFAULT 0,
  PRIMARY KEY (id),
  UNIQUE KEY uk_param (tenant_id, param_key)
);
