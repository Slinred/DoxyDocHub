import pathlib
import os

ALEMBIC_CFG = (
    pathlib.Path(__file__).parent.parent
    / "src"
    / "doxydochub"
    / "database"
    / "migrations"
    / "alembic.ini"
)


def main():
    import sys
    from alembic.config import Config
    from alembic import command

    if not ALEMBIC_CFG.exists():
        print(f"Error: Alembic configuration file not found at {ALEMBIC_CFG}")
        sys.exit(1)

    # Ensure the src directory is in the PYTHONPATH
    src_path = pathlib.Path(__file__).parent.parent / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

    alembic_cfg = Config(str(ALEMBIC_CFG))
    alembic_cfg.set_main_option("sqlalchemy.url", "sqlite:///test.db")

    new_revision = input("Enter a name for the new migration revision: ").strip()
    if not new_revision:
        print("Error: Revision name cannot be empty.")
        sys.exit(1)

    command.revision(alembic_cfg, autogenerate=True, message=new_revision)

    test_dir = pathlib.Path("build") / "new_db_revision"
    os.makedirs(str(test_dir), exist_ok=True)
    print(f"Testing migration in temporary directory: {test_dir.name}")
    os.chdir(str(test_dir))
    command.upgrade(alembic_cfg, "head")
    print("Migration applied successfully in the test environment.")
    command.check(alembic_cfg)
    os.remove("test.db")


if __name__ == "__main__":
    main()
