-- W5 采集配置（M8）：已有 ops 库补列；ims 库元数据表由 ORM create_all 创建
-- 执行前请备份；仅在 oa_collect_config 已存在但缺少 collect_enabled 时使用

ALTER TABLE oa_collect_config
  ADD COLUMN collect_enabled TINYINT NOT NULL DEFAULT 1 COMMENT '是否参与外部统一采集';
