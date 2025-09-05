import pytest
import sys
from unittest import mock
from src.DoxyDocHub import DoxyDocHubCli

class DummyConfig:
    DEFAULT_CONFIG_FILE = 'dummy.cfg'
    def load(self, path):
        self.loaded_path = path

class DummyServer:
    def __init__(self, config):
        self.config = config
        self.ran = False
    def run(self):
        self.ran = True

@pytest.fixture(autouse=True)
def patch_dependencies(monkeypatch):
    monkeypatch.setattr('src.DoxyDocHub.cli.DoxyDocHubConfig', DummyConfig)
    monkeypatch.setattr('src.DoxyDocHub.cli.DoxyDocHubServer', DummyServer)


def test_cli_start(monkeypatch):
    test_args = ['prog', 'start', '--config', 'test.cfg']
    monkeypatch.setattr(sys, 'argv', test_args)
    cli = DoxyDocHubCli()
    cli.run()
    assert isinstance(cli._server, DummyServer)
    assert cli._server.ran
    assert cli._server.config.loaded_path == 'test.cfg'


def test_cli_stop(monkeypatch):
    test_args = ['prog', 'stop']
    monkeypatch.setattr(sys, 'argv', test_args)
    cli = DoxyDocHubCli()
    cli.run()
    assert cli._server is None


def test_cli_no_command(monkeypatch):
    test_args = ['prog']
    monkeypatch.setattr(sys, 'argv', test_args)
    cli = DoxyDocHubCli()
    with mock.patch.object(cli.parser, 'print_help') as mock_help:
        cli.run()
        mock_help.assert_called_once()


def test_error_and_exit(monkeypatch):
    cli = DoxyDocHubCli()
    with mock.patch('sys.exit') as mock_exit:
        cli._error_and_exit('fail')
        mock_exit.assert_called_once()
