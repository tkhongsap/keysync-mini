# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Context

KeySync Mini is a mock reconciliation system that demonstrates key synchronization across multiple systems. System A is the authoritative source, while Systems B/C/D/E are downstream/peer systems that need reconciliation.

## Current Project State

This is a PRD-driven project currently in the implementation phase. The comprehensive PRDs are complete but no source code exists yet.

Key documents:
- `/keysync_mini_prd.md` - Original subsystem PRD
- `/tasks/prd-keysync-mini-mockup.md` - Detailed implementation PRD with 15 functional requirements
- `/tasks/tasks-prd-keysync-mini-mockup.md` - Task breakdown for implementation

## Development Commands

Since the project is not yet implemented, these commands will be relevant once created:

```bash
# After implementation:
python src/keysync.py                    # Run reconciliation
python src/keysync.py --dry-run         # Preview without registry updates  
python src/keysync.py --auto-approve    # Auto-activate proposed master keys
python src/mock_data_generator.py       # Generate test CSV data
python -m pytest tests/                 # Run all tests
```

## Architecture Overview

### Data Flow Pipeline
```
Extract (CSV) → Normalize → Compare → Detect Discrepancies → Propose Master Keys → Generate Reports → Audit Log
```

### Key Reconciliation Logic
1. System A is canonical/authoritative
2. Keys in B/C/D/E but not in A = "out-of-authority" (need master key provisioning)
3. Keys in A but missing from B/C/D/E = "propagation gaps"
4. Normalization applied before comparison: uppercase, trim, strip non-alphanumeric

### Expected Directory Structure
```
/keysync-mini
  /input/        # CSV files: A.csv, B.csv, C.csv, D.csv, E.csv
  /output/       # Generated reports
  /src/          # Python modules
    - keysync.py           # Main orchestration
    - normalizer.py        # Key normalization
    - comparator.py        # Comparison engine
    - provisioner.py       # Master key creation
    - reporter.py          # CSV generation
    - mock_data_generator.py
  /tests/        # Unit tests
  /data/         # SQLite DB for state
  keysync-config.yaml
  requirements.txt
```

### Output Reports
- `reconciliation_summary.csv` - High-level statistics
- `diff_missing_in_A.csv` - Keys needing master key provisioning
- `diff_missing_from_system.csv` - Keys not propagated to systems
- `master_key_registry.csv` - Registry of proposed/active master keys
- `audit_log.csv` - Detailed run history

## Configuration Schema

The system uses `keysync-config.yaml`:

```yaml
normalize:
  uppercase: true
  strip_non_alnum: true
  collapse_delims: "-"
  
provisioning:
  strategy: "mirror"  # or "namespaced"
  auto_approve: false
  
simulation:
  seed: 42
  scenario: "normal"  # normal|drift|failure|recovery
```

## Development Workflow

This project follows the PRD-driven workflow in `.cursor/rules/prd-driven-workflow/`:

1. Read PRD first: `/tasks/prd-keysync-mini-mockup.md`
2. Check task breakdown: `/tasks/tasks-prd-keysync-mini-mockup.md`
3. Implement according to the 15 functional requirements
4. Use mock data generation for testing (configurable discrepancy patterns)

## Key Implementation Requirements

1. **Python 3.8+** required
2. Dependencies: PyYAML, pandas, sqlite3 (built-in)
3. Performance target: 5,000 keys/system in <10 seconds
4. Support seed-based reproducible mock data
5. Handle missing/corrupted input files gracefully
6. Incremental mode should be 10x faster than full sync

## Testing Scenarios

The mockup must demonstrate:
- Normal operation (80% match, 10% missing each way)
- Drift scenario (gradual divergence)
- Failure scenario (50% mismatch)
- Recovery scenario (return to normal)

## Important Notes

- System A is always authoritative - never question its data
- All operations are local CSV-based (no external APIs)
- This is a mockup system - uses synthetic data only
- Focus on demonstrating the reconciliation workflow clearly
- Reports should be self-explanatory for junior developers