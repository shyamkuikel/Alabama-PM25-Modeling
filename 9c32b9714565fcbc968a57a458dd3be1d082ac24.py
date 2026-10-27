"""Run this study independently; accepts --workbook PATH."""
from pathlib import Path
import subprocess
import sys

if __name__ == "__main__":
    raise SystemExit(subprocess.call([sys.executable, str(Path(__file__).resolve().parents[1] / "study.py"), "--study", "7", *sys.argv[1:]]))
