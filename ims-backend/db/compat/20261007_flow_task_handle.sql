-- FLOW-002 P2：待办任务表（处理通过/驳回桩）
CREATE TABLE IF NOT EXISTS ims.ims_flow_task (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  instance_id BIGINT NOT NULL DEFAULT 0,
  node_order INT NOT NULL DEFAULT 1,
  node_name VARCHAR(128) NOT NULL DEFAULT '',
  node_type VARCHAR(16) NOT NULL DEFAULT 'APPROVE',
  assignee_user_id BIGINT NOT NULL DEFAULT 0,
  task_status VARCHAR(16) NOT NULL DEFAULT 'PENDING',
  comment VARCHAR(512) NOT NULL DEFAULT '',
  deleted TINYINT NOT NULL DEFAULT 0,
  tenant_id BIGINT NOT NULL DEFAULT 0,
  started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  handled_at DATETIME NULL DEFAULT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_flow_task_instance (instance_id),
  KEY idx_flow_task_assignee (assignee_user_id),
  KEY idx_flow_task_status (task_status),
  KEY idx_flow_task_tenant (tenant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
