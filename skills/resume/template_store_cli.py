from __future__ import annotations

import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from resume_runtime.template_store_cli import main


if __name__ == "__main__":
    raise SystemExit(main())
