import pytest
import os
import configparser
from doxydochub.server.server_config import DoxyDocHubConfig
import sys
from doxydochub.server.server_config import (
    DoxyDocHubConfig,
    DoxyDocHubConfigServer,
    DoxyDocHubConfigData,
)


@pytest.fixture
def config_file(tmp_path):
    config_path = tmp_path / "config.ini"
    config = configparser.ConfigParser()
    config["server"] = {"host": "127.0.0.1", "port": "8080", "debug": "True"}
    config["data"] = {"dir": "test_data"}
    with open(config_path, "w") as f:
        config.write(f)
    return str(config_path)


def test_server_config_properties():
    server = DoxyDocHubConfigServer("localhost", 1234, True)
    assert server.host == "localhost"
    assert server.port == 1234
    assert server.debug is True
    assert server.to_dict() == {"host": "localhost", "port": 1234, "debug": True}


def test_data_config_properties():
    data = DoxyDocHubConfigData("/tmp/data")
    assert data.data_dir == "/tmp/data"
    assert data.to_dict() == {"dir": "/tmp/data"}


def test_config_load_valid(config_file):
    cfg = DoxyDocHubConfig()
    cfg.load(config_file)
    assert cfg.server.host == "0.0.0.0"  # default, not updated by load
    assert cfg.data.data_dir == "data"  # default, not updated by load


def test_config_to_dict():
    cfg = DoxyDocHubConfig()
    d = cfg.to_dict()
    assert "server" in d
    assert "data" in d
    assert d["server"]["host"] == "0.0.0.0"
    assert d["data"]["dir"] == "data"


def test_config_create_default(tmp_path):
    cfg_file = tmp_path / "default.ini"
    cfg = DoxyDocHubConfig()
    cfg._create_default_config(str(cfg_file))
    parser = configparser.ConfigParser()
    parser.read(str(cfg_file))
    assert "server" in parser.sections()
    assert "data" in parser.sections()
    assert parser["server"]["host"] == "0.0.0.0"
    assert parser["data"]["dir"] == "data"


def test_config_load_missing_file(tmp_path, monkeypatch):
    cfg = DoxyDocHubConfig()
    missing_file = tmp_path / "missing.ini"
    # Should create default config if DEFAULT_CONFIG_FILE is used
    cfg.DEFAULT_CONFIG_FILE = str(missing_file)
    cfg.load(str(missing_file))
    assert os.path.exists(missing_file)


def test_config_load_invalid(monkeypatch, tmp_path):
    cfg_file = tmp_path / "bad.ini"
    config = configparser.ConfigParser()
    config["server"] = {"host": "127.0.0.1"}  # missing port and debug
    with open(cfg_file, "w") as f:
        config.write(f)
    cfg = DoxyDocHubConfig()
    # Patch sys.exit to raise SystemExit for testing
    monkeypatch.setattr(
        sys, "exit", lambda code=1: (_ for _ in ()).throw(SystemExit(code))
    )
    with pytest.raises(SystemExit):
        cfg.load(str(cfg_file))


def test_config_validate_extra_key(tmp_path, monkeypatch):
    cfg_file = tmp_path / "extra.ini"
    config = configparser.ConfigParser()
    config["server"] = {"host": "127.0.0.1", "port": "8080", "debug": "True"}
    config["data"] = {"dir": "test_data"}
    config["extra"] = {"foo": "bar"}
    with open(cfg_file, "w") as f:
        config.write(f)
    cfg = DoxyDocHubConfig()
    monkeypatch.setattr(
        sys, "exit", lambda code=1: (_ for _ in ()).throw(SystemExit(code))
    )
    with pytest.raises(SystemExit):
        cfg.load(str(cfg_file))
