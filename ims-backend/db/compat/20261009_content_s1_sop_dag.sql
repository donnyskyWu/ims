-- CONTENT S1 · SOP 节点 DAG（predecessors / 并行组 / 节点审核岗位）
-- 运行时由 app.main.ensure_content_sop_dag_columns 补列；本文件供已有库手工对照。
ALTER TABLE ims_content_sop_node ADD COLUMN predecessors JSON NULL;
ALTER TABLE ims_content_sop_node ADD COLUMN parallel_group VARCHAR(64) NOT NULL DEFAULT '';
ALTER TABLE ims_content_sop_node ADD COLUMN need_review INT NOT NULL DEFAULT 0;
ALTER TABLE ims_content_sop_node ADD COLUMN reviewer_role VARCHAR(32) NOT NULL DEFAULT '';
