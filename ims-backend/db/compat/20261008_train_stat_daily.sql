-- #76 TRAIN-003 部门日汇总 + 学习时长（已有库升级；新库由 ORM create_all 建表）
ALTER TABLE ims_train_task_record
  ADD COLUMN study_seconds INT NOT NULL DEFAULT 0;

CREATE TABLE IF NOT EXISTS ims_train_stat_daily (
  id BIGINT NOT NULL AUTO_INCREMENT,
  stat_date DATE NOT NULL,
  dept_id BIGINT NOT NULL DEFAULT 0,
  dept_name VARCHAR(128) NOT NULL DEFAULT '',
  assigned_count INT NOT NULL DEFAULT 0,
  finished_count INT NOT NULL DEFAULT 0,
  finish_rate DOUBLE NOT NULL DEFAULT 0,
  avg_duration_minutes INT NOT NULL DEFAULT 0,
  deleted INT NOT NULL DEFAULT 0,
  tenant_id BIGINT NOT NULL DEFAULT 0,
  created_at DATETIME NULL,
  updated_at DATETIME NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uk_train_stat_daily (tenant_id, stat_date, dept_id)
);
