-- S4 发布列表/回填/归档（已有 ims 库增量）
ALTER TABLE ims_content_publish ADD COLUMN published_at VARCHAR(32) NULL;
ALTER TABLE ims_content_publish ADD COLUMN archive_no VARCHAR(32) NULL;
ALTER TABLE ims_content_publish ADD COLUMN archive_package_url VARCHAR(512) NULL;
ALTER TABLE ims_content_publish ADD COLUMN archive_file_list JSON NULL;
ALTER TABLE ims_content_publish ADD COLUMN archived_at VARCHAR(32) NULL;
