import pytest
import flask
from flask_restx import Api
import os
from doxydochub.api.endpoints.config_apiendpoint import DoxyDocHubApiConfigEndpoint


class DummyConfig:
    def __init__(self, file_path, config_dict):
        self.file = file_path
        self._config_dict = config_dict

    def to_dict(self):
        return self._config_dict


@pytest.fixture
def app():
    app = flask.Flask(__name__)
    api = Api(app)
    dummy_cfg = DummyConfig("dummy_config.yaml", {"foo": "bar", "baz": 123})
    DoxyDocHubApiConfigEndpoint(api, dummy_cfg)
    return app, dummy_cfg


def test_config_endpoint_returns_config(app):
    client, dummy_cfg = app
    test_client = client.test_client()
    response = test_client.get("/config/")
    assert response.status_code == 200
    assert "source" in response.json
    assert "config" in response.json
    assert response.json["source"] == os.path.abspath(str(dummy_cfg.file))
    assert response.json["config"] == dummy_cfg.to_dict()
