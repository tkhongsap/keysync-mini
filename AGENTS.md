# Repository Guidelines

## Project Structure & Module Organization
The reconciliation engine lives in `src/`, with modules separated by responsibility (`normalizer.py`, `comparator.py`, `provisioner.py`, etc.). Keep new orchestration code near `keysync.py` and share helpers through package-level utilities. The Flask dashboard is under `webapp/` (`webapp/app.py`, templates, and static assets) and reads the same configuration as the CLI. Tests reside in `tests/` alongside integration coverage. Sample CSV inputs belong in `input/`; generated reports and diagnostics write to `output/` and should stay out of version control. Use `run.sh` when you need a scripted end-to-end run.

## Build, Test, and Development Commands
Create a virtual environment and install dependencies with `python3 -m venv venv && source venv/bin/activate` followed by `pip install -r requirements.txt`. Run the CLI via `python src/keysync.py --generate-data --scenario normal` or `./run.sh` for the common workflow. Launch the dashboard locally with `python -m webapp.app` (or `FLASK_APP=webapp.app flask run`). Use `python src/keysync.py --help` whenever you add flags to verify the public interface.

## Coding Style & Naming Conventions
Follow Black-formatted Python (88 character lines, 4-space indentation). Prefer explicit type hints and module-level loggers (`logger = get_logger(__name__)`) for new code. Functions, variables, and modules use `snake_case`; classes use `PascalCase`. Keep docstrings and Click option help concise, mirroring existing modules. Align data file names with the authoritative system labels (`A.csv`–`E.csv`).

## Testing Guidelines
All tests run through `pytest`. Target unit coverage in `tests/test_*.py` and keep scenario checks inside `test_integration.py`. Validate new behaviors with `pytest tests/ --cov=src --cov-report=term-missing` and include regression-focused fixtures when touching normalization or comparator logic. When modifying the dashboard, extend `test_keysync_frontend.py` to capture UI-triggered flows.

## Commit & Pull Request Guidelines
Commit subjects stay short, present-tense, and imperative ("Fix dashboard imports"). Optional scopes like `docs:` or `build:` align with the current history. Group related changes into a single commit, and update docs or config samples in the same change. Pull requests should link relevant issues, describe the reconciliation scenario exercised, and include before/after notes or screenshots for UI adjustments. Mention any skipped tests or configuration impacts explicitly.

## Security & Configuration Tips
Treat `keysync-config.yaml` as a template: place environment-specific overrides in untracked copies and never commit secrets or production endpoints. Keep generated CSVs and SQLite files confined to `output/`. When sharing sample data, scrub customer identifiers and rely on `--generate-data` to reproduce scenarios. Review logging levels before merging to avoid verbose production runs.
