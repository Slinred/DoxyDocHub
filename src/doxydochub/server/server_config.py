import configparser
import os
import logging
import sys


class DoxyDocHubConfigServer:
    def __init__(self, host: str, port: int, debug: bool) -> None:
        self._host = host
        self._port = port
        self._debug = debug

    @property
    def host(self) -> str:
        return self._host

    @property
    def port(self) -> int:
        return self._port

    @property
    def debug(self) -> bool:
        return self._debug

    def to_dict(self) -> dict[str, str | int | bool]:
        return {"host": self._host, "port": self._port, "debug": self._debug}


class DoxyDocHubConfigData:
    def __init__(self, data_dir: str) -> None:
        self._data_dir = data_dir

    @property
    def data_dir(self) -> str:
        return self._data_dir

    def to_dict(self) -> dict[str, str | int | bool]:
        return {"dir": self._data_dir}


class DoxyDocHubConfig:
    DEFAULT_CONFIG_FILE = "config.ini"

    DATA_CFG_SECTION = "data"
    SERVER_CFG_SECTION = "server"

    def __init__(self):
        self._logger = logging.getLogger(self.__class__.__name__)
        self._config_parser = configparser.ConfigParser()

        self._server = DoxyDocHubConfigServer("0.0.0.0", 8099, False)
        self._data = DoxyDocHubConfigData("data")

        self._config = {}

    @property
    def server(self) -> DoxyDocHubConfigServer:
        return self._server

    @property
    def data(self) -> DoxyDocHubConfigData:
        return self._data

    def load(self, file: str) -> None:
        self._logger.info(f"Loading configuration from {file}...")

        if not os.path.exists(file) and self.DEFAULT_CONFIG_FILE != file:
            self._error_and_exit(f"Configuration file '{file}' not found.")

        if not os.path.exists(file) and self.DEFAULT_CONFIG_FILE == file:
            self._create_default_config(file)

        self._config_parser.read(file)

        try:
            self._validate_config()
        except ValueError as e:
            self._error_and_exit(f"Configuration error in {file}: {e}")

    def _error_and_exit(self, message: str):
        self._logger.error(message)
        sys.exit(1)

    def _create_default_config(self, file: str):
        self._logger.info(f"Creating default configuration at {file}...")

        config = configparser.ConfigParser()
        self_dict = self.to_dict()
        for section in self_dict.keys():
            options = self_dict[section].items()
            config[section] = {k: str(o) for k, o in options}
        with open(file, "w") as configfile:
            config.write(configfile)

        self._logger.info(f"Default configuration created at {file}")

    def _validate_config(self):
        self._logger.info("Validating configuration...")
        path = ""
        invalid_keys: list[str] = self._config_parser.sections()

        self_dict = self.to_dict()

        for key in self_dict.keys():

            if key not in self._config_parser.sections():
                raise ValueError(f"Missing key '{path + key}' in loaded config")
            invalid_keys.remove(key)

            invalid_items: list[str] = list(self._config_parser[key].keys())
            for item in self_dict[key]:
                if item not in self._config_parser[key]:
                    raise ValueError(
                        f"Missing key '{path + key}.{item}' in loaded config"
                    )
                invalid_items.remove(item)

            if len(invalid_items) > 0:
                raise ValueError(f"Unexpected key '{path + key}' in loaded config")
        if len(invalid_keys) > 0:
            raise ValueError(
                f"Unexpected key '{path + invalid_keys[0]}' in loaded config"
            )

        self._logger.info("Configuration is valid.")

    def to_dict(self) -> dict[str, dict[str, str | int | bool]]:
        return {
            self.SERVER_CFG_SECTION: self._server.to_dict(),
            self.DATA_CFG_SECTION: self._data.to_dict(),
        }
