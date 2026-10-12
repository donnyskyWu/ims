"""共享实体骨架。业务字段由后续批次用迁移补齐。"""
from __future__ import annotations

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AssocBase, AuditBase
from app.db.columns import plain_id, ref_column
from app.db.refs import Ref


def _skeleton():
    return None


class Company(AuditBase):
    __tablename__ = "ims_org_company"
    __entity_label__ = "公司"
    __table_args__ = (UniqueConstraint("tenant_id", "code", "deleted", name="uq_company_code"),)
    code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ENABLED", info={"dict": "dict_common_status"})


class Realname(AuditBase):
    __tablename__ = "ims_master_realname"
    __entity_label__ = "实名人"
    __table_args__ = (UniqueConstraint("tenant_id", "code", "deleted", name="uq_realname_code"),)
    code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ENABLED", info={"dict": "dict_common_status"})
    user_id: Mapped[int | None] = ref_column(Ref("ims_sys_user", "RESTRICT", enforce_delete=False))
    company_id: Mapped[int | None] = ref_column(Ref("ims_org_company", "RESTRICT"))


class SimCard(AuditBase):
    __tablename__ = "ims_master_sim_card"
    __entity_label__ = "手机卡"
    __table_args__ = (UniqueConstraint("tenant_id", "code", "deleted", name="uq_sim_code"),)
    code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ENABLED", info={"dict": "dict_common_status"})


class Phone(AuditBase):
    __tablename__ = "ims_master_phone"
    __entity_label__ = "手机"
    __table_args__ = (UniqueConstraint("tenant_id", "code", "deleted", name="uq_phone_code"),)
    code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ENABLED", info={"dict": "dict_common_status"})
    sim_card_id: Mapped[int | None] = ref_column(Ref("ims_master_sim_card", "RESTRICT"))


class Cert(AuditBase):
    __tablename__ = "ims_master_cert"
    __entity_label__ = "证件"
    __table_args__ = (UniqueConstraint("tenant_id", "code", "deleted", name="uq_cert_code"),)
    code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ENABLED", info={"dict": "dict_common_status"})
    realname_id: Mapped[int | None] = ref_column(Ref("ims_master_realname", "RESTRICT"))


class PlatformAccount(AuditBase):
    __tablename__ = "ims_account_platform"
    __entity_label__ = "平台账号"
    __table_args__ = (UniqueConstraint("tenant_id", "code", "deleted", name="uq_platform_code"),)
    code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ENABLED", info={"dict": "dict_common_status"})
    platform: Mapped[str | None] = mapped_column(String(32), nullable=True, info={"dict": "dict_platform_type"})
    realname_id: Mapped[int | None] = ref_column(Ref("ims_master_realname", "RESTRICT"))


class PersonalAccount(AuditBase):
    __tablename__ = "ims_account_personal"
    __entity_label__ = "个人账号"
    __table_args__ = (UniqueConstraint("tenant_id", "code", "deleted", name="uq_personal_code"),)
    code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ENABLED", info={"dict": "dict_common_status"})
    realname_id: Mapped[int | None] = ref_column(Ref("ims_master_realname", "RESTRICT", allow_disabled=True))


class IpGroup(AuditBase):
    __tablename__ = "ims_ipg_group"
    __entity_label__ = "IP组"
    __table_args__ = (UniqueConstraint("tenant_id", "code", "deleted", name="uq_ipg_code"),)
    code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ENABLED", info={"dict": "dict_common_status"})


class IpMember(AssocBase):
    __tablename__ = "ims_ipg_member"
    group_id: Mapped[int] = ref_column(Ref("ims_ipg_group", "CASCADE_SOFT"), nullable=False)
    user_id: Mapped[int | None] = ref_column(Ref("ims_sys_user", "RESTRICT", enforce_delete=False))
    account_id: Mapped[int | None] = ref_column(Ref("ims_account_platform", "SET_NULL", enforce_delete=False))
    author_id: Mapped[int | None] = ref_column(Ref("ims_master_author", "SET_NULL", enforce_delete=False))


class Author(AuditBase):
    __tablename__ = "ims_master_author"
    __entity_label__ = "作者"
    __table_args__ = (UniqueConstraint("tenant_id", "code", "deleted", name="uq_author_code"),)
    code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ENABLED", info={"dict": "dict_common_status"})


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
