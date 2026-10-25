import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "backend" / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "tgm_agency.db"

# Server configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Default BigQuery dataset
DEFAULT_BQ_DATASET = "tgm_reporting"
DEFAULT_BQ_TABLE = "unified_ad_performance"
