from _future_ import annotations

import sys
from pathlib import Path

ROOT = Path(__file_).resolve().parent
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from mttt.cli import main  # noqa: E402


if _name_ == "_main_":
    raise SystemExit(main())
