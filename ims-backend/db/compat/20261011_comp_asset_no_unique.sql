-- 竞品库单号不可变。
-- 已有库先执行 scripts/repair_comp_asset_no.py（有重复时用 --apply），确认无重复后再执行本文件。
-- 新库 create_all 已包含 uk_comp_asset_no 与 ims_comp_asset_seq，不必再跑。
-- 本文件只加表和唯一约束，不 UPDATE ims_comp_asset.asset_no。

CREATE TABLE IF NOT EXISTS ims_comp_asset_seq (
  id BIGINT NOT NULL AUTO_INCREMENT,
  biz_date VARCHAR(8) NOT NULL,
  seq_val INT NOT NULL DEFAULT 0,
  tenant_id BIGINT NOT NULL DEFAULT 0,
  PRIMARY KEY (id),
  UNIQUE KEY uk_comp_asset_seq_day (tenant_id, biz_date)
);

ALTER TABLE ims_comp_asset
  ADD UNIQUE KEY uk_comp_asset_no (tenant_id, asset_no);
