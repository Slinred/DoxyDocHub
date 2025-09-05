import pytest
import os
import configparser
from src.DoxyDocHub.server_config import DoxyDocHubConfig

@pytest.fixture
def temp_config_file(tmp_path):
    config_path = tmp_path / "test_config.ini"
    config = configparser.ConfigParser()
    config["server"] = {"host": "127.0.0.1", "port": "8000", "debug": "true"}
    config["data"] = {"dir": "test_data"}
    with open(config_path, "w") as f:
        config.write(f)
    return str(config_path)


def test_load_valid_config(temp_config_file):
    cfg = DoxyDocHubConfig()
    loaded = cfg.load(temp_config_file)
    assert loaded["server"]["host"] == "127.0.0.1"
    assert loaded["server"]["port"] == "8000"
    assert loaded["server"]["debug"] == "true"
    assert loaded["data"]["dir"] == "test_data"


def test_load_missing_file_creates_default(tmp_path):
    config_path = tmp_path / DoxyDocHubConfig.DEFAULT_CONFIG_FILE
    cwd = os.getcwd()
    os.chdir(tmp_path)  # Change to temp directory to trigger default config creation
    cfg = DoxyDocHubConfig()
    loaded = cfg.load(str(config_path))
    os.chdir(cwd)  # Restore original working directory
    assert loaded["server"]["host"] == "0.0.0.0"
    assert loaded["server"]["port"] == "8080"
    assert loaded["server"]["debug"] == "false"
    assert loaded["data"]["dir"] == "data"


def test_load_invalid_section(tmp_path):
    config_path = tmp_path / "bad_config.ini"
    config = configparser.ConfigParser()
    config["badsection"] = {"foo": "bar"}
    with open(config_path, "w") as f:
        config.write(f)
    cfg = DoxyDocHubConfig()
    with pytest.raises(SystemExit):
        cfg.load(str(config_path))


def test_load_missing_option(tmp_path):
    config_path = tmp_path / "missing_option.ini"
    config = configparser.ConfigParser()
    config["server"] = {"host": "127.0.0.1", "port": "8000"}  # missing 'debug'
    config["data"] = {"dir": "test_data"}
    with open(config_path, "w") as f:
        config.write(f)
    cfg = DoxyDocHubConfig()
    with pytest.raises(SystemExit):
        cfg.load(str(config_path))


def test_load_unexpected_option(tmp_path):
    config_path = tmp_path / "unexpected_option.ini"
    config = configparser.ConfigParser()
    config["server"] = {"host": "127.0.0.1", "port": "8000", "debug": "true", "extra": "oops"}
    config["data"] = {"dir": "test_data"}
    with open(config_path, "w") as f:
        config.write(f)
    cfg = DoxyDocHubConfig()
    with pytest.raises(SystemExit):
        cfg.load(str(config_path))
