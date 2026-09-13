import json
from pathlib import Path
from functools import lru_cache

@lru_cache(maxsize=1)
def load_catalog():
    path=Path(__file__).resolve().parents[3]/"data"/"catalog.json"
    return json.loads(path.read_text(encoding="utf-8"))
