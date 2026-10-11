-- CONTENT · 内容所属账号（BUG-B009 筛选 accountId）
-- 运行时由 app.main.ensure_content_project_account_column 补列；本文件供已有库手工对照。
-- 不改权限种子。已有内容 account_id 默认为 0。
ALTER TABLE ims_content_project ADD COLUMN account_id BIGINT NOT NULL DEFAULT 0;
