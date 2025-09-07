import pytest
import json
from click.testing import CliRunner
from doxydochub.cli import main

from doxydochub.server.server_config import DoxyDocHubConfig


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_main_group_help(runner: CliRunner):
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "DoxyDocHub" in result.output


def test_logging_configuration(runner: CliRunner, monkeypatch: pytest.MonkeyPatch):
    import logging

    def logging_config(level: int, **kwargs) -> None:
        assert level == logging.DEBUG

    class DummyServer:
        def __init__(self, cfg):
            pass

        def run(self) -> None:
            pass  # Simulate server run without actually starting it

    monkeypatch.setattr("doxydochub.cli.DoxyDocHubServer", DummyServer)
    monkeypatch.setattr("logging.basicConfig", logging_config)
    result = runner.invoke(main, ["--loglevel", "DEBUG", "serve"])
    assert result.exit_code == 0
    assert "DoxyDocHub" in result.output


def test_invalid_log_level(runner: CliRunner, monkeypatch: pytest.MonkeyPatch):
    class DummyServer:
        def __init__(self, cfg):
            pass

        def run(self) -> None:
            pass  # Simulate server run without actually starting it

    monkeypatch.setattr("doxydochub.cli.DoxyDocHubServer", DummyServer)
    result = runner.invoke(main, ["--loglevel", "FOO", "serve"])
    assert result.exit_code != 0
    assert "Invalid log level" in result.output


def test_version_command(monkeypatch: pytest.MonkeyPatch, runner: CliRunner):
    monkeypatch.setattr("importlib.metadata.version", lambda pkg: "1.2.3")
    result = runner.invoke(main, ["version"])
    assert result.exit_code == 0
    assert "DoxyDocHub 1.2.3" in result.output


def test_serve_command(monkeypatch: pytest.MonkeyPatch, runner: CliRunner):
    class DummyServerConfig:
        DEFAULT_CONFIG_FILE = "config.ini"

        def load(self, path: str) -> None:
            assert path == "config.ini"

        class server:
            host = "127.0.0.1"
            port = 8080

    class DummyServer:
        def __init__(self, cfg: DummyServerConfig):
            pass

        def run(self) -> None:
            pass  # Simulate server run without actually starting it

    monkeypatch.setattr("doxydochub.cli.DoxyDocHubConfig", DummyServerConfig)
    monkeypatch.setattr("doxydochub.cli.DoxyDocHubServer", DummyServer)
    result = runner.invoke(main, ["serve", "--debug"])
    assert result.exit_code == 0
    assert "(debug=True)" in result.output


def test_db_check_command(monkeypatch: pytest.MonkeyPatch, runner: CliRunner):
    class DummyDB:
        schema_version = "abc"

        def validate_schema(self) -> None:
            pass

    monkeypatch.setattr("doxydochub.database.database.DoxyDocHubDatabase", DummyDB)
    result = runner.invoke(main, ["db", "check"])
    assert result.exit_code == 0
    assert "Database schema version is up-to-date" in result.output


def test_db_check_command_failure(monkeypatch: pytest.MonkeyPatch, runner: CliRunner):
    class DummyDB:
        schema_version = "abc"

        def validate_schema(self) -> None:
            raise RuntimeError("Simulated validation error")

    monkeypatch.setattr("doxydochub.database.database.DoxyDocHubDatabase", DummyDB)
    result = runner.invoke(main, ["db", "check"])
    assert result.exit_code != 0
    assert "Database schema validation failed" in result.output


def test_db_upgrade_command(monkeypatch: pytest.MonkeyPatch, runner: CliRunner):
    class DummyDB:
        schema_version = "xyz"

        def __init__(self, db_url: str = None, validate: bool = False):
            pass

        def migrate(self, backup: bool = True) -> None:
            pass

    monkeypatch.setattr("doxydochub.database.database.DoxyDocHubDatabase", DummyDB)
    result = runner.invoke(
        main,
        ["db", "upgrade", "--db-url", "sqlite:///test.db", "--no-backup"],
    )
    assert result.exit_code == 0
    assert "Database schema upgraded to version" in result.output


def test_db_upgrade_command_failure(monkeypatch: pytest.MonkeyPatch, runner: CliRunner):
    class DummyDB:
        schema_version = "xyz"

        def __init__(self, db_url: str = None, validate: bool = False):
            pass

        def migrate(self, backup: bool = True) -> None:
            raise RuntimeError("Simulated migration error")

    monkeypatch.setattr("doxydochub.database.database.DoxyDocHubDatabase", DummyDB)
    result = runner.invoke(
        main,
        ["db", "upgrade", "--db-url", "sqlite:///test.db", "--backup"],
    )
    assert result.exit_code != 0
    assert "Simulated migration error" in result.output


def test_config_show_command(monkeypatch: pytest.MonkeyPatch, runner: CliRunner):
    class DummyConfig:
        def load(self, file: str) -> None:
            pass

        def to_dict(self) -> dict:
            return {"dir": "data"}

    # Patch the config class used by the CLI command
    monkeypatch.setattr("doxydochub.cli.DoxyDocHubConfig", DummyConfig)
    result = runner.invoke(main, ["config", "show"])
    assert result.exit_code == 0
    assert json.dumps({"dir": "data"}, indent=4) in result.output


def test_config_show_command_not_existing_file(
    monkeypatch: pytest.MonkeyPatch, runner: CliRunner
):
    # Patch the config class used by the CLI command
    monkeypatch.setattr("os.path.exists", lambda file: False)
    result = runner.invoke(main, ["config", "show"])

    assert result.exit_code == 1
    assert FileNotFoundError == type(result.exception)


def test_config_show_command_invalid_file(
    monkeypatch: pytest.MonkeyPatch, runner: CliRunner
):
    class DummyConfig:
        def load(self, file: str) -> None:
            self._validate_config()

        def _validate_config(self):
            raise ValueError("Simulated error for invalid config")

        def to_dict(self) -> dict:
            return {"dir": "data"}

    class DummyConfigParser:
        def read(file):
            pass

    # Patch the config class used by the CLI command
    monkeypatch.setattr("doxydochub.cli.DoxyDocHubConfig", DummyConfig)
    monkeypatch.setattr("configparser.ConfigParser", DummyConfigParser)
    result = runner.invoke(main, ["config", "show"])

    assert result.exit_code == 1
    assert ValueError == type(result.exception)


def test_config_validate_command(monkeypatch: pytest.MonkeyPatch, runner: CliRunner):
    class DummyConfig:
        def load(self, file: str) -> None:
            pass

    monkeypatch.setattr("doxydochub.cli.DoxyDocHubConfig", DummyConfig)
    result = runner.invoke(main, ["config", "validate"])
    assert result.exit_code == 0
    assert "Configuration file is valid" in result.output


def test_config_validate_command_invalid(
    monkeypatch: pytest.MonkeyPatch, runner: CliRunner
):
    class DummyConfig:
        def load(self, file: str) -> None:
            raise RuntimeError("Simulated error for invalid config")

    monkeypatch.setattr("doxydochub.cli.DoxyDocHubConfig", DummyConfig)
    result = runner.invoke(main, ["config", "validate"])
    assert result.exit_code == 1
    assert "Configuration validation failed" in result.output


def test_config_create_command(monkeypatch: pytest.MonkeyPatch, runner: CliRunner):
    class DummyConfig:
        def create_default_config(self, file: str) -> None:
            pass

    monkeypatch.setattr("doxydochub.cli.DoxyDocHubConfig", DummyConfig)
    result = runner.invoke(main, ["config", "create"])
    assert result.exit_code == 0
    assert "Default configuration file created" in result.output
