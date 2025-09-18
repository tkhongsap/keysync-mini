# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Context

KeySync Mini is a fully implemented mock reconciliation system that demonstrates key synchronization across multiple systems. System A is the authoritative source, while Systems B/C/D/E are downstream/peer systems that need reconciliation.

## Development Commands

```bash
# Core Reconciliation
python3 src/keysync.py                                   # Run reconciliation with existing data
python3 src/keysync.py --generate-data --scenario normal --keys 1000  # Generate data and run
python3 src/keysync.py --dry-run                        # Preview without registry updates
python3 src/keysync.py --auto-approve                   # Auto-activate proposed master keys

# Web Dashboard
python3 -m webapp.app                                    # Launch dashboard at http://127.0.0.1:5000
FLASK_APP=webapp.app flask run --host=0.0.0.0 --port=5000  # Alternative launch method

# Testing
pytest tests/                                            # Run all tests
pytest tests/ --cov=src --cov-report=html              # Run with coverage report
pytest tests/test_normalizer.py                         # Run specific test file
pytest tests/test_integration.py                        # Run integration tests only
pytest -xvs tests/test_keysync_frontend.py::TestReconciliationRun::test_full_reconciliation_flow  # Run specific test

# Code Quality
black src/ tests/                                       # Format code
flake8 src/ tests/                                      # Check style
mypy src/                                               # Type checking

# Convenience Script
./run.sh                                                # Run with virtual env setup
./run.sh --generate-data --scenario drift --keys 2000  # Run with options
```

## Architecture Overview

### Core Components and Their Responsibilities

1. **keysync.py**: Main CLI entry point and orchestration
   - Handles command-line arguments via Click
   - Coordinates the entire reconciliation pipeline
   - Manages dry-run and auto-approve modes

2. **reconciler.py**: Core reconciliation orchestration
   - Coordinates the comparison → provisioning → reporting flow
   - Handles mode selection (full vs incremental)
   - Manages transaction boundaries for database operations

3. **comparator.py**: Multi-system comparison engine
   - Identifies out-of-authority keys (in B/C/D/E but not in A)
   - Detects propagation gaps (in A but missing from other systems)
   - Calculates match statistics per system

4. **normalizer.py**: Key normalization logic
   - Applies configurable rules: uppercase, trim, strip non-alphanumeric
   - Ensures consistent key format before comparison
   - Handles delimiter collapsing and whitespace normalization

5. **provisioner.py**: Master key management
   - Creates proposed master keys for out-of-authority entries
   - Supports mirror and namespaced strategies
   - Manages activation state transitions

6. **database.py**: SQLite persistence layer
   - Manages master_key_registry and audit_log tables
   - Provides checkpoint/resume capability
   - Handles transaction management

7. **webapp/app.py**: Flask dashboard
   - Interactive UI for triggering reconciliation runs
   - Real-time log streaming and report viewing
   - Statistics visualization

### Data Flow Pipeline
```
Extract (CSV) → Normalize → Compare → Detect Discrepancies → Propose Master Keys → Generate Reports → Audit Log
                    ↓                        ↓                      ↓                    ↓
              [Normalizer]            [Comparator]           [Provisioner]         [Reporter]
```

### Key Reconciliation Logic

1. **System A is Authoritative**: Always treated as the source of truth, never questioned
2. **Normalization Before Comparison**: Keys normalized using configurable rules
3. **Discrepancy Types**:
   - **Out-of-Authority**: Keys in B/C/D/E but not in A → Need master key provisioning
   - **Propagation Gaps**: Keys in A but missing from other systems → Need propagation
   - **Duplicates**: Multiple keys that normalize to the same value
4. **Master Key Strategies**:
   - **Mirror**: Use normalized key as master key
   - **Namespaced**: Prefix with system identifier (e.g., "SYSTEM_B_key123")

## PRD-Driven Development Workflow

This project follows the PRD-driven workflow in `.cursor/rules/prd-driven-workflow/`. Key documents:
- `/tasks/prd-keysync-mini-mockup.md` - Detailed PRD with 15 functional requirements
- `/tasks/tasks-prd-keysync-mini-mockup.md` - Task breakdown and implementation checklist

## Test Scenarios and Mock Data

The mock data generator supports four configurable scenarios:
- **normal**: 80% match, 10% missing in A, 10% missing from systems
- **drift**: Gradual divergence (60% match rate)
- **failure**: Sudden mismatch (50% match rate)
- **recovery**: Return to normal after failure (75% match rate)

Use `--generate-data --scenario [name] --keys [count]` to generate test data.

## Performance and Error Handling

- **Performance Target**: Process 5,000 keys/system in <10 seconds
- **Incremental Mode**: 10x faster than full sync for <5% changes
- **Error Resilience**: Handles missing files, corrupted data, partial system availability
- **Checkpoint/Resume**: SQLite-based state persistence for long runs
- **Parallel Processing**: Configurable batch size and parallel comparisons

## Output Reports

All reports generated in `output/` with ISO 8601 timestamps:
1. **reconciliation_summary.csv**: High-level statistics and match rates
2. **diff_missing_in_A.csv**: Keys requiring master key provisioning
3. **diff_missing_from_system.csv**: Keys not propagated to systems
4. **master_key_registry.csv**: Proposed and active master keys
5. **audit_log.csv**: Detailed run history with all events
6. **reconciliation_run_[N]_details.json**: JSON report with complete run data