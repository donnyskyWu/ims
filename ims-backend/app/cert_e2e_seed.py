"""证件 S6 E2E closure 种子：admin 可见水印查看样本（幂等）。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crypto import encrypt_text, sha256_hex
from app.models import CertArchive, User

E2E_CERT_HOLDER = "E2E-Cert-Watermark"
E2E_CERT_PLAIN = "110101199888011234"


def ensure_cert_e2e_seed(db: Session, user: User) -> None:
    if user.username != "admin":
        return
    cert_hash = sha256_hex(E2E_CERT_PLAIN)
    row = db.scalar(
        select(CertArchive).where(
            CertArchive.deleted == 0,
            CertArchive.tenant_id == 0,
            CertArchive.cert_no_hash == cert_hash,
        )
    )
    if row is not None:
        row.holder_name = E2E_CERT_HOLDER
        row.holder_user_id = user.id
        row.status = "EFFECTIVE"
        return
    db.add(
        CertArchive(
            holder_user_id=user.id,
            holder_name=E2E_CERT_HOLDER,
            cert_type="IDCARD",
            cert_no_enc=encrypt_text(E2E_CERT_PLAIN),
            cert_no_hash=cert_hash,
            issue_date="2020-01-01",
            expire_date="2030-12-31",
            status="EFFECTIVE",
            uploaded_by=user.id,
            creator=user.id,
            updater=user.id,
            tenant_id=0,
        )
    )


def refresh_cert_e2e_seed(db: Session, user: User) -> None:
    ensure_cert_e2e_seed(db, user)
