from __future__ import annotations

from pathlib import Path
from runpy import run_path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None


def run_seed():
    if load_dotenv is not None:
        project_root = Path(__file__).resolve().parent
        load_dotenv(project_root / ".env")

    seed_module_path = Path(__file__).resolve().parent / "seed" / "seed_data.py"
    namespace = run_path(str(seed_module_path))
    namespace["run_seed"]()


if __name__ == "__main__":
    run_seed()
