-- FLOW-002 发起实例：business_key 幂等 + form_data
ALTER TABLE ims.ims_flow_instance
  ADD COLUMN business_key VARCHAR(64) NULL DEFAULT NULL AFTER title,
  ADD COLUMN form_data JSON NULL AFTER business_key;

ALTER TABLE ims.ims_flow_instance
  ADD UNIQUE KEY uk_flow_instance_biz_key (tenant_id, business_key);
