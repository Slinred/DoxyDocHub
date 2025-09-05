import logging
import os
import typing

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
import alembic.config
import alembic.command

import shutil
import datetime


class DoxyDocHubDatabase:

    DEFAULT_DB_URL = "sqlite:///doxydochub.db"

    ALEMBIC_DATA = os.path.join(os.path.dirname(__file__), "migrations")

    def __init__(self, db_url: typing.Optional[str] = None):

        self._logger = logging.getLogger(self.__class__.__name__)

        if not db_url:
            self._logger.warning(
                f"No database URL provided! Falling back to default SQLite database '{self.DEFAULT_DB_URL}'."
            )
            db_url = self.DEFAULT_DB_URL

        self._db_url = db_url

        self._logger.info("Initializing database...")
        self._engine = create_engine(
            self._db_url, echo=self._logger.level == logging.DEBUG, future=True
        )
        self._session = self._create_session()

        self._alembic_cfg = alembic.config.Config(
            os.path.join(self.ALEMBIC_DATA, "alembic.ini")
        )
        self._alembic_cfg.set_main_option("sqlalchemy.url", str(self._engine.url))

        self._init_empty_database()

        self.validate_schema()

    def _create_session(self):
        session = sessionmaker(bind=self._engine)
        return session()

    def _init_empty_database(self) -> None:
        if not inspect(self._engine).get_table_names():
            self._logger.info("Empty database detected! Creating database schema...")
            self.migrate(backup=False)

    @property
    def session(self):
        return self._session

    @property
    def schema_version(self) -> str | None:
        with self._engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM alembic_version"))
            version = str(result.scalar())
        return version

    @property
    def database_size(self) -> str:
        db_url = str(self._engine.url)
        if db_url.startswith("sqlite:///"):
            db_filename = db_url.replace("sqlite:///", "")
            if os.path.exists(db_filename):
                size_bytes = os.path.getsize(db_filename)
                for unit in ["B", "KB", "MB", "GB", "TB"]:
                    if size_bytes < 1024.0:
                        return f"{size_bytes:.2f} {unit}"
                    size_bytes /= 1024.0
                return f"{size_bytes:.2f} PB"
            else:
                return "0 B"
        else:
            return "N/A for non-SQLite databases"

    @property
    def database_url(self) -> str:
        return str(self._engine.url)

    def validate_schema(self) -> None:
        try:
            alembic.command.check(self._alembic_cfg)  # Alembic 1.13+
        except Exception as e:
            raise RuntimeError("Database schema is not up-to-date!") from e

    def migrate(self, backup: bool = True) -> None:
        self._logger.info("Running database migrations...")

        if self._session:
            self._session.close()

        if backup:
            backup_filename = f"doxydochub_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            db_url = str(self._engine.url)
            if db_url.startswith("sqlite:///"):
                db_filename = db_url.replace("sqlite:///", "")
                shutil.copy(db_filename, backup_filename)
                self._logger.info(f"Database backup created: {backup_filename}")
            else:
                raise RuntimeError(
                    "Database backup is only supported for SQLite databases."
                )
        else:
            self._logger.warning("Database backup is disabled! Proceed with caution.")

        self._logger.info("Applying migrations...")
        alembic.command.upgrade(self._alembic_cfg, "head")
        self._logger.info("Database migrations complete.")
