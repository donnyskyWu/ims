-- CONTENT · SOP 适用平台（抖音/快手/视频号/微信公众号/全平台）
-- 运行时由 app.main.ensure_content_sop_platform_column 补列；本文件供已有库手工对照。
ALTER TABLE ims_content_sop ADD COLUMN platform VARCHAR(32) NOT NULL DEFAULT '';
