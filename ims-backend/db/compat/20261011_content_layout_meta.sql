-- CONTENT · 公推模板文档类型、标签（BUG-B006）
-- 运行时由 app.main.ensure_content_layout_meta_columns 补列；本文件供已有库手工对照。
-- 不改权限种子。已有行 document_type / tags 默认为空（页面显示「通用」）。
ALTER TABLE ims_content_layout_template ADD COLUMN document_type VARCHAR(32) NOT NULL DEFAULT '';
ALTER TABLE ims_content_layout_template ADD COLUMN tags VARCHAR(256) NOT NULL DEFAULT '';
