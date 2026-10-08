-- W9-14 · 绩效人工调整字段（已有 ims 库增量）
ALTER TABLE ims_perf_record
  ADD COLUMN calc_base_score DOUBLE NULL AFTER total_score,
  ADD COLUMN manual_adjustment DOUBLE NOT NULL DEFAULT 0 AFTER calc_base_score,
  ADD COLUMN adjust_remark VARCHAR(256) NOT NULL DEFAULT '' AFTER manual_adjustment;
