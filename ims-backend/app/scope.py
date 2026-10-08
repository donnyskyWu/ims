from dataclasses import dataclass, field

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core import utcnow
from app.models import Role, RoleMenu, RolePerm, User, UserDept, UserRole, UserScope

VALID_SCOPES = ("ALL", "DEPT", "IP_GROUP", "SELF")
RANK = {"SELF": 1, "IP_GROUP": 2, "DEPT": 3, "ALL": 4}
WHITELIST_PREFIXES = (
    "/admin-api/ims/auth/workbench",
    "/admin-api/ims/home",
)


@dataclass
class Spec:
    dept: bool = False
    ip_group: bool = False
    creator: bool = False
    br212: bool = False
    dept_col: str = "dept_id"
    creator_col: str = "creator_id"


@dataclass
class DataScope:
    kind: str
    user_id: int
    dept_ids: list[int] = field(default_factory=list)
    ip_group_ids: list[int] = field(default_factory=list)


SPECS = {
    "ims_sys_user": Spec(dept=True, creator=True),
    "ims_sys_role": Spec(),
    "ims_sys_menu": Spec(),
    "ims_sys_dict_type": Spec(),
    "ims_sys_dict_data": Spec(),
    "ims_sys_param": Spec(),
    "ims_sys_operate_log": Spec(),
    "ims_sys_login_log": Spec(),
    "ims_sys_notify": Spec(),
    "ims_auth_user_mapping": Spec(dept=True),
    "ims_auth_org_event": Spec(),
    "ims_position_template": Spec(),
    "scope_probe": Spec(dept=True, creator=True, br212=True),
    "oa_company": Spec(),
    "oa_realname": Spec(),
    "oa_sim_card": Spec(),
    "ims_cert_archive": Spec(creator=True, creator_col="holder_user_id"),
    "oa_phone": Spec(),
    "oa_platform_account": Spec(ip_group=True),
    "ims_acct_apply": Spec(creator=True, creator_col="applicant_user_id"),
    "ims_acct_recharge": Spec(creator=True, creator_col="operator_user_id"),
    "oa_ip_group": Spec(ip_group=True),
    "asset_ledger_blocked": Spec(),
    "ims_live_session": Spec(creator=True, creator_col="responsible_user_id"),
    "ims_live_alarm_record": Spec(),
    "ims_content_sop": Spec(),
    "ims_content_plan": Spec(creator=True),
    "ims_content_review": Spec(creator=True),
    "ims_content_project": Spec(creator=True),
    "ims_content_publish": Spec(creator=True),
    "ims_content_work_task_sheet": Spec(creator=True),
    "ims_content_task": Spec(creator=True),
    "ims_fb_sync_outbox": Spec(creator=True),
    "oa_collect_task": Spec(),
    "oa_collect_log": Spec(),
    "oa_collect_config": Spec(),
    "oa_collect_keyword": Spec(),
    "oa_threshold_config": Spec(),
    "ims_metadata_entity": Spec(),
    "ims_bi_custom_query": Spec(creator=True),
    "oa_internal_content": Spec(ip_group=True),
    "oa_internal_account": Spec(ip_group=True),
    "oa_external_work": Spec(ip_group=True),
    "oa_external_account": Spec(ip_group=True),
    "ims_meet_daily_report": Spec(dept=True, creator=True, creator_col="user_id"),
    "ims_meet_daily_review": Spec(creator=True, creator_col="reviewer_user_id"),
    "ims_meet_minutes": Spec(dept=True, creator=True, creator_col="recorder_user_id"),
    "ims_kb": Spec(creator=True, creator_col="owner_user_id"),
    "ims_kb_category": Spec(),
    "ims_kb_doc": Spec(creator=True, creator_col="uploader_user_id"),
    "ims_report_template": Spec(creator=True, creator_col="created_by"),
    "ims_report_submission": Spec(creator=True, creator_col="submitter_user_id"),
    "ims_report_audit": Spec(creator=True, creator_col="auditor_user_id"),
    "ims_train_material": Spec(creator=True, creator_col="uploader_user_id"),
    "ims_train_material_cate": Spec(),
    "ims_train_task": Spec(creator=True, creator_col="creator_user_id"),
    "ims_train_task_record": Spec(creator=True, creator_col="user_id"),
    "ims_fin_cost": Spec(creator=True, creator_col="entry_user_id"),
    "ims_fin_profit": Spec(),
    "ims_fin_share_result": Spec(),
    "ims_fin_period": Spec(),
    "ims_perf_scheme": Spec(creator=True, creator_col="created_by"),
    "ims_perf_record": Spec(creator=True, creator_col="created_by"),
    "ims_comp_asset": Spec(creator=True, creator_col="created_by"),
    "ims_exam_question": Spec(creator=True, creator_col="created_by"),
    "ims_flow_template": Spec(creator=True, creator_col="creator_id"),
    "ims_flow_instance": Spec(creator=True, creator_col="initiator_user_id"),
    "ims_flow_task": Spec(creator=True, creator_col="assignee_user_id"),
    "ims_alert_rule": Spec(creator=True, creator_col="created_by"),
    "ims_alert_record": Spec(),
    "ims_alert_dedup_policy": Spec(),
    "ims_air_api_key": Spec(creator=True, creator_col="owner_user_id"),
    "ims_air_audit_log": Spec(),
    "ims_content_layout_template": Spec(creator=True, creator_col="created_by"),
    "ims_eff_relation": Spec(creator=True, creator_col="changed_by"),
    "ims_air_skill": Spec(creator=True, creator_col="owner_user_id"),
    "ims_air_expert": Spec(creator=True, creator_col="owner_user_id"),
    "ims_bi_report_def": Spec(dept=True, creator=True, creator_col="creator_id", br212=True),
    "ims_bi_metric": Spec(creator=True, creator_col="creator_id"),
    "ims_air_model_config": Spec(creator=True, creator_col="creator_id"),
    "ims_air_prompt_config": Spec(creator=True, creator_col="creator_id"),
    "ims_query_template": Spec(creator=True, creator_col="owner_user_id"),
    "ims_bi_subscription": Spec(creator=True, creator_col="subscriber_user_id"),
    "ims_bi_share_link": Spec(dept=True, creator=True, creator_col="creator_user_id", br212=True),
}

PREFIXES = [
    ("GET", "/admin-api/ims/system/user", "ims_sys_user"),
    ("POST", "/admin-api/ims/system/user", "ims_sys_user"),
    ("PUT", "/admin-api/ims/system/user", "ims_sys_user"),
    ("GET", "/admin-api/ims/system/role", "ims_sys_role"),
    ("PUT", "/admin-api/ims/system/role", "ims_sys_role"),
    ("POST", "/admin-api/ims/system/role", "ims_sys_role"),
    ("GET", "/admin-api/ims/system/menu", "ims_sys_menu"),
    ("GET", "/admin-api/ims/system/dict-type", "ims_sys_dict_type"),
    ("GET", "/admin-api/ims/system/dict-data", "ims_sys_dict_data"),
    ("DELETE", "/admin-api/ims/system/dict-data", "ims_sys_dict_data"),
    ("GET", "/admin-api/ims/system/param", "ims_sys_param"),
    ("PUT", "/admin-api/ims/system/param", "ims_sys_param"),
    ("GET", "/admin-api/ims/system/operate-log", "ims_sys_operate_log"),
    ("GET", "/admin-api/ims/system/login-log", "ims_sys_login_log"),
    ("GET", "/admin-api/ims/system/notify", "ims_sys_notify"),
    ("GET", "/admin-api/ims/auth/org/users", "ims_auth_user_mapping"),
    ("GET", "/admin-api/ims/auth/org/events", "ims_auth_org_event"),
    ("GET", "/admin-api/ims/auth/org/sync-metrics", "ims_auth_org_event"),
    ("POST", "/admin-api/ims/auth/org/reconcile", "ims_auth_org_event"),
    ("POST", "/admin-api/ims/auth/org/sync-from-dingtalk", "ims_auth_org_event"),
    ("GET", "/admin-api/ims/auth/position", "ims_position_template"),
    ("POST", "/admin-api/ims/auth/position", "ims_position_template"),
    ("PUT", "/admin-api/ims/auth/position", "ims_position_template"),
    ("DELETE", "/admin-api/ims/auth/position", "ims_position_template"),
    ("GET", "/admin-api/ims/corp/resource/company", "oa_company"),
    ("GET", "/admin-api/ims/corp/resource/realname", "oa_realname"),
    ("GET", "/admin-api/ims/corp/resource/sim-card", "oa_sim_card"),
    ("POST", "/admin-api/ims/corp/resource/sim-card", "oa_sim_card"),
    ("PUT", "/admin-api/ims/corp/resource/sim-card", "oa_sim_card"),
    ("GET", "/admin-api/ims/corp/resource/certificate", "ims_cert_archive"),
    ("GET", "/admin-api/ims/corp/device/office", "asset_ledger_blocked"),
    ("GET", "/admin-api/ims/corp/device/live", "asset_ledger_blocked"),
    ("GET", "/admin-api/ims/corp/device/phone", "oa_phone"),
    ("GET", "/admin-api/ims/corp/account", "oa_platform_account"),
    ("POST", "/admin-api/ims/corp/account", "oa_platform_account"),
    ("GET", "/admin-api/ims/account/apply", "ims_acct_apply"),
    ("POST", "/admin-api/ims/account/apply", "ims_acct_apply"),
    ("PUT", "/admin-api/ims/account/apply", "ims_acct_apply"),
    ("GET", "/admin-api/ims/account/timeline", "ims_acct_apply"),
    ("POST", "/admin-api/ims/account/return", "ims_acct_apply"),
    ("POST", "/admin-api/ims/account/recharge", "ims_acct_recharge"),
    ("GET", "/admin-api/ims/account/recharge", "ims_acct_recharge"),
    ("GET", "/admin-api/ims/master/phone", "oa_phone"),
    ("POST", "/admin-api/ims/master/phone", "oa_phone"),
    ("PUT", "/admin-api/ims/master/phone", "oa_phone"),
    ("POST", "/admin-api/ims/master/platform-account", "oa_platform_account"),
    ("PUT", "/admin-api/ims/master/platform-account", "oa_platform_account"),
    ("GET", "/admin-api/ims/ip-group", "oa_ip_group"),
    ("POST", "/admin-api/ims/ip-group", "oa_ip_group"),
    ("PUT", "/admin-api/ims/ip-group", "oa_ip_group"),
    ("DELETE", "/admin-api/ims/ip-group", "oa_ip_group"),
    ("GET", "/admin-api/ims/live", "ims_live_session"),
    ("POST", "/admin-api/ims/live", "ims_live_session"),
    ("PUT", "/admin-api/ims/live", "ims_live_session"),
    ("GET", "/admin-api/ims/cost", "oa_platform_account"),
    ("POST", "/admin-api/ims/cost", "oa_platform_account"),
    ("PUT", "/admin-api/ims/cost", "oa_platform_account"),
    ("DELETE", "/admin-api/ims/cost", "oa_platform_account"),
    ("GET", "/admin-api/ims/content/work-task", "ims_content_work_task_sheet"),
    ("POST", "/admin-api/ims/content/work-task", "ims_content_work_task_sheet"),
    ("GET", "/admin-api/ims/content/task", "ims_content_task"),
    ("POST", "/admin-api/ims/content/task", "ims_content_task"),
    ("PUT", "/admin-api/ims/content/task", "ims_content_task"),
    ("GET", "/admin-api/ims/content/sop", "ims_content_sop"),
    ("POST", "/admin-api/ims/content/sop", "ims_content_sop"),
    ("PUT", "/admin-api/ims/content/sop", "ims_content_sop"),
    ("DELETE", "/admin-api/ims/content/sop", "ims_content_sop"),
    ("GET", "/admin-api/ims/content/plan", "ims_content_plan"),
    ("POST", "/admin-api/ims/content/plan", "ims_content_plan"),
    ("GET", "/admin-api/ims/content/review", "ims_content_review"),
    ("PUT", "/admin-api/ims/content/review", "ims_content_review"),
    ("POST", "/admin-api/ims/content/review", "ims_content_review"),
    ("GET", "/admin-api/ims/content/publish", "ims_content_publish"),
    ("POST", "/admin-api/ims/content/publish", "ims_content_publish"),
    ("PUT", "/admin-api/ims/content/publish", "ims_content_publish"),
    ("GET", "/admin-api/ims/content", "ims_content_project"),
    ("POST", "/admin-api/ims/content", "ims_content_project"),
    ("PUT", "/admin-api/ims/content", "ims_content_project"),
    ("DELETE", "/admin-api/ims/content", "ims_content_project"),
    ("GET", "/admin-api/ims/content/fb-sync", "ims_fb_sync_outbox"),
    ("POST", "/admin-api/ims/content/fb-sync", "ims_fb_sync_outbox"),
    ("GET", "/admin-api/ims/collect/task", "oa_collect_task"),
    ("POST", "/admin-api/ims/collect/task", "oa_collect_task"),
    ("PUT", "/admin-api/ims/collect/task", "oa_collect_task"),
    ("DELETE", "/admin-api/ims/collect/task", "oa_collect_task"),
    ("GET", "/admin-api/ims/collect/log", "oa_collect_log"),
    ("GET", "/admin-api/ims/collect/quality", "oa_collect_log"),
    ("POST", "/admin-api/ims/collect/manual-fill", "oa_collect_log"),
    ("GET", "/admin-api/ims/collect/external", "oa_collect_config"),
    ("POST", "/admin-api/ims/collect/external", "oa_collect_config"),
    ("PUT", "/admin-api/ims/collect/external", "oa_collect_config"),
    ("DELETE", "/admin-api/ims/collect/external", "oa_collect_config"),
    ("GET", "/admin-api/ims/collect/threshold", "oa_threshold_config"),
    ("POST", "/admin-api/ims/collect/threshold", "oa_threshold_config"),
    ("PUT", "/admin-api/ims/collect/threshold", "oa_threshold_config"),
    ("DELETE", "/admin-api/ims/collect/threshold", "oa_threshold_config"),
    ("GET", "/admin-api/ims/collect/metadata", "ims_metadata_entity"),
    ("POST", "/admin-api/ims/collect/metadata", "ims_metadata_entity"),
    ("PUT", "/admin-api/ims/collect/metadata", "ims_metadata_entity"),
    ("GET", "/admin-api/ims/bi/query", "ims_bi_custom_query"),
    ("POST", "/admin-api/ims/bi/query", "ims_bi_custom_query"),
    ("PUT", "/admin-api/ims/bi/query", "ims_bi_custom_query"),
    ("GET", "/admin-api/ims/int-analysis/work", "oa_internal_content"),
    ("GET", "/admin-api/ims/int-analysis/account", "oa_internal_account"),
    ("GET", "/admin-api/ims/comp-analysis/work", "oa_external_work"),
    ("GET", "/admin-api/ims/comp-analysis/account", "oa_external_account"),
    ("GET", "/admin-api/ims/comp/asset", "ims_comp_asset"),
    ("POST", "/admin-api/ims/comp/asset", "ims_comp_asset"),
    ("GET", "/admin-api/ims/perf/exam", "ims_exam_question"),
    ("GET", "/admin-api/ims/flow/template", "ims_flow_template"),
    ("GET", "/admin-api/ims/flow/instance", "ims_flow_instance"),
    ("POST", "/admin-api/ims/flow/instance", "ims_flow_instance"),
    ("GET", "/admin-api/ims/flow/task", "ims_flow_task"),
    ("PUT", "/admin-api/ims/flow/task", "ims_flow_task"),
    ("GET", "/admin-api/ims/flow/timeout", "ims_flow_task"),
    ("PUT", "/admin-api/ims/flow/timeout", "ims_flow_task"),
    ("GET", "/admin-api/ims/bi/screen", "ims_bi_report_def"),
    ("GET", "/admin-api/ims/monitor/ip-theme", "oa_external_work"),
    ("GET", "/admin-api/ims/monitor/industry", "oa_external_work"),
    ("GET", "/admin-api/ims/meet/daily", "ims_meet_daily_report"),
    ("POST", "/admin-api/ims/meet/daily", "ims_meet_daily_report"),
    ("PUT", "/admin-api/ims/meet/daily", "ims_meet_daily_report"),
    ("GET", "/admin-api/ims/meet/review", "ims_meet_daily_review"),
    ("PUT", "/admin-api/ims/meet/review", "ims_meet_daily_review"),
    ("GET", "/admin-api/ims/meet/minutes", "ims_meet_minutes"),
    ("POST", "/admin-api/ims/meet/minutes", "ims_meet_minutes"),
    ("GET", "/admin-api/ims/meet/stat", "ims_meet_daily_report"),
    ("GET", "/admin-api/ims/air/kb", "ims_kb_doc"),
    ("POST", "/admin-api/ims/air/kb", "ims_kb_doc"),
    ("GET", "/admin-api/ims/air/kb/category", "ims_kb_category"),
    ("POST", "/admin-api/ims/air/kb/category", "ims_kb_category"),
    ("POST", "/admin-api/ims/air/kb/doc/audit", "ims_kb_doc"),
    ("GET", "/admin-api/ims/report/template", "ims_report_template"),
    ("POST", "/admin-api/ims/report/template", "ims_report_template"),
    ("PUT", "/admin-api/ims/report/template", "ims_report_template"),
    ("DELETE", "/admin-api/ims/report/template", "ims_report_template"),
    ("GET", "/admin-api/ims/report/submit", "ims_report_submission"),
    ("POST", "/admin-api/ims/report/submit", "ims_report_submission"),
    ("GET", "/admin-api/ims/report/audit", "ims_report_submission"),
    ("PUT", "/admin-api/ims/report/audit", "ims_report_submission"),
    ("GET", "/admin-api/ims/report/stat", "ims_report_submission"),
    ("GET", "/admin-api/ims/train/task", "ims_train_task"),
    ("GET", "/admin-api/ims/train/stat", "ims_train_task"),
    ("POST", "/admin-api/ims/train/task", "ims_train_task"),
    ("PUT", "/admin-api/ims/train/task", "ims_train_task_record"),
    ("POST", "/admin-api/ims/train/task", "ims_train_task_record"),
    ("GET", "/admin-api/ims/train/material", "ims_train_material"),
    ("POST", "/admin-api/ims/train/material", "ims_train_material"),
    ("DELETE", "/admin-api/ims/train/material", "ims_train_material"),
    ("GET", "/admin-api/ims/train/material/cates", "ims_train_material_cate"),
    ("GET", "/admin-api/ims/fin/cost", "ims_fin_cost"),
    ("POST", "/admin-api/ims/fin/cost", "ims_fin_cost"),
    ("PUT", "/admin-api/ims/fin/cost", "ims_fin_cost"),
    ("POST", "/admin-api/ims/fin/profit/recalc", "ims_fin_profit"),
    ("GET", "/admin-api/ims/fin/profit", "ims_fin_profit"),
    ("GET", "/admin-api/ims/fin/share", "ims_fin_share_result"),
    ("PUT", "/admin-api/ims/fin/share", "ims_fin_share_result"),
    ("GET", "/admin-api/ims/fin/period", "ims_fin_period"),
    ("POST", "/admin-api/ims/fin/period", "ims_fin_period"),
    ("GET", "/admin-api/ims/dc/profit-trace", "ims_fin_profit"),
    ("GET", "/admin-api/ims/perf/scheme", "ims_perf_scheme"),
    ("POST", "/admin-api/ims/perf/scheme", "ims_perf_scheme"),
    ("GET", "/admin-api/ims/perf/execution", "ims_perf_record"),
    ("POST", "/admin-api/ims/perf/execution", "ims_perf_record"),
    ("GET", "/admin-api/ims/dc/trace", "ims_live_session"),
    ("POST", "/admin-api/ims/dc/trace", "ims_live_session"),
    ("GET", "/admin-api/ims/alert/rule", "ims_alert_rule"),
    ("POST", "/admin-api/ims/alert/rule", "ims_alert_rule"),
    ("PUT", "/admin-api/ims/alert/rule", "ims_alert_rule"),
    ("GET", "/admin-api/ims/alert/check", "ims_alert_record"),
    ("PUT", "/admin-api/ims/alert/check", "ims_alert_record"),
    ("POST", "/admin-api/ims/alert/check", "ims_alert_record"),
    ("GET", "/admin-api/ims/alert/dedup", "ims_alert_dedup_policy"),
    ("GET", "/admin-api/ims/alert/history", "ims_alert_record"),
    ("GET", "/admin-api/ims/content/layout-template", "ims_content_layout_template"),
    ("POST", "/admin-api/ims/content/layout-template", "ims_content_layout_template"),
    ("PUT", "/admin-api/ims/content/layout-template", "ims_content_layout_template"),
    ("GET", "/admin-api/ims/perf/result/export", "ims_perf_record"),
    ("GET", "/admin-api/ims/perf/result", "ims_perf_record"),
    ("GET", "/admin-api/ims/perf/result/", "ims_perf_record"),
    ("PUT", "/admin-api/ims/meet/minutes", "ims_meet_minutes"),
    ("GET", "/admin-api/ims/eff/relation", "ims_eff_relation"),
    ("POST", "/admin-api/ims/eff/relation", "ims_eff_relation"),
    ("GET", "/admin-api/ims/eff/metrics", "ims_eff_relation"),
    ("GET", "/admin-api/ims/eff/inventory", "ims_eff_relation"),
    ("GET", "/admin-api/ims/bi/report/list", "ims_bi_report_def"),
    ("POST", "/admin-api/ims/bi/report", "ims_bi_report_def"),
    ("GET", "/admin-api/ims/bi/report/categories", "ims_bi_report_def"),
    ("GET", "/admin-api/ims/bi/report/datasets", "ims_bi_report_def"),
    ("PUT", "/admin-api/ims/bi/report", "ims_bi_report_def"),
    ("POST", "/admin-api/ims/bi/report/query", "ims_bi_report_def"),
    ("POST", "/admin-api/ims/bi/report/", "ims_bi_report_def"),
    ("GET", "/admin-api/ims/air/cfg/model", "ims_air_model_config"),
    ("POST", "/admin-api/ims/air/cfg/model", "ims_air_model_config"),
    ("PUT", "/admin-api/ims/air/cfg/model", "ims_air_model_config"),
    ("GET", "/admin-api/ims/air/cfg/prompt", "ims_air_prompt_config"),
    ("POST", "/admin-api/ims/air/cfg/prompt", "ims_air_prompt_config"),
    ("PUT", "/admin-api/ims/air/cfg/prompt", "ims_air_prompt_config"),
    ("GET", "/admin-api/ims/air/cfg/key", "ims_air_api_key"),
    ("GET", "/admin-api/ims/air/cfg/audit", "ims_air_audit_log"),
    ("GET", "/admin-api/ims/master/overview", "oa_company"),
    ("GET", "/admin-api/ims/bi/metric/list", "ims_bi_metric"),
    ("POST", "/admin-api/ims/bi/metric", "ims_bi_metric"),
    ("PUT", "/admin-api/ims/bi/metric", "ims_bi_metric"),
    ("DELETE", "/admin-api/ims/bi/metric", "ims_bi_metric"),
    ("POST", "/admin-api/ims/bi/metric/", "ims_bi_metric"),
    ("POST", "/admin-api/ims/bi/metric/analysis", "ims_bi_metric"),
    ("GET", "/admin-api/ims/bi/metric/", "ims_bi_metric"),
    ("GET", "/admin-api/ims/analysis/query-tool", "ims_query_template"),
    ("POST", "/admin-api/ims/analysis/query-tool", "ims_query_template"),
    ("PUT", "/admin-api/ims/analysis/query-tool", "ims_query_template"),
    ("DELETE", "/admin-api/ims/analysis/query-tool", "ims_query_template"),
    ("GET", "/admin-api/ims/bi/subscribe", "ims_bi_subscription"),
    ("POST", "/admin-api/ims/bi/subscribe", "ims_bi_subscription"),
    ("PUT", "/admin-api/ims/bi/subscribe", "ims_bi_subscription"),
    ("DELETE", "/admin-api/ims/bi/subscribe", "ims_bi_subscription"),
    ("GET", "/admin-api/ims/bi/subscribe/share-link", "ims_bi_share_link"),
    ("POST", "/admin-api/ims/bi/subscribe/share-link", "ims_bi_share_link"),
    ("PUT", "/admin-api/ims/bi/subscribe/share-approval", "ims_bi_share_link"),
    ("GET", "/admin-api/ims/bi/subscribe/publish", "ims_bi_report_def"),
    ("POST", "/admin-api/ims/bi/report/preview", "ims_bi_report_def"),
    ("POST", "/admin-api/ims/perf/execution/", "ims_perf_record"),
    ("PUT", "/admin-api/ims/perf/execution", "ims_perf_record"),
    ("GET", "/admin-api/ims/bi/report", "ims_bi_custom_query"),
    ("GET", "/admin-api/ims/air/skill", "ims_air_skill"),
    ("POST", "/admin-api/ims/air/skill", "ims_air_skill"),
    ("PUT", "/admin-api/ims/air/skill", "ims_air_skill"),
    ("GET", "/admin-api/ims/air/expert", "ims_air_expert"),
    ("POST", "/admin-api/ims/air/expert", "ims_air_expert"),
    ("PUT", "/admin-api/ims/air/expert", "ims_air_expert"),
]


def deny():
    from app.api import AuthError

    raise AuthError(1008, "无数据权限")


def match_table(method: str, path: str) -> str | None:
    found = None
    length = -1
    for item_method, prefix, table in PREFIXES:
        if item_method == method and path.startswith(prefix) and len(prefix) > length:
            found = table
            length = len(prefix)
    return found


def enabled_roles(db: Session, user: User) -> list[Role]:
    db.flush()
    role_ids = list(db.scalars(select(UserRole.role_id).where(UserRole.user_id == user.id)).all())
    if not role_ids:
        return []
    return list(
        db.scalars(
            select(Role).where(Role.id.in_(role_ids), Role.deleted == 0, Role.status == "ENABLED")
        ).all()
    )


def dept_ids_of(db: Session, user: User) -> list[int]:
    rows = db.scalars(
        select(UserDept.dept_id).where(
            UserDept.user_id == user.id,
            UserDept.tenant_id == (user.tenant_id or 0),
        )
    ).all()
    return sorted({int(row) for row in rows})


def resolve(db: Session, user: User) -> DataScope:
    roles = enabled_roles(db, user)
    if not roles:
        deny()
    for role in roles:
        if role.data_scope not in VALID_SCOPES:
            deny()
    role_ids = [role.id for role in roles]
    perms = db.scalar(select(func.count()).select_from(RolePerm).where(RolePerm.role_id.in_(role_ids))) or 0
    menus = db.scalar(select(func.count()).select_from(RoleMenu).where(RoleMenu.role_id.in_(role_ids))) or 0
    if perms == 0 and menus == 0:
        deny()
    kind = max((role.data_scope for role in roles), key=lambda item: RANK[item])
    scope = DataScope(kind=kind, user_id=user.id, dept_ids=dept_ids_of(db, user))
    if kind == "IP_GROUP":
        rows = db.scalars(
            select(UserScope.scope_value).where(
                UserScope.user_id == user.id,
                UserScope.deleted == 0,
                UserScope.scope_type == "IP_GROUP",
                UserScope.tenant_id == (user.tenant_id or 0),
            )
        ).all()
        scope.ip_group_ids = sorted({int(row) for row in rows if str(row).isdigit()})
        if not scope.ip_group_ids:
            deny()
    return scope


def fit(scope: DataScope, spec: Spec) -> None:
    if scope.kind == "DEPT" and not spec.dept:
        deny()
    if scope.kind == "IP_GROUP" and not spec.ip_group:
        deny()
    if scope.kind == "SELF" and not spec.creator:
        deny()


def gate(db: Session, request, user: User) -> None:
    path = request.url.path
    if any(path.startswith(prefix) for prefix in WHITELIST_PREFIXES):
        request.state.scope = None
        return
    table = match_table(request.method, path)
    if table is None or table not in SPECS:
        deny()
    scope = resolve(db, user)
    fit(scope, SPECS[table])
    request.state.scope = scope
    request.state.scope_table = table


def restrict_users(stmt, actor: User, scope: DataScope):
    stmt = stmt.where(User.tenant_id == (actor.tenant_id or 0))
    if scope.kind == "ALL":
        return stmt
    if scope.kind == "SELF":
        return stmt.where(User.id == actor.id)
    if scope.kind == "DEPT":
        if not scope.dept_ids:
            return stmt.where(User.id < 0)
        return stmt.where(
            User.id.in_(
                select(UserDept.user_id).where(
                    UserDept.dept_id.in_(scope.dept_ids),
                    UserDept.tenant_id == (actor.tenant_id or 0),
                )
            )
        )
    return stmt.where(User.id < 0)


def user_visible(db: Session, actor: User, scope: DataScope, target: User) -> bool:
    if target.deleted or (target.tenant_id or 0) != (actor.tenant_id or 0):
        return False
    if scope.kind == "ALL":
        return True
    if scope.kind == "SELF":
        return target.id == actor.id
    if scope.kind == "DEPT":
        if not scope.dept_ids:
            return False
        found = db.scalar(
            select(UserDept.user_id).where(
                UserDept.user_id == target.id,
                UserDept.dept_id.in_(scope.dept_ids),
                UserDept.tenant_id == (actor.tenant_id or 0),
            )
        )
        return found is not None
    return False


def refresh_user_scope(db: Session, user_id: int) -> None:
    from app.api import AuthError

    db.execute(delete(UserScope).where(UserScope.user_id == user_id))
    user = db.get(User, user_id)
    if user is None or user.deleted:
        return
    try:
        scope = resolve(db, user)
    except AuthError:
        return
    now = utcnow()
    tenant_id = user.tenant_id or 0
    rows: list[tuple[str, str]] = []
    if scope.kind == "ALL":
        rows.append(("ALL", "*"))
    elif scope.kind == "DEPT":
        rows.extend(("DEPT", str(dept_id)) for dept_id in scope.dept_ids)
    elif scope.kind == "SELF":
        rows.append(("SELF", str(user_id)))
    elif scope.kind == "IP_GROUP":
        rows.extend(("IP_GROUP", str(group_id)) for group_id in scope.ip_group_ids)
    for scope_type, scope_value in rows:
        db.add(
            UserScope(
                user_id=user_id,
                scope_type=scope_type,
                scope_value=scope_value,
                creator=user_id,
                updater=user_id,
                tenant_id=tenant_id,
                created_at=now,
                updated_at=now,
            )
        )


def refresh_role_holders(db: Session, role_id: int) -> None:
    holder_ids = db.scalars(select(UserRole.user_id).where(UserRole.role_id == role_id)).all()
    for user_id in holder_ids:
        refresh_user_scope(db, int(user_id))


def intersection_sql(scope: DataScope, tenant_id: int, spec: Spec) -> tuple[str, dict]:
    if not spec.br212:
        deny()
    fit(scope, spec)
    params: dict = {"tenant_id": tenant_id, "cs_tenant": tenant_id, "self_id": scope.user_id}
    sql = [" AND t.tenant_id = :tenant_id"]
    if scope.kind == "ALL":
        sql.append(" AND (1=1)")
    elif scope.kind == "DEPT":
        if not scope.dept_ids:
            sql.append(" AND (1=0)")
        else:
            names = []
            for index, dept_id in enumerate(scope.dept_ids):
                key = f"vd{index}"
                params[key] = dept_id
                names.append(f":{key}")
            sql.append(f" AND (t.{spec.dept_col} IN ({', '.join(names)}))")
    elif scope.kind == "SELF":
        params["viewer_id"] = scope.user_id
        sql.append(f" AND (t.{spec.creator_col} = :viewer_id)")
    else:
        deny()
    creator = [
        " AND EXISTS (SELECT 1 FROM ims_user_scope cs WHERE cs.deleted = 0",
        f" AND cs.user_id = t.{spec.creator_col} AND cs.tenant_id = :cs_tenant",
        " AND (cs.scope_type = 'ALL'",
    ]
    if scope.dept_ids:
        names = []
        for index, dept_id in enumerate(scope.dept_ids):
            key = f"cd{index}"
            params[key] = str(dept_id)
            names.append(f":{key}")
        creator.append(f" OR (cs.scope_type = 'DEPT' AND cs.scope_value IN ({', '.join(names)}))")
    if scope.ip_group_ids:
        names = []
        for index, group_id in enumerate(scope.ip_group_ids):
            key = f"ig{index}"
            params[key] = str(group_id)
            names.append(f":{key}")
        creator.append(f" OR (cs.scope_type = 'IP_GROUP' AND cs.scope_value IN ({', '.join(names)}))")
    creator.append(" OR (cs.scope_type = 'SELF' AND cs.user_id = :self_id)))")
    sql.append("".join(creator))
    return "".join(sql), params


def scope_values(db: Session, user_id: int) -> set[tuple[str, str]]:
    rows = db.scalars(select(UserScope).where(UserScope.user_id == user_id, UserScope.deleted == 0)).all()
    return {(row.scope_type, row.scope_value) for row in rows}
