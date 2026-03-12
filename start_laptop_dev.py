from __future__ import annotations

from pathlib import Path
import os

ROOT = Path(__file__).resolve().parent
os.environ.setdefault('II_ENV_FILE', str(ROOT / '.env.laptop_dev'))

from app import app  # noqa: E402
from ingenious_irrigation import config  # noqa: E402


if __name__ == '__main__':
    app.run(host=config.APP_HOST, port=config.APP_PORT, debug=False)
