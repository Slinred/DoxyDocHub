import pytest
from click.testing import CliRunner
from doxydochub.cli import main


@pytest.fixture
def runner():
    return CliRunner()


def test_main_group_help(runner):
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "DoxyDocHub" in result.output


def test_version_command(monkeypatch, runner):
    monkeypatch.setattr("importlib.metadata.version", lambda pkg: "1.2.3")
    result = runner.invoke(main, ["version"])
    assert result.exit_code == 0
    assert "DoxyDocHub 1.2.3" in result.output


def test_serve_command(monkeypatch, runner):
    class DummyServerConfig:
        DEFAULT_CONFIG_FILE = "dummy.cfg"

        def load(self, path):
            assert path == "dummy.cfg"

        class server:
            host = "127.0.0.1"
            port = 8080

    class DummyServer:
        def __init__(self, cfg):
            pass

        def run(self):
            pass  # Simulate server run without actually starting it

    monkeypatch.setattr("doxydochub.cli.DoxyDocHubConfig", DummyServerConfig)
    monkeypatch.setattr("doxydochub.cli.DoxyDocHubServer", DummyServer)

    result = runner.invoke(main, ["serve", "--config", "dummy.cfg"])
    assert result.exit_code == 0
    assert "Starting DoxyDocHub at http://127.0.0.1:8080" in result.output


def test_serve_command_debug(monkeypatch, runner):
    class DummyServerConfig:
        DEFAULT_CONFIG_FILE = "dummy.cfg"

        def load(self, path):
            pass

        class server:
            host = "localhost"
            port = 5000

    class DummyServer:
        def __init__(self, cfg):
            pass

        def run(self):
            pass

    monkeypatch.setattr("doxydochub.cli.DoxyDocHubConfig", DummyServerConfig)
    monkeypatch.setattr("doxydochub.cli.DoxyDocHubServer", DummyServer)

    result = runner.invoke(main, ["serve", "--debug"])
    assert result.exit_code == 0
    assert "(debug=True)" in result.output
