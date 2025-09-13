import pathlib
import sys
import os

from flask import Flask, render_template, send_from_directory, abort

from .server_config import DoxyDocHubConfig
from ..api.doxydochubapi import DoxyDocHubApi

from ..database.database import DoxyDocHubDatabase
from ..database.database_schema import Project, ProjectVersion


class DoxyDocHubServer:

    HTML_TEMPLATE_PATH = "templates"

    def __init__(self, config: DoxyDocHubConfig):
        from .. import __version__

        self._app = Flask(
            __name__,
            template_folder=pathlib.Path(__file__).parent / self.HTML_TEMPLATE_PATH,
            static_folder=pathlib.Path(__file__).parent / "static",
            static_url_path="/static",
        )

        self._config = config
        self._version = __version__
        self._db = DoxyDocHubDatabase(db_url=self._config.data.db_url)

        self._setup_routes()

        self._api = DoxyDocHubApi(db=self._db, server_config=self._config)
        self._api.register_api(self._app)

    def _setup_routes(self):
        @self._app.route("/")
        def index():  # type: ignore
            return render_template(
                "index.html",
                projects=self._db.session.query(Project)
                .filter(Project.parent_id == None)
                .all(),
                version=self._version,
            )

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

        @self._app.route(
            "/docs/<string:project_slug>/<string:version_slug>/<path:filename>"
        )
        def serve_docs(project_slug, version_slug, filename):
            project = (
                self._db.session.query(Project)
                .filter_by(name_slug=project_slug)
                .first()
            )
            if not project:
                abort(404, description="Project not found")

            # Look up the ProjectVersion in the DB
            version = (
                self._db.session.query(ProjectVersion)
                .filter_by(version_slug=version_slug, project_id=project.id)
                .first()
            )
            if not version or not version.storage_path:
                abort(404, description="Version not found or no docs uploaded")

            # Make sure the file exists in the storage path
            base_path = version.storage_path
            file_path = os.path.join(base_path, filename)
            if not os.path.exists(file_path):
                abort(404, description="File not found")

            return send_from_directory(base_path, filename)

    def run(self, host: str = "0.0.0.0", port: int = 8099, debug: bool = False):
        self._app.run(host=host, port=port, debug=debug)
