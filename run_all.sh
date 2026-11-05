#!/usr/bin/env bash
# Runs the whole pipeline from the raw file to the charts. Stops at the first error.
set -euo pipefail
cd "$(dirname "$0")/src"
python 01_clean.py
python 02_eda.py
python 03_rfm_segmentation.py
python 04_holdout_validation.py
echo "Done. See ../reports and ../images"
