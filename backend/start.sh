#!/usr/bin/env bash
set -e

pip install -r requirements.txt
gunicorn -b 0.0.0.0:${PORT} run:app
