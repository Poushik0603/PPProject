"""
main.py - Entry point for News Fetcher + Bookmark System.

Run this file to launch the application:
    py main.py
"""

import logging
import os
import sys


LOG_FORMAT = "%(asctime)s  [%(levelname)-8s]  %(name)s - %(message)s"
LOG_DATE = "%Y-%m-%d %H:%M:%S"
LOG_FILE = os.path.join(os.path.dirname(__file__), "news_fetcher.log")

logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=LOG_DATE,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)

logger = logging.getLogger("main")


def _check_python_version() -> None:
    major, minor = sys.version_info[:2]
    if (major, minor) < (3, 10):
        sys.exit(
            f"Python 3.10+ required. You are running {major}.{minor}.\n"
            "Please upgrade Python and try again."
        )
    logger.info("Python %d.%d detected - OK", major, minor)


def _check_dependencies() -> None:
    """
    Most modules are part of the Python standard library. MySQL access uses
    mysql-connector-python, which must be installed with pip.
    """
    required_stdlib = [
        "tkinter",
        "urllib",
        "json",
        "threading",
        "webbrowser",
        "logging",
        "csv",
    ]
    missing = []
    for mod in required_stdlib:
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)

    if missing:
        sys.exit(
            f"Missing standard-library modules: {', '.join(missing)}\n"
            "Ensure you have a complete Python installation."
        )

    try:
        __import__("mysql.connector")
    except ImportError:
        sys.exit(
            "Missing MySQL dependency: mysql-connector-python\n"
            "Install it with:\n"
            "    py -m pip install mysql-connector-python"
        )

    logger.info("All dependencies satisfied.")


def main() -> None:
    """
    Application entry point.
    1. Validates environment.
    2. Initialises the MySQL database.
    3. Launches the Tkinter GUI.
    """
    logger.info("=" * 60)
    logger.info("India News Desk - Starting up")
    logger.info("=" * 60)

    _check_python_version()
    _check_dependencies()

    import database
    import gui

    try:
        database.initialize_database()
        logger.info("Database ready.")
    except Exception as exc:
        logger.critical("Database initialisation failed: %s", exc)
        sys.exit(1)

    logger.info("Launching GUI...")
    try:
        app = gui.NewsFetcherApp()
        app.mainloop()
    except KeyboardInterrupt:
        logger.info("Application interrupted by user.")
    except Exception as exc:
        logger.critical("Fatal GUI error: %s", exc, exc_info=True)
        sys.exit(1)
    finally:
        logger.info("Application exited cleanly.")


if __name__ == "__main__":
    main()
