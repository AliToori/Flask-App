import hashlib
import subprocess
import subprocess as sub
import os
from datetime import datetime

from pathlib import Path
import json
import excel2json
import pandas as pd

PROJECT_ROOT = Path(os.path.abspath(os.path.dirname(__file__)))
# Upload folder
UPLOAD_FOLDER = PROJECT_ROOT / 'uploads/'
OUTPUT_FOLDER = PROJECT_ROOT / 'output/'
BACKTESTER_CFG_BUY = UPLOAD_FOLDER / 'backtester_config_buy.json'

print(f"MAIN.py Results: {UPLOAD_FOLDER}")
print(f"MAIN.py Results: {OUTPUT_FOLDER}")
print(f"MAIN.py Results: {BACKTESTER_CFG_BUY}")
