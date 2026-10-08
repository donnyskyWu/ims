-- ims_content_plan · 计划终止申请原因（#36）
ALTER TABLE ims_content_plan
  ADD COLUMN terminate_reason VARCHAR(512) NOT NULL DEFAULT '' COMMENT '计划终止申请原因';
