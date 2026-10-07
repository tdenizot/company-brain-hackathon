"""Environment setup. Import this module before cognee: access control and storage paths
must be set before cognee's first call."""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

os.environ.setdefault("ENABLE_BACKEND_ACCESS_CONTROL", "true")
# Keep cognee state inside the project so a reset is just `rm -rf .cognee_*`.
os.environ.setdefault("SYSTEM_ROOT_DIRECTORY", str(ROOT / ".cognee_system"))
os.environ.setdefault("DATA_ROOT_DIRECTORY", str(ROOT / ".cognee_data"))
for _var in ("SYSTEM_ROOT_DIRECTORY", "DATA_ROOT_DIRECTORY"):
    Path(os.environ[_var]).mkdir(parents=True, exist_ok=True)
(Path(os.environ["SYSTEM_ROOT_DIRECTORY"]) / "databases").mkdir(exist_ok=True)

SAMPLE_DIR = ROOT / "data" / "sample"
RESPAN_BASE_URL = os.environ.get("RESPAN_BASE_URL", "https://api.respan.ai/api")
AGENT_MODEL = os.environ.get("AGENT_MODEL", "gpt-5-mini")
