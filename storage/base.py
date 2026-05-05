import json
from pathlib import Path
from threading import Lock

DATA_DIR = Path(__file__).parent.parent / "data"
_locks: dict = {}


def _lock(filename: str) -> Lock:
    if filename not in _locks:
        _locks[filename] = Lock()
    return _locks[filename]


def read_db(filename: str) -> list:
    path = DATA_DIR / filename
    if not path.exists():
        return []
    with _lock(filename):
        with open(path, encoding="utf-8") as f:
            return json.load(f)


def write_db(filename: str, data: list) -> None:
    with _lock(filename):
        with open(DATA_DIR / filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
