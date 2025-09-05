import click

from .server.server_config import (
    DoxyDocHubConfig,
)
from .server.server import DoxyDocHubServer


@click.group()
def main():
    """DoxyDocHub – Host and manage Doxygen documentation archives."""
    pass


@main.command()
@click.option(
    "--config",
    type=click.Path(readable=False),
    default=DoxyDocHubConfig.DEFAULT_CONFIG_FILE,
    help="Path to config file.",
)
@click.option("--debug", is_flag=True, help="Enable debug mode.")
def serve(config: str, debug: bool):
    """Start the DoxyDocHub web server."""

    server_cfg = DoxyDocHubConfig()
    server_cfg.load(config)

    click.echo(
        f"🚀 Starting DoxyDocHub at http://{server_cfg.server.host}:{server_cfg.server.port} (debug={debug})"
    )

    server = DoxyDocHubServer(server_cfg)
    server.run()


@main.command()
def version():
    """Show DoxyDocHub version."""
    import importlib.metadata

    version = importlib.metadata.version("doxydochub")
    click.echo(f"DoxyDocHub {version}")
