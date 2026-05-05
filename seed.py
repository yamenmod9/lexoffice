from __future__ import annotations

from pathlib import Path
from runpy import run_path


def run_seed():
    seed_module_path = Path(__file__).resolve().parent / "seed" / "seed_data.py"
    namespace = run_path(str(seed_module_path))
    namespace["run_seed"]()


if __name__ == "__main__":
    run_seed()
