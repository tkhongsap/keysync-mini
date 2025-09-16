# Product Requirements Document: KeySync Mini Mockup System

## Introduction/Overview

The KeySync Mini Mockup System is a demonstration and testing platform that simulates a multi-system key reconciliation workflow. It showcases how an authoritative system (System A) can be compared against multiple downstream/peer systems (B, C, D, E) to identify synchronization gaps, propose master keys, and generate comprehensive reconciliation reports. This mockup uses entirely synthetic data to demonstrate the complete workflow without requiring actual system integrations.

## Goals

1. **Demonstrate key reconciliation workflow** with realistic data patterns and discrepancy scenarios
2. **Validate reconciliation logic** including normalization, comparison, and master key provisioning
3. **Generate actionable reports** showing synchronization gaps and proposed remediation actions
4. **Provide a testing platform** for different synchronization scenarios and edge cases
5. **Create an audit trail** of all reconciliation runs and decisions

## User Stories

1. **As a data engineer**, I want to see how keys from multiple systems are compared and reconciled, so that I can understand the synchronization workflow.

2. **As a system architect**, I want to test different normalization and matching rules, so that I can determine the best approach for production systems.

3. **As a QA engineer**, I want to simulate various discrepancy scenarios, so that I can validate the system handles edge cases correctly.

4. **As a compliance officer**, I want to review audit logs of reconciliation runs, so that I can ensure data governance requirements are met.

5. **As a developer**, I want to generate mock data with configurable discrepancy patterns, so that I can test specific scenarios.

## Functional Requirements

1. **The system must generate mock CSV data files** for Systems A through E with configurable sizes (default: 1000-5000 keys per system)

2. **The system must implement key normalization** including:
   - Converting to uppercase
   - Trimming whitespace
   - Collapsing delimiters
   - Stripping non-alphanumeric characters
   - Left-padding numbers

3. **The system must perform exact-match comparison** between System A (authoritative) and Systems B-E after normalization

4. **The system must detect and flag the following discrepancies:**
   - Keys present in B/C/D/E but missing in A (out-of-authority)
   - Keys present in A but missing from B/C/D/E (propagation gaps)
   - Duplicate keys within the same system

5. **The system must propose master keys** for out-of-authority keys using configurable strategies:
   - Mirror strategy (default): use normalized source key
   - Namespaced strategy: prefix with system identifier

6. **The system must generate the following CSV reports:**
   - `reconciliation_summary.csv`: Statistical overview of matches/mismatches
   - `diff_missing_in_A.csv`: Keys requiring master key provisioning
   - `diff_missing_from_system.csv`: Keys not yet propagated to systems
   - `master_key_registry.csv`: Proposed and active master keys
   - `audit_log.csv`: Detailed run history with timestamps

7. **The system must support configuration via YAML file** specifying:
   - Data source paths
   - Normalization rules
   - Provisioning strategies
   - Mock data generation parameters

8. **The system must support multiple execution modes:**
   - Normal run: Full reconciliation with report generation
   - Dry-run: Preview changes without updating registry
   - Auto-approve: Automatically activate proposed master keys

9. **The system must maintain a local master key registry** tracking:
   - Master key identifiers
   - Source system and keys
   - Status (Proposed/Active/Deprecated)
   - Creation and update timestamps

10. **The system must log all significant events** including run starts/completions, errors, and key provisioning decisions

11. **The system must track temporal aspects** including last_seen_at timestamps and maintain history of keys across runs

12. **The system must support incremental reconciliation mode** comparing only changes since the last successful run

13. **The system must handle failure scenarios gracefully:**
    - Missing input files with clear error messages
    - Corrupted CSV data with row-level error reporting
    - Partial system availability (e.g., only 3 of 5 systems available)

14. **The system must provide seed-based mock data generation** for reproducible test scenarios

15. **The system must support configurable test scenarios:**
    - "normal": 80% match, 10% missing each way
    - "drift": Gradual key divergence over time
    - "failure": Sudden 50% mismatch
    - "recovery": Return to normal after failure

## Non-Goals (Out of Scope)

1. **Will NOT write data back to external systems** - all operations are local
2. **Will NOT connect to real APIs or databases** - uses only CSV files
3. **Will NOT implement real-time synchronization** - batch processing only
4. **Will NOT include a graphical user interface** - command-line execution only
5. **Will NOT handle semantic metadata mapping** - focuses on key matching only
6. **Will NOT implement data encryption or security features** - this is a mockup system

## Design Considerations

### Directory Structure
```
/keysync-mini
  /input         # Mock CSV data files
  /output        # Generated reports
  /src           # Python implementation
  /tasks         # PRD and documentation
  /tests         # Unit tests
  /data          # Historical data and state
  keysync-config.yaml
  run.sh
  requirements.txt
```

### Mock Data Patterns
- **Realistic business keys**: Mix of customer IDs (CUST-12345), product codes (PROD-ABC-789), transaction IDs (TXN-2024-001)
- **Configurable discrepancy rates**: Default 80% match, 10% missing in A, 10% missing from systems
- **Edge cases**: Duplicates, special characters, varying formats
- **Temporal patterns**: Keys with last_seen_at timestamps showing realistic update patterns

### Report Format
- CSV format for easy analysis in Excel/spreadsheets
- Clear column headers with descriptions
- Summary statistics at the top of detail reports
- ISO 8601 timestamps for all date/time fields

### Configuration Schema
```yaml
schedule: "0 2 * * *"
normalize:
  uppercase: true
  strip_non_alnum: true
  collapse_delims: "-"
  
provisioning:
  strategy: "mirror"  # mirror|namespaced
  auto_approve: false
  
sources:
  A: { type: "csv", path: "./input/A.csv" }
  B: { type: "csv", path: "./input/B.csv" }
  C: { type: "csv", path: "./input/C.csv" }
  D: { type: "csv", path: "./input/D.csv" }
  E: { type: "csv", path: "./input/E.csv" }

simulation:
  seed: 42  # For reproducible runs
  scenario: "normal"  # normal|drift|failure|recovery
  temporal:
    simulate_history: true
    days_of_history: 30
  failures:
    inject_corruption: 0.01  # 1% chance
    simulate_timeout: false
  
processing:
  mode: "full"  # full|incremental
  batch_size: 1000
  parallel: true
  checkpoint_interval: 5000
```

## Technical Considerations

1. **Language**: Python 3.8+ for broad compatibility and ease of understanding
2. **Dependencies**: 
   - PyYAML for configuration
   - pandas for data manipulation
   - sqlite3 (built-in) for state management
3. **Performance**: Should handle up to 10,000 keys per system efficiently
4. **Error Handling**: Graceful degradation with clear error messages
5. **Testing**: Unit tests for core logic (normalization, comparison, provisioning)
6. **Logging**: Structured logging to both console and file
7. **State Management**: SQLite database for tracking historical runs and key lifecycle
8. **Parallel Processing**: Process multiple systems concurrently using threading
9. **Checkpointing**: Save progress during long runs for resume capability

## Success Metrics

1. **Functional Completeness**: All 15 functional requirements implemented and tested
2. **Data Quality**: Mock data generates expected discrepancy patterns ±5%
3. **Performance**: Processes 5,000 keys per system in under 10 seconds
4. **Accuracy**: 100% accurate identification of discrepancies after normalization
5. **Usability**: Junior developer can run the system and understand reports without additional documentation
6. **Reproducibility**: Same seed produces identical mock data 100% of the time
7. **Failure Recovery**: System can resume from checkpoint within 2 seconds
8. **Incremental Efficiency**: Incremental mode 10x faster than full sync for <5% changes

## Open Questions

1. Should the system support custom normalization rules via plugins?
2. Do we need to simulate temporal aspects (keys appearing/disappearing over time)?
3. Should we add a simple REST API for viewing results programmatically?
4. Do we want to support other input formats besides CSV (JSON, XML)?
5. Should we implement basic data quality checks on input files?
6. Is there a need for real-time monitoring/alerting during long runs?
7. Should we support multiple master key provisioning strategies running in parallel?
8. Do we need to implement role-based access control for different report types?