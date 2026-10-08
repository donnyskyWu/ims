ALTER TABLE ims_content_project ADD COLUMN author_article_id VARCHAR(64) NULL;
ALTER TABLE ims_content_project ADD COLUMN fb_sync_status VARCHAR(16) NOT NULL DEFAULT 'NONE';
ALTER TABLE ims_content_project ADD COLUMN fb_sync_version INT NOT NULL DEFAULT 0;
ALTER TABLE ims_content_project ADD COLUMN last_fb_sync_at VARCHAR(32) NULL;
ALTER TABLE ims_content_project ADD COLUMN last_fb_sync_error VARCHAR(512) NULL;

CREATE TABLE IF NOT EXISTS ims_fb_sync_outbox (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  content_project_id BIGINT NOT NULL,
  action VARCHAR(16) NOT NULL DEFAULT 'UPSERT',
  idempotency_key VARCHAR(128) NOT NULL DEFAULT '',
  payload_json JSON NULL,
  sync_status VARCHAR(16) NOT NULL DEFAULT 'PENDING',
  retry_count INT NOT NULL DEFAULT 0,
  next_retry_at DATETIME NULL,
  last_error_code INT NULL,
  last_error_msg VARCHAR(512) NULL,
  dead_letter TINYINT NOT NULL DEFAULT 0,
  creator BIGINT NOT NULL DEFAULT 0,
  tenant_id BIGINT NOT NULL DEFAULT 0,
  created_at DATETIME NULL,
  updated_at DATETIME NULL,
  UNIQUE KEY uk_fb_sync_idem (tenant_id, idempotency_key),
  KEY idx_fb_sync_content (content_project_id),
  KEY idx_fb_sync_pending (sync_status, next_retry_at)
);
