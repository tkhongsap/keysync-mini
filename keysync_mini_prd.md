# KeySync Mini — Subsystem PRD (Mock & Validate Logic)

## Objective
On a schedule, pull **index keys** from:
- **System A** (authoritative for keys in this test)
- **Systems B, C, D, E** (downstream/peer systems)

Compare and flag:
1. Keys in **B/C/D/E** **missing in A** (out-of-authority).
2. Keys in **A** missing in B/C/D/E (not yet propagated).

When a key exists in B/C/D/E but **not in A**, **provision a new Master Key** (per rules below) and **emit a reconciliation action**.

---

## Scope
**In:** Scheduled pulls, schema normalization, key comparison, diff classification, master key creation proposal, reports/exports, audit trail.  
**Out (for now):** No writes back to systems B–E; no semantic metadata mapping; no UI (CSV/JSON reports only).

---

## Data Contracts

### Input per system (CSV or API JSON → normalized)
- `source_system` (A|B|C|D|E)
- `source_key` (string)
- `entity_type` (optional)
- `location_ref` (optional)
- `last_seen_at` (timestamp)

### Output artifacts
1. **reconciliation_summary.csv** — counts of matches/mismatches.  
2. **diff_missing_in_A.csv** — candidate new master keys.  
3. **diff_missing_from_system.csv** — propagation gaps.  
4. **master_key_registry.csv** — local mock registry.  
5. **audit_log.csv** — change history.

---

## Matching & Provisioning Rules

1. **Exact-by-value**: System A is canonical. Match if B/C/D/E key == A key (after normalization).  
2. **Normalization**: uppercase/trim, collapse delimiters, strip non-alphanum, left-pad numbers.  
3. **Conflict handling**: duplicates flagged as exceptions.  
4. **Master key creation**:  
   - *Mirror strategy*: use normalized source key.  
   - *Namespaced*: `A-<system>-<key>`.

---

## Process Flow

1. Schedule kicks.  
2. Extract A–E keys.  
3. Normalize.  
4. Compare: find missing_in_A and missing_from_system.  
5. Detect duplicates.  
6. Propose master keys.  
7. Persist registry + write reports.  
8. Audit the run.  
9. (Optional) notify summary.

---

## Pseudocode

```pseudo
function run_keysync():
  sources = ["A","B","C","D","E"]
  tables = {}
  for s in sources:
    raw = extract(s)
    tables[s] = normalize(raw)

  setA = set(row.key for row in tables["A"])
  results = {"missing_in_A":[],"missing_from_system":[],"duplicates":[]}

  for s in ["B","C","D","E"]:
    seen = {}
    for row in tables[s]:
      key = row.key
      if key in seen:
        results["duplicates"].append({system:s, key:key})
      else:
        seen[key]=row
      if key not in setA:
        proposed = propose_master_key(s,key)
        results["missing_in_A"].append({system:s,key:key,master:proposed})

  for s in ["B","C","D","E"]:
    setS = set(r.key for r in tables[s])
    for key in setA:
      if key not in setS:
        results["missing_from_system"].append({system:s,master:key})

  write_reports(results)
  update_registry(results["missing_in_A"])
```

---

## Minimal Schema

**master_key_registry**  
- master_key (PK)  
- source_system, source_key  
- status (Proposed|Active|Deprecated)  
- created_at, updated_at  

**pull_log**  
- run_id, started_at, finished_at, status, errors  

**audit_log**  
- event_id, run_id, event_type, payload, created_at

---

## KPIs
- missing_in_A_count  
- missing_from_system_count  
- duplicate_keys_count  
- auto-approval_rate  
- run_success_rate / duration

---

## Mock Modes
- **CSV mode**: place A.csv, B.csv… in `/input`.  
- **Dry-run**: generate proposals without writing registry.  
- **Auto-approve**: flip Proposed → Active.

---

## Folder Layout

```
/keysync-mini
  /input/A.csv  B.csv  C.csv  D.csv  E.csv
  /output/reconciliation_summary.csv
          /diff_missing_in_A.csv
          /diff_missing_from_system.csv
          /master_key_registry.csv
          /audit_log.csv
  keysync-config.yaml
  run.sh
```

**keysync-config.yaml**

```yaml
schedule: "0 2 * * *"
normalize:
  uppercase: true
  strip_non_alnum: true
  collapse_delims: "-"
provisioning:
  strategy: "mirror"
  auto_approve: false
sources:
  A: { type: "csv", path: "./input/A.csv" }
  B: { type: "csv", path: "./input/B.csv" }
  C: { type: "csv", path: "./input/C.csv" }
  D: { type: "csv", path: "./input/D.csv" }
  E: { type: "csv", path: "./input/E.csv" }
```
