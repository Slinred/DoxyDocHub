import os
import pytest
import logging
from doxydochub.database.database import DoxyDocHubDatabase

TEST_DB_FILENAME = "test_doxydochub.db"
TEST_DB_URL = f"sqlite:///{TEST_DB_FILENAME}"


@pytest.fixture
def clean_test_db():
    # Remove test DB before and after test
    if os.path.exists(TEST_DB_FILENAME):
        os.remove(TEST_DB_FILENAME)
    yield
    if os.path.exists(TEST_DB_FILENAME):
        os.remove(TEST_DB_FILENAME)
    # Remove backup files
    for fname in os.listdir("."):
        if fname.startswith("doxydochub_backup_") and fname.endswith(".db"):
            os.remove(fname)


@pytest.fixture
def capture_warning(monkeypatch):
    messages = []

    def fake_warning(msg, *args, **kwargs):
        messages.append(msg)

    monkeypatch.setattr(
        logging.getLogger("DoxyDocHubDatabase"), "warning", fake_warning
    )
    return messages


def test_default_database_url(clean_test_db):
    db = DoxyDocHubDatabase(db_url=TEST_DB_URL)
    assert db.database_url == TEST_DB_URL


def test_database_size_property(clean_test_db):
    db = DoxyDocHubDatabase(db_url=TEST_DB_URL)
    size = db.database_size
    assert "B" in size or "KB" in size


def test_schema_version_property(clean_test_db):
    db = DoxyDocHubDatabase(db_url=TEST_DB_URL)
    version = db.schema_version
    assert isinstance(version, str) or version is None


def test_validate_schema(clean_test_db):
    db = DoxyDocHubDatabase(db_url=TEST_DB_URL)
    db.validate_schema()  # Should not raise


def test_migrate_creates_backup(clean_test_db):
    db = DoxyDocHubDatabase(db_url=TEST_DB_URL)
    db.migrate(backup=True)
    backups = [
        f
        for f in os.listdir(".")
        if f.startswith("doxydochub_backup_") and f.endswith(".db")
    ]
    assert backups


def test_migrate_without_backup_warns(clean_test_db, capture_warning):
    db = DoxyDocHubDatabase(db_url=TEST_DB_URL)
    db.migrate(backup=False)
    assert any("Database backup is disabled" in msg for msg in capture_warning)


def test_session_property(clean_test_db):
    db = DoxyDocHubDatabase(db_url=TEST_DB_URL)
    session = db.session
    assert session is not None
