"""证件 S6 E2E closure 种子：水印样本与频次锁样本（幂等）。"""

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.crypto import encrypt_text, sha256_hex
from app.models import CertArchive, CertViewLog, User

E2E_CERT_HOLDER = "E2E-Cert-Watermark"
E2E_CERT_PLAIN = "110101199888011234"
E2E_CERT_FREQ_HOLDER = "E2E-Cert-Freq"
E2E_CERT_FREQ_PLAIN = "110101199777011067"


def _upsert_cert(db: Session, user: User, holder: str, plain: str) -> CertArchive | None:
    cert_hash = sha256_hex(plain)
    row = db.scalar(
        select(CertArchive).where(
            CertArchive.deleted == 0,
            CertArchive.tenant_id == 0,
            CertArchive.cert_no_hash == cert_hash,
        )
    )
    if row is not None:
        row.holder_name = holder
        row.holder_user_id = user.id
        row.status = "EFFECTIVE"
        return row
    row = CertArchive(
        holder_user_id=user.id,
        holder_name=holder,
        cert_type="IDCARD",
        cert_no_enc=encrypt_text(plain),
        cert_no_hash=cert_hash,
        issue_date="2020-01-01",
        expire_date="2030-12-31",
        status="EFFECTIVE",
        uploaded_by=user.id,
        creator=user.id,
        updater=user.id,
        tenant_id=0,
    )
    db.add(row)
    db.flush()
    return row


def ensure_cert_e2e_seed(db: Session, user: User) -> None:
    if user.username != "admin":
        return
    _upsert_cert(db, user, E2E_CERT_HOLDER, E2E_CERT_PLAIN)
    _upsert_cert(db, user, E2E_CERT_FREQ_HOLDER, E2E_CERT_FREQ_PLAIN)


def refresh_cert_e2e_seed(db: Session, user: User) -> None:
    """重建种子，并清掉这两张证在 1 小时窗口里的查看审计，避免重跑 E2E 误触 1035。"""
    ensure_cert_e2e_seed(db, user)
    hashes = [sha256_hex(E2E_CERT_PLAIN), sha256_hex(E2E_CERT_FREQ_PLAIN)]
    ids = list(
        db.scalars(
            select(CertArchive.id).where(
                CertArchive.deleted == 0,
                CertArchive.tenant_id == 0,
                CertArchive.cert_no_hash.in_(hashes),
            )
        ).all()
    )
    if ids:
        db.execute(delete(CertViewLog).where(CertViewLog.cert_id.in_(ids)))
