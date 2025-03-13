import os
from pathlib import Path
DATA_DIR = Path.home() / ".orcallm"
LOG_DIR = DATA_DIR / "logs"
LOG_FILE = LOG_DIR / "researcher.log"
RESEARCH_DIR = DATA_DIR / "research"
CACHE_DIR = DATA_DIR / "cache"
TEMP_DIR = DATA_DIR / "temp"
FIGURE_DIR = DATA_DIR / "figures"

def setup_directories():

    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(RESEARCH_DIR, exist_ok=True)
    os.makedirs(CACHE_DIR, exist_ok=True)
    os.makedirs(TEMP_DIR, exist_ok=True)
    os.makedirs(FIGURE_DIR, exist_ok=True)

