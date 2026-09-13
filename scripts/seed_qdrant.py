"""One-time Qdrant catalog seeding for SpaceWeave.

Run from the repository root after setting QDRANT_URL and QDRANT_API_KEY.
The script is intentionally separate from the request path so Vercel cold starts
never perform catalog indexing.
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

# Load .env when present for local development.
os.environ.setdefault("SEED_CATALOG", "false")

from app.services.vector_store import seed_collection  # noqa: E402


if __name__ == "__main__":
    count = seed_collection()
    print(f"Seeded {count} products into Qdrant.")
