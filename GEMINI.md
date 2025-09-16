# Gemini Code Assistant Context

This document provides context for the Gemini Code Assistant to understand the KeySync Mini project.

## Project Overview

KeySync Mini is a Python-based command-line tool that demonstrates and tests multi-system key reconciliation workflows. It simulates a scenario where an authoritative system (System A) is compared against multiple downstream/peer systems (B, C, D, E) to identify synchronization gaps, propose master keys, and generate comprehensive reconciliation reports.

The project is well-structured, with separate modules for different functionalities:

*   **`src/keysync.py`**: The main entry point of the application, using `click` for command-line argument parsing.
*   **`src/config.py`**: Manages the application configuration from a YAML file (`keysync-config.yaml`).
*   **`src/database.py`**: Handles the SQLite database for storing run history, master keys, and audit logs.
*   **`src/mock_data_generator.py`**: Generates synthetic test data with configurable discrepancy patterns.
*   **`src/normalizer.py`**: Applies consistent formatting rules across all systems.
*   **`src/comparator.py`**: Compares the data from different systems to identify discrepancies.
*   **`src/reconciler.py`**: Orchestrates the entire reconciliation process.
*   **`src/provisioner.py`**: Manages the creation of master keys for unrecognized entries.
*   **`src/reporter.py`**: Generates CSV reports with detailed reconciliation results.
*   **`tests/`**: Contains unit and integration tests for the project.

## Building and Running

The project uses a `requirements.txt` file to manage dependencies.

**Installation:**

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Running the application:**

The main application can be run using `src/keysync.py`.

```bash
# Generate mock data and run reconciliation
python src/keysync.py --generate-data --scenario normal --keys 1000

# Run with existing data
python src/keysync.py

# Dry-run mode (preview without changes)
python src/keysync.py --dry-run

# Auto-approve mode (activate master keys automatically)
python src/keysync.py --auto-approve
```

A convenience script `run.sh` is also provided.

```bash
# Make script executable
chmod +x run.sh

# Run with default settings
./run.sh

# Run with options
./run.sh --generate-data --scenario drift --keys 2000
```

**Running tests:**

The project uses `pytest` for testing.

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

## Development Conventions

*   **Configuration:** The application is configured through the `keysync-config.yaml` file.
*   **Code Style:** The project uses `black` for code formatting, `flake8` for linting, and `mypy` for type checking.
*   **Testing:** The project has a `tests` directory with unit and integration tests. `pytest` is the test runner.
*   **Database:** A SQLite database is used for persistence.
*   **Command-line Interface:** The `click` library is used to create the command-line interface.
