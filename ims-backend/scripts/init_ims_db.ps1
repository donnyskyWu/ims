# Initialize local MySQL ims + opsbiz (CREATE IF NOT EXISTS, ORM create_all, seed).
# Optional: apply db/compat/*.sql for incremental upgrades on existing DBs.
param(
    [switch]$ApplyCompat
)

$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

python -c "from app.main import init_db; init_db(); print('init_db OK')"

if ($ApplyCompat) {
    python -c @"
import glob
from pathlib import Path
from sqlalchemy import create_engine, text
from app.core import server_url, IMS_DB, OPS_DB

def run_file(path, db):
    eng = create_engine(server_url(db), pool_pre_ping=True)
    sql = Path(path).read_text(encoding='utf-8')
    stmts = [s.strip() for s in sql.split(';') if s.strip() and not s.strip().startswith('--')]
    with eng.begin() as conn:
        for stmt in stmts:
            try:
                conn.execute(text(stmt))
            except Exception as e:
                msg = str(e)
                if '1060' in msg or 'Duplicate' in msg or '1061' in msg or '1050' in msg:
                    continue
                raise

for f in sorted(Path('db/compat').glob('*.sql')):
    body = f.read_text(encoding='utf-8')
    if 'ims.' in body or 'ims_' in body:
        run_file(f, IMS_DB)
    if 'oa_' in body or 'ops.' in body:
        run_file(f, OPS_DB)
    print('compat', f.name)
"@
}
