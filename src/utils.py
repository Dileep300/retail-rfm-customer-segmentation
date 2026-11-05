"""Shared paths and helpers used by every script in the pipeline."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_FILE = ROOT / "data" / "raw" / "online_retail.xlsx"
PROCESSED = ROOT / "data" / "processed"
IMAGES = ROOT / "images"
REPORTS = ROOT / "reports"
METRICS_FILE = REPORTS / "key_metrics.json"

for folder in (PROCESSED, IMAGES, REPORTS):
    folder.mkdir(parents=True, exist_ok=True)


def save_metrics(new_metrics: dict) -> None:
    """Merge new numbers into reports/key_metrics.json.

    Every number quoted in the README is read from this file, so the README
    can never drift away from what the code actually produced.
    """
    current = {}
    if METRICS_FILE.exists():
        current = json.loads(METRICS_FILE.read_text())
    current.update(new_metrics)
    METRICS_FILE.write_text(json.dumps(current, indent=2, default=float))
