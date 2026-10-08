-- FLOW-004：超时督办 remind_count（已有 ims_flow_task 表时执行）
ALTER TABLE ims.ims_flow_task
  ADD COLUMN remind_count INT NOT NULL DEFAULT 0 AFTER comment;
