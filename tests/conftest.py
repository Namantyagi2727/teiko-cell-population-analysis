import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import load_data  # noqa: E402


@pytest.fixture(scope="session")
def conn():
    """
    An in-memory database built fresh from cell-count.csv, independent of
    any cell_counts.db file on disk. Keeps tests self-contained and safe to
    run before `make pipeline` has ever been run.
    """
    connection = sqlite3.connect(":memory:")
    load_data.init_db(connection)
    load_data.load_csv(connection, load_data.CSV_PATH)
    yield connection
    connection.close()
