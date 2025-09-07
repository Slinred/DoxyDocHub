import pytest
import flask
from doxydochub.api.doxydochubapi import DoxyDocHubApi
from doxydochub.server.server_config import DoxyDocHubConfig
from doxydochub.database.database import DoxyDocHubDatabase


class DummyDB(DoxyDocHubDatabase):
    def __init__(self):
        pass


@pytest.fixture
def app():
    app = flask.Flask(__name__)
    db = DummyDB()
    config = DoxyDocHubConfig()
    setattr(app, "api", DoxyDocHubApi(db, config))
    app.api.register_api(app)
    return app


def test_api_blueprint_registered(app):
    # The blueprint should be registered
    assert "api" in app.blueprints


def test_api_version_and_title(app):
    # The API object should have correct version and title
    assert app.api._api.version == "1.0"
    assert app.api._api.title == "📚 DoxyDocHub API"


def test_api_base_endpoint(app):
    # The API base endpoint should be set
    api_bp = app.blueprints["api"]
    assert api_bp.url_prefix == "/api"
