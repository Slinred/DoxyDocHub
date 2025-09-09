import logging
import pathlib

import flask
import flask_restx

from ..server.server_config import DoxyDocHubConfig
from ..database.database import DoxyDocHubDatabase

API_VERSION = "1.0"


class DoxyDocHubApi:

    API_BASE_ENDPOINT = "api"

    ENDPOINTS_DIR = pathlib.Path(__file__).parent / "endpoints"

    def __init__(self, db: DoxyDocHubDatabase, server_config: DoxyDocHubConfig):
        """
        Initialize the API.
        :param db: Instance of DoxyDocHubDatabase
        :param config: Optional config dict
        """
        self._db = db
        self._server_config = server_config or {}
        self._logger = logging.getLogger(self.__class__.__name__)
        self._bp = flask.Blueprint(
            self.API_BASE_ENDPOINT, __name__, url_prefix=f"/{self.API_BASE_ENDPOINT}"
        )
        self._api = flask_restx.Api(
            self._bp, version=API_VERSION, title="📚 DoxyDocHub API", doc="/"
        )

        self._register_endpoints()

    def _register_endpoints(self):
        from .endpoints.projects_apiendpoint import DoxyDocHubApiProjectsEndpoint
        from .endpoints.config_apiendpoint import DoxyDocHubApiConfigEndpoint
        from .endpoints.versions_apiendpoint import DoxyDocHubApiVersionsEndpoint

        DoxyDocHubApiConfigEndpoint(self._api, self._server_config)
        DoxyDocHubApiProjectsEndpoint(self._api, self._db, config=None)
        DoxyDocHubApiVersionsEndpoint(
            self._api, self._db, self._server_config, config=None
        )

    def register_api(self, app: flask.Flask):
        app.register_blueprint(self._bp)
