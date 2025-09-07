import pytest
import os
import configparser
import sys

from doxydochub.server.server_config import (
    DoxyDocHubConfig,
    DoxyDocHubConfigGeneric,
    DoxyDocHubConfigServer,
    DoxyDocHubConfigData,
    VERSION as CONFIG_VERSION,
)


@pytest.fixture
def config_file(tmp_path):
    def _make_config(version="0.1.1"):
        config_path = tmp_path / "config.ini"
        config = configparser.ConfigParser()
        config[DoxyDocHubConfig.GENERIC_CFG_SECTION] = DoxyDocHubConfigGeneric(
            version
        ).to_dict()
        config[DoxyDocHubConfig.SERVER_CFG_SECTION] = DoxyDocHubConfigServer(
            "127.0.0.1", 8080, True
        ).to_dict()
        config[DoxyDocHubConfig.DATA_CFG_SECTION] = DoxyDocHubConfigData(
            "test_data", "sqlite:///test.db"
        ).to_dict()
        with open(config_path, "w") as f:
            config.write(f)
        return str(config_path)

    return _make_config


def test_server_config_properties():
    server = DoxyDocHubConfigServer("localhost", 1234, True)
    assert server.host == "localhost"
    assert server.port == 1234
    assert server.debug is True
    assert server.to_dict() == {"host": "localhost", "port": 1234, "debug": True}


def test_data_config_properties():
    data = DoxyDocHubConfigData("/tmp/data", "sqlite:///test.db")
    assert data.data_dir == "/tmp/data"
    assert data.db_url == "sqlite:///test.db"
    assert data.to_dict() == {"dir": "/tmp/data"}


def test_config_load_valid(config_file):
    cfg = DoxyDocHubConfig()
    cfg.load(config_file(version=CONFIG_VERSION))
    # The config file is loaded, but defaults are not updated by load
    assert cfg.server.host == "0.0.0.0"
    assert cfg.server.port == 8099
    assert cfg.server.debug is False
    assert cfg.data.data_dir == "data"
    assert cfg.data.db_url == "sqlite:///doxydochub.db"


def test_config_to_dict():
    cfg = DoxyDocHubConfig()
    d = cfg.to_dict()
    assert "server" in d
    assert "data" in d
    assert d["server"]["host"] == "0.0.0.0"
    assert d["server"]["port"] == 8099
    assert d["server"]["debug"] is False
    assert d["data"]["dir"] == "data"


def test_config_create_default(tmp_path):
    cfg_file = tmp_path / "default.ini"
    cfg = DoxyDocHubConfig()
    cfg.create_default_config(str(cfg_file))
    parser = configparser.ConfigParser()
    parser.read(str(cfg_file))
    assert "server" in parser.sections()
    assert "data" in parser.sections()
    assert parser["server"]["host"] == "0.0.0.0"
    assert parser["server"]["port"] == "8099"
    assert parser["server"]["debug"] == "False"
    assert parser["data"]["dir"] == "data"


def test_config_missing_file(tmp_path, monkeypatch):
    cfg = DoxyDocHubConfig()
    missing_file = tmp_path / "missing.ini"
    # Should create default config if DEFAULT_CONFIG_FILE is used
    cfg.DEFAULT_CONFIG_FILE = str(missing_file)

    with pytest.raises(FileNotFoundError):
        cfg.load(str(missing_file))


def test_config_load_invalid(monkeypatch, tmp_path):
    cfg_file = tmp_path / "bad.ini"
    config = configparser.ConfigParser()
    config["server"] = {"host": "127.0.0.1"}  # missing port and debug
    with open(cfg_file, "w") as f:
        config.write(f)
    cfg = DoxyDocHubConfig()
    with pytest.raises(RuntimeError):
        cfg.load(str(cfg_file))

    os.remove(str(cfg_file))


def test_config_validate_extra_key(tmp_path, monkeypatch):
    cfg_file = tmp_path / "extra.ini"
    config = configparser.ConfigParser()
    config["server"] = {"host": "127.0.0.1", "port": "8080", "debug": "True"}
    config["data"] = {"dir": "test_data"}
    config["extra"] = {"foo": "bar"}
    with open(cfg_file, "w") as f:
        config.write(f)
    cfg = DoxyDocHubConfig()
    with pytest.raises(RuntimeError):
        cfg.load(str(cfg_file))
    os.remove(str(cfg_file))
