#!/usr/bin/env bash
set -e
source .venv/bin/activate
python -m src.pipeline
chmod +x scripts/run_pipeline.sh
