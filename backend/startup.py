import os
import sqlite3
import subprocess
import sys
from pathlib import Path


ROOT = Path("/home/site/wwwroot")


def run(cmd: list[str]) -> None:
    print(f"[startup] {' '.join(cmd)}", flush=True)
    subprocess.check_call(cmd, cwd=ROOT)


def table_count(db_path: Path, table: str) -> int:
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    finally:
        conn.close()


def main() -> None:
    os.chdir(ROOT)

    run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "-q"])

    db_path = ROOT / "exitpoll.db"
    # Always run migrations — init_db.py uses CREATE TABLE IF NOT EXISTS (idempotente)
    run([sys.executable, "init_db.py"])

    if table_count(db_path, "centros") == 0:
        run([sys.executable, "init_showcase.py"])

    port = os.environ.get("PORT", "8000")
    os.execvp("uvicorn", ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", port])


if __name__ == "__main__":
    main()
