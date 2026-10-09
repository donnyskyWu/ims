ALTER TABLE ims_content_project ADD COLUMN body_format VARCHAR(20) NOT NULL DEFAULT 'PLAIN';
ALTER TABLE ims_content_project ADD COLUMN layout_json TEXT NULL;
ALTER TABLE ims_content_project ADD COLUMN layout_template_id BIGINT NULL;
ALTER TABLE ims_content_layout_template ADD COLUMN preset_code VARCHAR(32) NOT NULL DEFAULT '';
ALTER TABLE ims_content_layout_template ADD COLUMN layout_json TEXT NULL;
