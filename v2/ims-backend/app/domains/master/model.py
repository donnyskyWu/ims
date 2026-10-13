"""共享实体骨架。业务字段由后续批次用迁移补齐。"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, Integer, SmallInteger, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AssocBase, AuditBase
from app.db.columns import plain_id, ref_column
from app.db.refs import Ref
from app.db.types import EncryptedString


def _skeleton():
    return None


class Company(AuditBase):
    __tablename__ = "ims_org_company"
    __entity_label__ = "公司"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", "deleted", name="uq_company_code"),
        UniqueConstraint("tenant_id", "name", "deleted", name="uq_company_name"),
        UniqueConstraint("tenant_id", "credit_code", "deleted", name="uq_company_credit"),
    )
    code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    company_no: Mapped[str | None] = mapped_column(String(32), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    credit_code: Mapped[str | None] = mapped_column(String(18), nullable=True)
    legal_person: Mapped[str | None] = mapped_column(String(32), nullable=True)
    address: Mapped[str | None] = mapped_column(String(128), nullable=True)
    wx_official_capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ENABLED", info={"dict": "dict_corp_status"})
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True)


class Realname(AuditBase):
    __tablename__ = "ims_master_realname"
    __entity_label__ = "实名人"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", "deleted", name="uq_realname_code"),
        UniqueConstraint("tenant_id", "id_no_hash", "deleted", name="uq_realname_idhash"),
    )
    code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    realname_no: Mapped[str | None] = mapped_column(String(32), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    id_type: Mapped[str | None] = mapped_column(String(32), nullable=True, info={"dict": "dict_cert_type"})
    id_no_enc: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    id_no_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mobile_enc: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    mobile_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    agent_name: Mapped[str | None] = mapped_column(String(32), nullable=True)
    agent_mobile_enc: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ENABLED", info={"dict": "dict_corp_status"})
    user_id: Mapped[int | None] = ref_column(Ref("ims_sys_user", "RESTRICT", enforce_delete=False))
    company_id: Mapped[int | None] = ref_column(Ref("ims_org_company", "RESTRICT"))
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)


class SimCard(AuditBase):
    __tablename__ = "ims_master_sim_card"
    __entity_label__ = "手机卡"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", "deleted", name="uq_sim_code"),
        UniqueConstraint("tenant_id", "phone_number_hash", "deleted", name="uq_sim_phone"),
        UniqueConstraint("tenant_id", "iccid_hash", "deleted", name="uq_sim_iccid"),
    )
    code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sim_no: Mapped[str | None] = mapped_column(String(32), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    phone_number_enc: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    phone_number_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    iccid_enc: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    iccid_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    operator: Mapped[str | None] = mapped_column(String(32), nullable=True, info={"dict": "dict_sim_operator"})
    is_primary: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    realname_id: Mapped[int | None] = ref_column(Ref("ims_master_realname", "RESTRICT"))
    assigned_user_id: Mapped[int | None] = ref_column(Ref("ims_sys_user", "RESTRICT", enforce_delete=False))
    package_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    monthly_rent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    payment_cycle: Mapped[str | None] = mapped_column(String(32), nullable=True, info={"dict": "dict_payment_cycle"})
    activated_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    next_payment_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    phone_id: Mapped[int | None] = ref_column(Ref("ims_master_phone", "SET_NULL", enforce_delete=False))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ENABLED", info={"dict": "dict_corp_status"})


class Phone(AuditBase):
    __tablename__ = "ims_master_phone"
    __entity_label__ = "手机"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", "deleted", name="uq_phone_code"),
        UniqueConstraint("tenant_id", "device_no", "deleted", name="uq_phone_device_no"),
        UniqueConstraint("tenant_id", "imei", "deleted", name="uq_phone_imei"),
    )
    code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    device_no: Mapped[str | None] = mapped_column(String(32), nullable=True)
    model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    os_type: Mapped[str | None] = mapped_column(String(32), nullable=True, info={"dict": "dict_phone_os"})
    imei: Mapped[str | None] = mapped_column(String(15), nullable=True)
    custodian_user_id: Mapped[int | None] = ref_column(Ref("ims_sys_user", "RESTRICT", allow_disabled=True, enforce_delete=False))
    purchase_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    purchase_amount: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="IDLE", info={"dict": "dict_phone_status"})
    remark: Mapped[str | None] = mapped_column(String(256), nullable=True)
    sim_card_id: Mapped[int | None] = ref_column(Ref("ims_master_sim_card", "RESTRICT"))


class Cert(AuditBase):
    __tablename__ = "ims_master_cert"
    __entity_label__ = "证件"
    __table_args__ = (UniqueConstraint("tenant_id", "code", "deleted", name="uq_cert_code"),)
    code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cert_no: Mapped[str | None] = mapped_column(String(32), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    cert_type: Mapped[str | None] = mapped_column(String(32), nullable=True, info={"dict": "dict_cert_type"})
    cert_no_enc: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    cert_no_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expire_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    file_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING_REVIEW", info={"dict": "dict_cert_status"})
    realname_id: Mapped[int | None] = ref_column(Ref("ims_master_realname", "RESTRICT"))
    renew_of_cert_id: Mapped[int | None] = ref_column(Ref("ims_master_cert", "RESTRICT", enforce_delete=False))
    reviewed_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reject_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    uploaded_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    ocr_status: Mapped[str | None] = mapped_column(String(16), nullable=True)


class PlatformAccount(AuditBase):
    __tablename__ = "ims_account_platform"
    __entity_label__ = "平台账号"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", "deleted", name="uq_platform_code"),
        UniqueConstraint("tenant_id", "account_no", "deleted", name="uq_platform_account_no"),
    )
    code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    # 状态走 dict_account_status。列上不挂字典，避免既有骨架行的 ENABLED 被 1503 拦住。
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ENABLED")
    platform: Mapped[str | None] = mapped_column(String(32), nullable=True, info={"dict": "dict_platform_type"})
    realname_id: Mapped[int | None] = ref_column(Ref("ims_master_realname", "RESTRICT"))
    account_no: Mapped[str | None] = mapped_column(String(32), nullable=True)
    nickname: Mapped[str | None] = mapped_column(String(64), nullable=True)
    company_id: Mapped[int | None] = ref_column(Ref("ims_org_company", "RESTRICT"))
    sim_card_id: Mapped[int | None] = ref_column(Ref("ims_master_sim_card", "RESTRICT"))
    phone_id: Mapped[int | None] = ref_column(Ref("ims_master_phone", "RESTRICT", enforce_delete=True))
    ip_group_id: Mapped[int | None] = ref_column(Ref("ims_ipg_group", "RESTRICT", enforce_delete=False))
    # B8：author_user_id 指向作者档案，不再指向系统用户。
    author_user_id: Mapped[int | None] = ref_column(Ref("ims_master_author", "RESTRICT", enforce_delete=True))
    owner_user_id: Mapped[int | None] = ref_column(Ref("ims_sys_user", "RESTRICT", allow_disabled=True, enforce_delete=False))
    collect_bind_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    remark: Mapped[str | None] = mapped_column(String(256), nullable=True)
    recharge_total_fen: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class PersonalAccount(AuditBase):
    __tablename__ = "ims_account_personal"
    __entity_label__ = "个人账号"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", "deleted", name="uq_personal_code"),
        UniqueConstraint("tenant_id", "account_no", "deleted", name="uq_personal_account_no"),
    )
    code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ENABLED", info={"dict": "dict_common_status"})
    realname_id: Mapped[int | None] = ref_column(Ref("ims_master_realname", "RESTRICT", allow_disabled=True))
    account_no: Mapped[str | None] = mapped_column(String(32), nullable=True)
    account_type: Mapped[str | None] = mapped_column(String(32), nullable=True, info={"dict": "dict_personal_account_type"})
    nickname: Mapped[str | None] = mapped_column(String(64), nullable=True)
    owner_user_id: Mapped[int | None] = ref_column(Ref("ims_sys_user", "RESTRICT", enforce_delete=False))
    mobile_mask: Mapped[str | None] = mapped_column(String(32), nullable=True)
    mobile_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    remark: Mapped[str | None] = mapped_column(String(256), nullable=True)


class IpGroup(AuditBase):
    """IP 组。组名同时写入 name 与 group_name，兼容 B0a 骨架。"""

    __tablename__ = "ims_ipg_group"
    __entity_label__ = "IP组"
    __table_args__ = (UniqueConstraint("tenant_id", "code", "deleted", name="uq_ipg_code"),)
    code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    group_name: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    group_type: Mapped[str] = mapped_column(String(16), nullable=False, default="BIG", info={"dict": "dict_ip_group_type"})
    parent_id: Mapped[int | None] = ref_column(Ref("ims_ipg_group", "RESTRICT", enforce_delete=False))
    leader_user_id: Mapped[int | None] = ref_column(Ref("ims_sys_user", "RESTRICT", allow_disabled=True, enforce_delete=False))
    level: Mapped[str | None] = mapped_column(String(16), nullable=True, info={"dict": "dict_ip_group_level"})
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ENABLED", info={"dict": "dict_ip_group_status"})
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ding_dept_id: Mapped[str | None] = mapped_column(String(64), nullable=True)


class IpMember(AssocBase):
    """组成员。组外键沿用骨架列 group_id，接口字段仍叫 ipGroupId。"""

    __tablename__ = "ims_ipg_member"
    group_id: Mapped[int] = ref_column(Ref("ims_ipg_group", "CASCADE_SOFT"), nullable=False)
    user_id: Mapped[int | None] = ref_column(Ref("ims_sys_user", "RESTRICT", allow_disabled=True, enforce_delete=False))
    account_id: Mapped[int | None] = ref_column(Ref("ims_account_platform", "SET_NULL", enforce_delete=False))
    author_id: Mapped[int | None] = ref_column(Ref("ims_master_author", "SET_NULL", enforce_delete=False))
    position: Mapped[str | None] = mapped_column(String(32), nullable=True, info={"dict": "dict_position"})
    relation_type: Mapped[str | None] = mapped_column(String(16), nullable=True, info={"dict": "dict_member_relation"})
    is_leader: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)


class IpAnchor(AuditBase):
    """小组与作者的关联，含主作者标记。"""

    __tablename__ = "ims_ipg_anchor"
    __entity_label__ = "IP组作者"
    __table_args__ = (UniqueConstraint("tenant_id", "ip_group_id", "author_id", "deleted", name="uq_ipg_anchor"),)
    ip_group_id: Mapped[int] = ref_column(Ref("ims_ipg_group", "RESTRICT", enforce_delete=False), nullable=False)
    author_id: Mapped[int] = ref_column(Ref("ims_master_author", "RESTRICT", enforce_delete=True), nullable=False)
    anchor_type: Mapped[str | None] = mapped_column(String(32), nullable=True, info={"dict": "dict_author_type"})
    is_primary: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)


class Author(AuditBase):
    __tablename__ = "ims_master_author"
    __entity_label__ = "作者"
    __table_args__ = (UniqueConstraint("tenant_id", "code", "deleted", name="uq_author_code"),)
    code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    author_no: Mapped[str | None] = mapped_column(String(32), nullable=True)
    author_name: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    author_type: Mapped[str | None] = mapped_column(String(32), nullable=True, info={"dict": "dict_author_type"})
    ip_group_id: Mapped[int | None] = ref_column(Ref("ims_ipg_group", "RESTRICT", enforce_delete=False))
    user_id: Mapped[int | None] = ref_column(Ref("ims_sys_user", "RESTRICT", allow_disabled=True, enforce_delete=False))
    primary_account_id: Mapped[int | None] = ref_column(Ref("ims_account_platform", "RESTRICT", enforce_delete=False))
    football_author_id: Mapped[int | None] = plain_id()
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ENABLED", info={"dict": "dict_author_status"})
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True)


class LiveSession(AuditBase):
    __tablename__ = "ims_live_session"
    __entity_label__ = "场次"
    __table_args__ = (UniqueConstraint("tenant_id", "session_code", "deleted", name="uq_session_code"),)
    session_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ENABLED", info={"dict": "dict_common_status"})
    football_room_id: Mapped[int | None] = ref_column(Ref("live_room", "RESTRICT", external=True, enforce_delete=False))
    account_id: Mapped[int | None] = ref_column(Ref("ims_account_platform", "RESTRICT"))
    realname_id: Mapped[int | None] = ref_column(Ref("ims_master_realname", "RESTRICT", enforce_delete=False))
    ip_group_id: Mapped[int | None] = ref_column(Ref("ims_ipg_group", "RESTRICT", enforce_delete=False))


class CompAccount(AuditBase):
    __tablename__ = "ims_comp_account"
    __entity_label__ = "外部账号"
    __table_args__ = (UniqueConstraint("tenant_id", "code", "deleted", name="uq_comp_code"),)
    code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ENABLED", info={"dict": "dict_common_status"})
