from flask import Flask

from .server_config import DoxyDocHubConfig
from .server_data import DoxyDocHubData

class DoxyDocHubServer:
    def __init__(self, config: DoxyDocHubConfig):
        self._app = Flask(__name__)
        self._setup_routes()

        self._config = config
        self._data = DoxyDocHubData(self._config.get('data', 'dir'))

    def _setup_routes(self):
        @self._app.route('/')
        def index(): # type: ignore
            return "Welcome to DoxyDocHub!"

    def run(self, host: str = '0.0.0.0', port: int = 5000, debug: bool = True):
        self._app.run(host=host, port=port, debug=debug)
