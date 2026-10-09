from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core import utcnow
from app.ops_db import OpsBase


class Company(OpsBase):
    __tablename__ = "oa_company"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_name: Mapped[str] = mapped_column(String(100), default="")
    credit_code: Mapped[str] = mapped_column(String(18), default="")
    industry: Mapped[str] = mapped_column(String(64), default="")
    address: Mapped[str] = mapped_column(String(255), default="")
    legal_name: Mapped[str] = mapped_column(String(64), default="")
    legal_id_card_enc: Mapped[str] = mapped_column(String(512), default="")
    mp_capacity_standard: Mapped[int] = mapped_column(Integer, default=0)
    expansion_history: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(16), default="ENABLED")
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Realname(OpsBase):
    __tablename__ = "oa_realname"
    __table_args__ = (UniqueConstraint("tenant_id", "phone_sha256", name="uk_realname_phone"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    real_name: Mapped[str] = mapped_column(String(64), default="")
    id_type: Mapped[str] = mapped_column(String(32), default="")
    id_card_enc: Mapped[str] = mapped_column(String(512), default="")
    phone_enc: Mapped[str] = mapped_column(String(512), default="")
    phone_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    wechat: Mapped[str] = mapped_column(String(64), default="")
    gender: Mapped[str] = mapped_column(String(16), default="")
    status: Mapped[str] = mapped_column(String(16), default="ENABLED")
    company_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Phone(OpsBase):
    __tablename__ = "oa_phone"
    __table_args__ = (UniqueConstraint("tenant_id", "phone_sha256", name="uk_phone_number"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    phone_enc: Mapped[str] = mapped_column(String(512), default="")
    phone_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    phone_code: Mapped[str] = mapped_column(String(64), default="")
    phone_model: Mapped[str] = mapped_column(String(64), default="")
    keeper_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    wechat_bound: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(16), default="IN_USE")
    device_number: Mapped[str] = mapped_column(String(64), default="")
    phone_type: Mapped[str] = mapped_column(String(32), default="")
    is_aochuang: Mapped[str] = mapped_column(String(8), default="")
    handler_name: Mapped[str] = mapped_column(String(64), default="")
    purchase_batch: Mapped[str] = mapped_column(String(64), default="")
    purchase_date: Mapped[str] = mapped_column(String(10), default="")
    purchase_time: Mapped[str] = mapped_column(String(8), default="")
    settings_screenshot_key: Mapped[str] = mapped_column(String(255), default="")
    front_image_key: Mapped[str] = mapped_column(String(255), default="")
    back_image_key: Mapped[str] = mapped_column(String(255), default="")
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class IpGroup(OpsBase):
    __tablename__ = "oa_ip_group"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    group_name: Mapped[str] = mapped_column(String(100), default="")
    group_type: Mapped[str] = mapped_column(String(16), default="SMALL")
    parent_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    leader_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    level: Mapped[str] = mapped_column(String(8), default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    remark: Mapped[str] = mapped_column(String(255), default="")
    ding_dept_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="ENABLED")
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class IpGroupMember(OpsBase):
    __tablename__ = "oa_ip_group_member"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ip_group_id: Mapped[int] = mapped_column(BigInteger, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    position: Mapped[str] = mapped_column(String(32), default="")
    relation_type: Mapped[str] = mapped_column(String(16), default="PRIMARY")
    is_leader: Mapped[int] = mapped_column(Integer, default=0)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class IpGroupAnchorRel(OpsBase):
    __tablename__ = "oa_ip_group_anchor_rel"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ip_group_id: Mapped[int] = mapped_column(BigInteger, index=True)
    anchor_user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    anchor_type: Mapped[str] = mapped_column(String(32), default="")
    is_primary: Mapped[int] = mapped_column(Integer, default=0)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AuthorUser(OpsBase):
    __tablename__ = "oa_author"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    author_name: Mapped[str] = mapped_column(String(64), default="")
    ip_group_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    author_type: Mapped[str] = mapped_column(String(32), default="")
    primary_account_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="ENABLED")
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class PlatformAccount(OpsBase):
    __tablename__ = "oa_platform_account"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    account_no: Mapped[str] = mapped_column(String(64), default="")
    account_name: Mapped[str] = mapped_column(String(128), default="")
    platform_type: Mapped[str] = mapped_column(String(32), default="", index=True)
    platform_account_id: Mapped[str] = mapped_column(String(128), default="")
    ip_group_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    company_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    realname_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    phone_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    sim_card_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    holder_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    author_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    cookie_enc: Mapped[str] = mapped_column(String(512), default="")
    credential_ref: Mapped[str] = mapped_column(String(128), default="")
    status: Mapped[str] = mapped_column(String(32), default="IN_USE")
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class CollectorAccountBind(OpsBase):
    __tablename__ = "oa_collector_account_bind"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    oa_account_id: Mapped[int] = mapped_column(BigInteger, index=True)
    collector_account_id: Mapped[str] = mapped_column(String(128), default="")
    bind_status: Mapped[str] = mapped_column(String(32), default="UNBOUND")
    conn_status: Mapped[str] = mapped_column(String(32), default="")
    last_probe_at: Mapped[str] = mapped_column(String(32), default="")
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class LiveRoom(OpsBase):
    __tablename__ = "live_room"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    author_id: Mapped[str] = mapped_column(String(64), default="")
    nickname: Mapped[str] = mapped_column(String(128), default="")
    avatar: Mapped[str] = mapped_column(String(512), default="")
    live_id: Mapped[str] = mapped_column(String(64), default="")
    live_name: Mapped[str] = mapped_column(String(256), default="")
    cover: Mapped[str] = mapped_column(String(512), default="")
    status: Mapped[int] = mapped_column(Integer, default=1)
    start_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    orientation: Mapped[str] = mapped_column(String(16), default="")
    pay_type: Mapped[str] = mapped_column(String(16), default="")
    play_url: Mapped[str] = mapped_column(String(512), default="")
    replay_url: Mapped[str] = mapped_column(String(512), default="")
    push_url: Mapped[str] = mapped_column(String(512), default="")
    viewer_count: Mapped[int] = mapped_column(Integer, default=0)
    like_count: Mapped[int] = mapped_column(Integer, default=0)
    reservation_count: Mapped[int] = mapped_column(Integer, default=0)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AccountCost(OpsBase):
    __tablename__ = "oa_account_cost"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(BigInteger, index=True)
    cost_type: Mapped[str] = mapped_column(String(32), default="PROCESS")
    process_subtype: Mapped[str] = mapped_column(String(32), default="")
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    pay_method: Mapped[str] = mapped_column(String(32), default="")
    pay_date: Mapped[str] = mapped_column(String(10), default="")
    period: Mapped[str] = mapped_column(String(7), default="")
    handler_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    remark: Mapped[str] = mapped_column(String(255), default="")
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class SimCard(OpsBase):
    __tablename__ = "oa_sim_card"
    __table_args__ = (UniqueConstraint("tenant_id", "phone_sha256", name="uk_sim_phone"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    phone_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    phone_enc: Mapped[str] = mapped_column(String(512), default="")
    phone_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_primary: Mapped[str] = mapped_column(String(8), default="NO")
    operator: Mapped[str] = mapped_column(String(16), default="")
    assigned_user_id: Mapped[int] = mapped_column(BigInteger, default=0)
    iccid_enc: Mapped[str] = mapped_column(String(512), default="")
    package_name: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(16), default="IN_USE")
    realname_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    activated_at: Mapped[str] = mapped_column(String(10), default="")
    monthly_rent: Mapped[str] = mapped_column(String(32), default="")
    payment_cycle: Mapped[str] = mapped_column(String(32), default="")
    next_payment_date: Mapped[str] = mapped_column(String(10), default="")
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class CollectConfig(OpsBase):
    __tablename__ = "oa_collect_config"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    config_name: Mapped[str] = mapped_column(String(128), default="")
    platform_type: Mapped[str] = mapped_column(String(32), default="", index=True)
    scope: Mapped[str] = mapped_column(String(32), default="EXTERNAL")
    account_identifier: Mapped[str] = mapped_column(String(128), default="")
    collect_enabled: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(16), default="ENABLED")
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class CollectKeyword(OpsBase):
    __tablename__ = "oa_collect_keyword"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    platform_type: Mapped[str] = mapped_column(String(32), default="", index=True)
    keyword: Mapped[str] = mapped_column(String(128), default="")
    match_type: Mapped[str] = mapped_column(String(32), default="CONTAINS")
    status: Mapped[str] = mapped_column(String(16), default="ENABLED")
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ThresholdConfig(OpsBase):
    __tablename__ = "oa_threshold_config"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    threshold_category: Mapped[str] = mapped_column(String(32), default="", index=True)
    platform_type: Mapped[str] = mapped_column(String(32), default="")
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(16), default="ENABLED")
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class CollectTask(OpsBase):
    __tablename__ = "oa_collect_task"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    task_name: Mapped[str] = mapped_column(String(128), default="")
    platform_type: Mapped[str] = mapped_column(String(32), default="", index=True)
    account_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    collect_config_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    credential_profile: Mapped[str] = mapped_column(String(64), default="default")
    method: Mapped[str] = mapped_column(String(32), default="INTERNAL")
    source: Mapped[str] = mapped_column(String(32), default="")
    data_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    frequency: Mapped[str] = mapped_column(String(32), default="DAILY")
    cron: Mapped[str] = mapped_column(String(64), default="")
    api_config_enc: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="ENABLED")
    is_unified: Mapped[int] = mapped_column(Integer, default=0)
    is_external_unified: Mapped[int] = mapped_column(Integer, default=0)
    last_run_at: Mapped[str] = mapped_column(String(32), default="")
    next_run_at: Mapped[str] = mapped_column(String(32), default="")
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    fail_count: Mapped[int] = mapped_column(Integer, default=0)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class CollectTaskMember(OpsBase):
    __tablename__ = "oa_collect_task_member"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(BigInteger, index=True)
    account_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    collect_config_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class CollectLog(OpsBase):
    __tablename__ = "oa_collect_log"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(BigInteger, index=True)
    account_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="SUCCESS")
    started_at: Mapped[str] = mapped_column(String(32), default="")
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    record_count: Mapped[int] = mapped_column(Integer, default=0)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    error_summary: Mapped[str] = mapped_column(String(512), default="")
    type_results_json: Mapped[str] = mapped_column(Text, default="[]")
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class InternalAccount(OpsBase):
    __tablename__ = "oa_internal_account"
    __table_args__ = (
        UniqueConstraint("tenant_id", "platform_type", "account_identifier", name="uk_internal_account"),
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    account_identifier: Mapped[str] = mapped_column(String(128), default="")
    account_name: Mapped[str] = mapped_column(String(128), default="")
    platform_type: Mapped[str] = mapped_column(String(32), default="", index=True)
    account_status: Mapped[str] = mapped_column(String(32), default="")
    ip_group_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    follower_count: Mapped[int] = mapped_column(BigInteger, default=0)
    content_count: Mapped[int] = mapped_column(Integer, default=0)
    last_synced_at: Mapped[str] = mapped_column(String(32), default="")
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class InternalContent(OpsBase):
    __tablename__ = "oa_internal_content"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), default="")
    account_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    account_name: Mapped[str] = mapped_column(String(128), default="")
    platform_type: Mapped[str] = mapped_column(String(32), default="", index=True)
    content_type: Mapped[str] = mapped_column(String(32), default="")
    ip_group_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    play_count: Mapped[int] = mapped_column(BigInteger, default=0)
    completion_rate: Mapped[float] = mapped_column(Float, default=0.0)
    publish_time: Mapped[str] = mapped_column(String(32), default="")
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ExternalAccount(OpsBase):
    __tablename__ = "oa_external_account"
    __table_args__ = (
        UniqueConstraint("tenant_id", "platform_type", "account_identifier", name="uk_external_account"),
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    account_identifier: Mapped[str] = mapped_column(String(128), default="")
    account_name: Mapped[str] = mapped_column(String(128), default="")
    platform_type: Mapped[str] = mapped_column(String(32), default="", index=True)
    industry: Mapped[str] = mapped_column(String(64), default="")
    ip_theme: Mapped[str] = mapped_column(String(64), default="", index=True)
    ip_group_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    follower_count: Mapped[int] = mapped_column(BigInteger, default=0)
    work_count: Mapped[int] = mapped_column(Integer, default=0)
    last_synced_at: Mapped[str] = mapped_column(String(32), default="")
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ExternalWork(OpsBase):
    __tablename__ = "oa_external_work"
    __table_args__ = (
        UniqueConstraint("tenant_id", "platform_type", "platform_work_id", name="uk_external_work"),
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    platform_work_id: Mapped[str] = mapped_column(String(64), default="")
    title: Mapped[str] = mapped_column(String(255), default="")
    account_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    account_name: Mapped[str] = mapped_column(String(128), default="")
    account_identifier: Mapped[str] = mapped_column(String(128), default="")
    platform_type: Mapped[str] = mapped_column(String(32), default="", index=True)
    content_type: Mapped[str] = mapped_column(String(32), default="")
    industry: Mapped[str] = mapped_column(String(64), default="")
    ip_theme: Mapped[str] = mapped_column(String(64), default="", index=True)
    ip_group_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    play_count: Mapped[int] = mapped_column(BigInteger, default=0)
    like_count: Mapped[int] = mapped_column(BigInteger, default=0)
    completion_rate: Mapped[float] = mapped_column(Float, default=0.0)
    publish_time: Mapped[str] = mapped_column(String(32), default="")
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class KuaishouVideo(OpsBase):
    """快手内部作品。UK：租户 + 平台账号 + video_id（重复采集更新同一行）。"""

    __tablename__ = "oa_kuaishou_video"
    __table_args__ = (UniqueConstraint("tenant_id", "account_id", "video_id", name="uk_ks_video"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(BigInteger, index=True)
    video_id: Mapped[str] = mapped_column(String(64), default="")
    title: Mapped[str] = mapped_column(String(255), default="")
    cover_url: Mapped[str] = mapped_column(String(512), default="")
    play_count: Mapped[int] = mapped_column(BigInteger, default=0)
    like_count: Mapped[int] = mapped_column(BigInteger, default=0)
    comment_count: Mapped[int] = mapped_column(BigInteger, default=0)
    share_count: Mapped[int] = mapped_column(BigInteger, default=0)
    publish_time: Mapped[str] = mapped_column(String(32), default="")
    duration_sec: Mapped[int] = mapped_column(Integer, default=0)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class DouyinVideo(OpsBase):
    """抖音内部作品。UK：租户 + 平台账号 + video_id（重复采集更新同一行）。"""

    __tablename__ = "oa_douyin_video"
    __table_args__ = (UniqueConstraint("tenant_id", "account_id", "video_id", name="uk_dy_video"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(BigInteger, index=True)
    video_id: Mapped[str] = mapped_column(String(64), default="")
    title: Mapped[str] = mapped_column(String(255), default="")
    cover_url: Mapped[str] = mapped_column(String(512), default="")
    play_count: Mapped[int] = mapped_column(BigInteger, default=0)
    like_count: Mapped[int] = mapped_column(BigInteger, default=0)
    comment_count: Mapped[int] = mapped_column(BigInteger, default=0)
    share_count: Mapped[int] = mapped_column(BigInteger, default=0)
    publish_time: Mapped[str] = mapped_column(String(32), default="")
    duration_sec: Mapped[int] = mapped_column(Integer, default=0)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class DouyinVideoSnapshot(OpsBase):
    """抖音作品日快照。同一天重复采集更新同一行。"""

    __tablename__ = "oa_douyin_video_snapshot"
    __table_args__ = (
        UniqueConstraint("tenant_id", "account_id", "video_id", "stat_date", name="uk_dy_video_snap"),
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(BigInteger, index=True)
    video_id: Mapped[str] = mapped_column(String(64), default="")
    stat_date: Mapped[str] = mapped_column(String(10), default="")
    play_count: Mapped[int] = mapped_column(BigInteger, default=0)
    like_count: Mapped[int] = mapped_column(BigInteger, default=0)
    comment_count: Mapped[int] = mapped_column(BigInteger, default=0)
    share_count: Mapped[int] = mapped_column(BigInteger, default=0)
    collected_at: Mapped[str] = mapped_column(String(32), default="")
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class DouyinFollower(OpsBase):
    """抖音粉丝列表。UK：租户 + 平台账号 + follower_id（重复采集更新同一行）。"""

    __tablename__ = "oa_douyin_follower"
    __table_args__ = (UniqueConstraint("tenant_id", "account_id", "follower_id", name="uk_dy_follower"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(BigInteger, index=True)
    follower_id: Mapped[str] = mapped_column(String(64), default="")
    nickname: Mapped[str] = mapped_column(String(128), default="")
    followed_at: Mapped[str] = mapped_column(String(32), default="")
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class DouyinFollowerDaily(OpsBase):
    """抖音粉丝日统计。同一天重复采集更新同一行。"""

    __tablename__ = "oa_douyin_follower_daily"
    __table_args__ = (UniqueConstraint("tenant_id", "account_id", "stat_date", name="uk_dy_follower_daily"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(BigInteger, index=True)
    stat_date: Mapped[str] = mapped_column(String(10), default="")
    follower_count: Mapped[int] = mapped_column(BigInteger, default=0)
    following_count: Mapped[int] = mapped_column(BigInteger, default=0)
    new_follower_count: Mapped[int] = mapped_column(BigInteger, default=0)
    collected_at: Mapped[str] = mapped_column(String(32), default="")
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class KuaishouFollowerDaily(OpsBase):
    """快手粉丝日统计。同一天重复采集更新同一行。"""

    __tablename__ = "oa_kuaishou_follower_daily"
    __table_args__ = (UniqueConstraint("tenant_id", "account_id", "stat_date", name="uk_ks_follower_daily"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(BigInteger, index=True)
    stat_date: Mapped[str] = mapped_column(String(10), default="")
    follower_count: Mapped[int] = mapped_column(BigInteger, default=0)
    following_count: Mapped[int] = mapped_column(BigInteger, default=0)
    new_follower_count: Mapped[int] = mapped_column(BigInteger, default=0)
    collected_at: Mapped[str] = mapped_column(String(32), default="")
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class KuaishouVideoSnapshot(OpsBase):
    """快手作品日快照。同一天重复采集更新同一行。"""

    __tablename__ = "oa_kuaishou_video_snapshot"
    __table_args__ = (
        UniqueConstraint("tenant_id", "account_id", "video_id", "stat_date", name="uk_ks_video_snap"),
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(BigInteger, index=True)
    video_id: Mapped[str] = mapped_column(String(64), default="")
    stat_date: Mapped[str] = mapped_column(String(10), default="")
    play_count: Mapped[int] = mapped_column(BigInteger, default=0)
    like_count: Mapped[int] = mapped_column(BigInteger, default=0)
    comment_count: Mapped[int] = mapped_column(BigInteger, default=0)
    share_count: Mapped[int] = mapped_column(BigInteger, default=0)
    collected_at: Mapped[str] = mapped_column(String(32), default="")
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
