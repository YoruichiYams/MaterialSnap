"""
MaterialSnap Source Entrypoint Forwarder.
Enables running directly via `python src/main.py` or `python main.py`.
"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import main

if __name__ == "__main__":
    main.main()
