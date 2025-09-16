#!/bin/bash

# KeySync Mini run script

set -e

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/upgrade dependencies
echo "Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Run KeySync with provided arguments
echo "Running KeySync Mini..."
python src/keysync.py "$@"

deactivate