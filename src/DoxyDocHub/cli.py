import argparse
import logging
import sys

from .server_config import DoxyDocHubConfig
from .server import DoxyDocHubServer

class DoxyDocHubCli:
    def __init__(self):
        self._logger = logging.getLogger(self.__class__.__name__)

        self.parser = argparse.ArgumentParser(description="DoxyDocHub CLI")
        self.parser.add_argument(
            "--config",
            type=str,
            default=DoxyDocHubConfig.DEFAULT_CONFIG_FILE,
            help="Path to the configuration file",
        )
        self.subparsers = self.parser.add_subparsers(dest="command")

        # Add commands here
        self.subparsers.add_parser("start", help="Start the DoxyDocHub server")
        self.subparsers.add_parser("stop", help="Stop the DoxyDocHub server")

        self._server: DoxyDocHubServer|None = None

    def run(self):
        args = self.parser.parse_args()

        config = DoxyDocHubConfig()
        config.load(args.config)
        

        if args.command == "start":
            self._logger.info("Starting the DoxyDocHub server...")
            self._server = DoxyDocHubServer(config)
            self._server.run()
        elif args.command == "stop":
            self._logger.info("Stopping the DoxyDocHub server...")
            pass  # Stop the server
        else:
            self.parser.print_help()

    def _error_and_exit(self, message: str):
        self._logger.error(message)
        sys.exit(1)

def main():
    cli = DoxyDocHubCli()
    cli.run()

if __name__ == "__main__":
    main()