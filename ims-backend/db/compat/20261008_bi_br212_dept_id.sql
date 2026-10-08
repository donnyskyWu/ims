ALTER TABLE ims_bi_report_def ADD COLUMN dept_id BIGINT NOT NULL DEFAULT 0;
CREATE INDEX idx_ims_bi_report_def_dept_id ON ims_bi_report_def (dept_id);
ALTER TABLE ims_bi_share_link ADD COLUMN dept_id BIGINT NOT NULL DEFAULT 0;
CREATE INDEX idx_ims_bi_share_link_dept_id ON ims_bi_share_link (dept_id);
