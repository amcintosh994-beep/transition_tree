from __future__ import annotations
import sys
from pathlib import Path

# Make src/ importable without editable install
_ROOT = Path(__file__).resolve().parent
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from mttt.pipeline import *  # noqa: F401,F403
