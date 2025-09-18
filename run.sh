#!/bin/bash

# KeySync Mini run script

set -e

# Separate command-line arguments for sandbox and reconciliation
SANDBOX_ARGS=()
KEYSYNC_ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --sandbox)
      shift
      while [[ $# -gt 0 && "$1" != "--" ]]; do
        SANDBOX_ARGS+=("$1")
        shift
      done
      if [[ $# -gt 0 && "$1" == "--" ]]; then
        shift
      fi
      ;;
    *)
      KEYSYNC_ARGS+=("$1")
      shift
      ;;
  esac
done

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
if [ ${#SANDBOX_ARGS[@]} -gt 0 ]; then
    echo "Running sandbox command: ${SANDBOX_ARGS[*]}"
    python src/sandbox.py "${SANDBOX_ARGS[@]}"
fi

python src/keysync.py "${KEYSYNC_ARGS[@]}"

deactivate
