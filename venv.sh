#!/bin/bash
# Check if the script is being sourced
(return 0 2>/dev/null) && SOURCED=1 || SOURCED=0

if [ "$SOURCED" -eq 0 ]; then
    echo "Please run this script with: source $0"
    exit 1
fi

python3 -m venv ./.venv
source ./.venv/bin/activate  # macOS/Linux
pip install -r requirements.txt