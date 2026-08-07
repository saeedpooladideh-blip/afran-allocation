from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import inspect

from app.database.session import Database


def test_schema_contains_required_tables(tmp_path) -> None:
    database = Database(f"sqlite:///{tmp_path / 'schema.db'}")
    database.create_schema()
    assert {
        "funds",
        "fund_navs",
        "fund_performances",
        "fund_managers",
        "fund_exposures",
        "crawl_logs",
    }.issubset(set(inspect(database.engine).get_table_names()))
    database.dispose()


def test_alembic_upgrade_creates_required_schema(tmp_path) -> None:
    database_path = tmp_path / "migration.db"
    project_root = Path(__file__).resolve().parents[1]
    environment = {
        **os.environ,
        "DATABASE_URL": f"sqlite:///{database_path}",
        "DATABASE_AUTO_CREATE": "false",
    }
    subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "alembic.ini", "upgrade", "head"],
        cwd=project_root,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    database = Database(f"sqlite:///{database_path}")
    tables = set(inspect(database.engine).get_table_names())
    assert {
        "alembic_version",
        "funds",
        "fund_navs",
        "fund_performances",
        "fund_managers",
        "fund_exposures",
        "crawl_logs",
    }.issubset(tables)
    database.dispose()
