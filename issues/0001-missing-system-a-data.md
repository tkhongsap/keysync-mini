# Bug: Minimal config drops System A input during reconciliation

## Summary
Running the CLI with the shipped `keysync-config.yaml` leaves the comparator with no System A CSV path. The reconciliation proceeds without any source data and reports zero keys processed, which breaks the default demo experience.

## Steps to Reproduce
1. Ensure no override configuration is supplied (use the repository default `keysync-config.yaml`).
2. Generate mock inputs and run the pipeline:
   ```bash
   python src/keysync.py --generate-data --scenario normal --keys 1000 -v
   ```
3. Watch the log output during the comparison phase.

## Expected Behavior
The comparator should load `input/A.csv` (and the other generated CSVs) so a full reconciliation executes with non-zero key counts when someone runs the tool with the provided default configuration.

## Actual Behavior
* The comparator logs `System A data not found - cannot perform comparison` and the statistics block shows `total_unique_keys: 0`.
* All discrepancy counts remain zero even though discrepancies exist in the generated mock data.
* The console summary and generated reports therefore show an empty run, undermining the showcase scenario.

_Log excerpt:_
```
2025-09-17T00:45:23 - comparator - ERROR - System A data not found - cannot perform comparison
...
"total_unique_keys": 0,
"keys_in_a": 0,
"keys_in_all_systems": 0,
```

## Impact
High. Anyone following the README or `--help` guidance lands on a "successful" run with empty reports, masking the intended workflow and making the demo look broken.

## Suspected Root Cause
`Config.get_system_files()` returns an empty mapping when the YAML lacks a `sources` section. The CLI never reapplies the default CSV mapping that `Reconciler.start_reconciliation()` would normally use, so both the initial `start_reconciliation(...)` call and the subsequent `perform_reconciliation(...)` call receive `{}` and skip loading System A entirely.

## Proposed Fix
When the CLI initializes the run, reuse the same default source-map fallback that `Reconciler.start_reconciliation()` applies (e.g., detect an empty dict and substitute the default CSV paths). Alternatively, ensure `_load_config()` merges the default `sources` into the loaded YAML so `get_system_files()` always returns the CSV paths unless the user explicitly clears them.

## Environment
* Commit: ec19b368eb8d6dec9877190f753723e5b8f89744
* Python: 3.11.9
* OS: Debian GNU/Linux 12 (container)
