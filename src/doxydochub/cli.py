import logging
import typing

import click

from .server.server_config import (
    DoxyDocHubConfig,
)
from .server.server import DoxyDocHubServer

VERSION = "0.1.0"


# Configure root logger once
def configure_logging(loglevel: str) -> None:
    numeric_level = getattr(logging, loglevel.upper(), None)
    if not isinstance(numeric_level, int):
        raise click.BadParameter(f"Invalid log level: {loglevel}")
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


@click.group()
@click.option(
    "--loglevel",
    default="INFO",
    show_default=True,
    help="Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).",
)
def main(loglevel: str):
    """DoxyDocHub – Host and manage Doxygen documentation archives."""
    configure_logging(loglevel)


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


@click.group()
def db():
    """Database management commands."""
    pass


@db.command("check")
def check():
    """Check the database schema version."""
    from .database.database import DoxyDocHubDatabase

    try:
        db = DoxyDocHubDatabase()
        db.validate_schema()
        click.echo(f"✅ Database schema version is up-to-date: {db.schema_version}")
    except Exception as e:
        click.echo(f"❌ Database schema validation failed: {e}")
        raise click.Abort()


@db.command("upgrade")
@click.option(
    "--db-url",
    default=None,
    help="Database URL to connect to (overrides config)",
    type=str,
)
@click.option(
    "--backup/--no-backup", default=True, help="Create a backup before upgrading."
)
def upgrade(db_url: typing.Optional[str], backup: bool):
    """Upgrade the database schema to the latest version."""
    from .database.database import DoxyDocHubDatabase

    db = DoxyDocHubDatabase(db_url=db_url)
    try:
        db.migrate(backup=backup)
        click.echo(f"✅ Database schema upgraded to version: {db.schema_version}")
    except Exception as e:
        click.echo(f"❌ Database schema upgrade failed: {e}")
        raise click.Abort()


main.add_command(db)
