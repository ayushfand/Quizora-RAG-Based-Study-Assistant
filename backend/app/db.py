"""Database engine, session factory, and helpers.

SQLite is the default (easy to swap to Postgres by changing DATABASE_URL);
SQLite needs `check_same_thread=False` and an existing parent directory.
"""

from __future__ import annotations

from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from .config import get_settings
from .models.entities import Base


def _database_url_is_sqlite(database_url: str) -> bool:
    return database_url.startswith("sqlite")


def _ensure_sqlite_parent_dir(database_url: str) -> None:
    """Create the directory that will hold a SQLite file (no-op for :memory:)."""
    if not _database_url_is_sqlite(database_url):
        return
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        return
    db_path = database_url[len(prefix) :]
    if db_path and db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)


settings = get_settings()
_ensure_sqlite_parent_dir(settings.database_url)

if _database_url_is_sqlite(settings.database_url):
    engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
        """SQLite needs foreign keys enabled per-connection for ON DELETE CASCADE."""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

else:
    engine = create_engine(settings.database_url)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    """Create all tables if they do not exist yet, then sync added columns.

    Safe to call on every boot.
    """
    Base.metadata.create_all(bind=engine)
    _sync_sqlite_columns(engine)


def _sync_sqlite_columns(bind=None) -> None:
    """Add columns that exist in the ORM but not yet in an existing database.

    The project deliberately avoids Alembic; this additive-only sync keeps
    databases created by earlier phases working after new nullable columns are
    introduced. It never drops data, never rewrites rows, and is a no-op on a
    brand-new database or a non-SQLite backend.
    """
    bind = bind or engine
    if bind.dialect.name != "sqlite":
        return
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())
    with bind.begin() as connection:
        for table in Base.metadata.sorted_tables:
            if table.name not in existing_tables:
                continue
            existing_columns = {col["name"] for col in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in existing_columns:
                    continue
                if not column.nullable and column.server_default is None and column.default is None:
                    # Cannot safely add a required column without a default.
                    continue
                connection.execute(
                    text(f'ALTER TABLE "{table.name}" ADD COLUMN {_column_ddl(column, bind.dialect)}')
                )


def _column_ddl(column, dialect=None) -> str:
    """Render a ``column_name TYPE [DEFAULT ...]`` fragment for ALTER TABLE."""
    dialect = dialect or engine.dialect
    type_sql = column.type.compile(dialect=dialect)
    ddl = f'"{column.name}" {type_sql}'
    if column.server_default is not None and getattr(column.server_default, "arg", None) is not None:
        ddl += f" DEFAULT {column.server_default.arg}"
    return ddl


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yield a request-scoped database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ping_db() -> bool:
    """Return True when the database replies to a trivial query."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False