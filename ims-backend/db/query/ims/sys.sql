-- name: ListRoles :many
SELECT id, role_name, data_scope, status FROM ims_sys_role WHERE tenant_id = ? AND deleted = 0;
