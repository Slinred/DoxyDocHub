import sys
import logging
import subprocess

VENV_DIR = ".venv"

def is_venv():
    return (
        hasattr(sys, 'real_prefix') or
        (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    )

def get_venv_python():
    return f"{VENV_DIR}/bin/python"

def create_venv():
    logging.info(f"Creating virtual environment in {VENV_DIR}")
    subprocess.check_call([sys.executable, "-m", "venv", VENV_DIR])

def setup_venv():
    logging.info("Installing dependencies...")
    subprocess.check_call([get_venv_python(), "-m", "pip", "install", "-r", "requirements.txt"])

    logging.info("Installing package in editable mode...")
    subprocess.check_call([get_venv_python(), "-m", "pip", "install", "-e", "."])

def main():
    logging.basicConfig(level=logging.INFO)

    if not is_venv():
        create_venv()
    
    setup_venv()

    logging.info("Environment setup complete.")

if __name__ == "__main__":
    main()
