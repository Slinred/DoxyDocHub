from flask import Flask
import pytest
import os
from unittest.mock import MagicMock

from doxydochub.server.server import (
    DoxyDocHubServer,
    DoxyDocHubApi,
    DoxyDocHubDatabase,
    DoxyDocHubConfig,
)

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


class DummyConfig(DoxyDocHubConfig):
    def __init__(self):
        self._data = type(
            "Data", (), {"db_url": "sqlite:///:memory:", "data_dir": "data"}
        )()
        self._file = "config.ini"
        self.SERVER_CFG_SECTION = "server"
        self._server = type("Server", (), {"host": "0.0.0.0", "port": 8099})()


class DummyApi(DoxyDocHubApi):
    def __init__(self, **kwargs):
        pass

    def register_api(self, app: Flask):
        pass


class DummyDB(DoxyDocHubDatabase):
    def __init__(self, db_url: str | None = None, validate: bool = True):
        pass

    @property
    def session(self):
        return MagicMock()

    @property
    def schema_version(self):
        return "abc"

    @property
    def database_url(self):
        return TEST_DB_URL

    @property
    def database_size(self):
        return "1 MB"


def test_server_app_creation(monkeypatch):
    monkeypatch.setattr("doxydochub.server.server.DoxyDocHubApi", DummyApi)
    monkeypatch.setattr("doxydochub.server.server.DoxyDocHubDatabase", DummyDB)

    server = DoxyDocHubServer(DummyConfig())

    assert hasattr(server, "_app")
    assert server._app is not None


def test_server_index_route(monkeypatch):
    monkeypatch.setattr("doxydochub.server.server.DoxyDocHubApi", DummyApi)
    monkeypatch.setattr("doxydochub.server.server.DoxyDocHubDatabase", DummyDB)
    monkeypatch.setattr(
        "doxydochub.server.server.render_template",
        lambda template, **kwargs: "Welcome to DoxyDocHub!",
    )

    server = DoxyDocHubServer(DummyConfig())
    client = server._app.test_client()
    response = client.get("/")

    assert response.status_code == 200
    assert b"Welcome to DoxyDocHub!" in response.data


def test_server_info_route(monkeypatch):
    monkeypatch.setattr("doxydochub.__version__", "1.2.3")
    monkeypatch.setattr("doxydochub.server.server.DoxyDocHubApi", DummyApi)
    monkeypatch.setattr("doxydochub.server.server.DoxyDocHubDatabase", DummyDB)

    server = DoxyDocHubServer(DummyConfig())
    client = server._app.test_client()
    response = client.get("/info")

    assert response.status_code == 200
    assert b"info.html" not in response.data  # Should render template, not error
    assert b"1.2.3" in response.data
    assert b"abc" in response.data
    assert TEST_DB_URL.encode("utf-8") in response.data
