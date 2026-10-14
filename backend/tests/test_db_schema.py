"""Schema-drift guard and additive SQLite migration tests."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, inspect, text

from app.db import _sync_sqlite_columns, engine, init_db
from app.models.entities import Base

# The legacy attempt_answers table as created before Phase 4 (no selected_option).
_LEGACY_ATTEMPT_ANSWERS = """
CREATE TABLE attempt_answers (
    id INTEGER NOT NULL PRIMARY KEY,
    attempt_id INTEGER NOT NULL,
    question_id INTEGER NOT NULL,
    user_answer TEXT NOT NULL,
    score FLOAT,
    max_score FLOAT,
    verdict VARCHAR(32),
    covered_points JSON,
    missed_points JSON,
    feedback TEXT,
    model_answer TEXT,
    created_at DATETIME
)
"""


def test_orm_columns_exist_in_database() -> None:
    """Every mapped column must be present after init_db (catches forgotten sync)."""
    init_db()
    inspector = inspect(engine)
    for table in Base.metadata.sorted_tables:
        db_columns = {col["name"] for col in inspector.get_columns(table.name)}
        orm_columns = {col.name for col in table.columns}
        missing = orm_columns - db_columns
        assert not missing, f"table {table.name} is missing columns: {sorted(missing)}"


def test_sync_adds_missing_column_to_legacy_table(tmp_path: Path) -> None:
    """An older table without selected_option gains it on sync (add-only)."""
    legacy_engine = create_engine(f"sqlite:///{(tmp_path / 'legacy.db').as_posix()}")
    with legacy_engine.begin() as connection:
        connection.execute(text(_LEGACY_ATTEMPT_ANSWERS))
        connection.execute(
            text(
                "INSERT INTO attempt_answers (id, attempt_id, question_id, user_answer) "
                "VALUES (1, 1, 1, 'prior submission')"
            )
        )

    _sync_sqlite_columns(legacy_engine)

    columns = {col["name"] for col in inspect(legacy_engine).get_columns("attempt_answers")}
    assert "selected_option" in columns
    # Existing rows survive the additive migration.
    with legacy_engine.connect() as connection:
        rows = connection.execute(text("SELECT user_answer, selected_option FROM attempt_answers")).all()
    assert rows == [("prior submission", None)]
