"""
main.py - Entry point for the simplified news fetcher project.

Run:
    py main.py
"""

import logging
import sys

import database
import gui


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)


def main() -> None:
    if sys.version_info < (3, 10):
        raise SystemExit("Python 3.10 or newer is required.")

    database.initialize_database()
    app = gui.NewsFetcherApp()
    app.mainloop()


if __name__ == "__main__":
    main()
