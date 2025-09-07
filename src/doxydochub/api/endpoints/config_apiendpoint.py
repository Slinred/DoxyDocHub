import logging
import typing
import os

import flask_restx

from ...server.server_config import DoxyDocHubConfig


class DoxyDocHubApiConfigEndpoint:

    ENDPOINT = "config"

    def __init__(
        self,
        api: flask_restx.Api,
        server_cfg: DoxyDocHubConfig,
        config: typing.Optional[dict[typing.Any, typing.Any]] = None,
    ):
        """
        Initialize the config endpoint.
        :param api: Instance of flask_restx.flask_restx.Api
        :param config: server configuration
        """
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)

        ns: flask_restx.Namespace = api.namespace(
            self.ENDPOINT, description="Server configuration information"
        )

        @ns.route("/")
        class ConfigInfo(flask_restx.Resource):  # type: ignore
            """Shows the actual server configuration"""

            @ns.doc("sys_info")
            @ns.response(200, "Success")
            def get(inner_self) -> dict[str, typing.Any]:
                """Returns server configuration"""
                config_dict = {
                    "source": os.path.abspath(str(server_cfg.file)),
                    "config": server_cfg.to_dict(),
                }
                return config_dict, 200

        api.add_namespace(ns, path=f"/{self.ENDPOINT}")
