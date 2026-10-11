-- CONTENT · 公推模板导入任务（BUG-B058）
-- 新表由 create_all 在启动时创建；本文件供已有库手工对照。不改权限种子。
CREATE TABLE IF NOT EXISTS ims_content_layout_import_job (
  id BIGINT NOT NULL AUTO_INCREMENT,
  job_no VARCHAR(32) NOT NULL DEFAULT '',
  channel VARCHAR(16) NOT NULL DEFAULT '',
  status VARCHAR(16) NOT NULL DEFAULT 'SUCCESS',
  template_id BIGINT NOT NULL DEFAULT 0,
  template_name VARCHAR(128) NOT NULL DEFAULT '',
  message VARCHAR(256) NOT NULL DEFAULT '',
  created_by BIGINT NOT NULL DEFAULT 0,
  deleted INT NOT NULL DEFAULT 0,
  tenant_id BIGINT NOT NULL DEFAULT 0,
  created_at DATETIME NULL,
  updated_at DATETIME NULL,
  PRIMARY KEY (id),
  KEY ix_ims_content_layout_import_job_job_no (job_no),
  KEY ix_ims_content_layout_import_job_tenant_id (tenant_id)
);
