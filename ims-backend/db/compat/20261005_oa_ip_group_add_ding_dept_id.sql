-- 现网 OPS 表只加列。人工运维窗口执行，重复执行需先确认列不存在。
ALTER TABLE oa_ip_group ADD COLUMN ding_dept_id BIGINT NULL COMMENT '钉钉部门映射';
