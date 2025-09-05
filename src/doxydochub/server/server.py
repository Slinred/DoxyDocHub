import pathlib
import sys

from flask import Flask, render_template

from .server_config import DoxyDocHubConfig
from ..database.database import DoxyDocHubDatabase


class DoxyDocHubServer:

    HTML_TEMPLATE_PATH = "templates"

    def __init__(self, config: DoxyDocHubConfig):
        from .. import __version__

        self._app = Flask(
            __name__,
            template_folder=pathlib.Path(__file__).parent / self.HTML_TEMPLATE_PATH,
        )

        self._config = config
        self._version = __version__

        self._setup_routes()

        self._db = DoxyDocHubDatabase()

    def _setup_routes(self):
        @self._app.route("/")
        def index():  # type: ignore
            return "Welcome to DoxyDocHub!"

        @self._app.route("/info")
        def info():  # type: ignore
            from ..cli import VERSION as CLI_VERSION
            from .server_config import VERSION as CONFIG_VERSION

            return render_template(
                "info.html",
                python_version=".".join(map(str, sys.version_info[:3])),
                program_version=self._version,
                db_schema_version=self._db.schema_version,
                cli_version=CLI_VERSION,
                config_version=CONFIG_VERSION,
                python_exe=sys.executable,
                work_dir=pathlib.Path.cwd(),
                config_file=self._config.file,
                data_dir=self._config.data.data_dir,
                db_url=self._db.database_url,
                db_size=self._db.database_size,
            )

    def run(self, host: str = "0.0.0.0", port: int = 8099, debug: bool = False):
        self._app.run(host=host, port=port, debug=debug)
