-- TRAIN-002 学习进度/完成确认（#48）：已有 ims_train_task_record 表时执行
ALTER TABLE ims_train_task_record
  ADD COLUMN material_progress JSON NULL AFTER progress,
  ADD COLUMN finished_at DATETIME NULL AFTER confirm_score;
