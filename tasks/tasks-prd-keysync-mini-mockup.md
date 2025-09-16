# Task List for KeySync Mini Mockup System

## Relevant Files

- `/tasks/prd-keysync-mini-mockup.md` - Comprehensive PRD with 15 functional requirements
- `/keysync_mini_prd.md` - Original subsystem PRD
- `keysync-config.yaml` - Configuration file (to be created)

## Primary Tasks

### Phase 1: Foundation
- [ ] 1.0 Set up project infrastructure and dependencies
  - [ ] 1.1 Create directory structure (/input, /output, /src, /tests, /data)
  - [ ] 1.2 Create requirements.txt (PyYAML, pandas, pytest, click for CLI interface)
  - [ ] 1.3 Initialize SQLite schema for state management
  - [ ] 1.4 Set up logging configuration
  - [ ] 1.5 Create run.sh script

### Phase 2: Data Generation & Scenarios
- [ ] 2.0 Implement mock data generation system
  - [ ] 2.1 Create seed-based reproducible data generator (FR14)
  - [ ] 2.2 Implement configurable test scenarios (normal/drift/failure/recovery) (FR15)
  - [ ] 2.3 Generate temporal patterns with last_seen_at timestamps (FR11)
  - [ ] 2.4 Create realistic business key patterns (CUST-, PROD-, TXN-)
  - [ ] 2.5 Implement controlled discrepancy injection (default: 80% match, 10% missing in A, 10% missing from systems)
  - [ ] 2.6 Add duplicate key generation for testing

### Phase 3: Core Processing Engine
- [ ] 3.0 Build key normalization and comparison engine
  - [ ] 3.1 Implement normalization rules (uppercase, trim, strip, collapse, pad) (FR2)
  - [ ] 3.2 Create exact-match comparison logic (FR3)
  - [ ] 3.3 Add parallel processing with threading (Technical Spec)
  - [ ] 3.4 Implement batch processing for large datasets

### Phase 4: Reconciliation & Detection
- [ ] 4.0 Develop reconciliation logic and discrepancy detection
  - [ ] 4.1 Detect keys missing in A (out-of-authority) (FR4)
  - [ ] 4.2 Detect keys missing from B/C/D/E (propagation gaps) (FR4)
  - [ ] 4.3 Implement duplicate key detection within systems (FR4)
  - [ ] 4.4 Create master key provisioning logic (mirror/namespaced) (FR5)
  - [ ] 4.5 Build incremental reconciliation mode (FR12)
  - [ ] 4.6 Add run-to-run comparison capabilities

### Phase 5: Reporting & Audit
- [ ] 5.0 Create report generation and output management
  - [ ] 5.1 Generate reconciliation_summary.csv with ISO 8601 timestamps and summary statistics (FR6)
  - [ ] 5.2 Create diff_missing_in_A.csv with master key proposals, ISO 8601 timestamps, and clear headers (FR6)
  - [ ] 5.3 Generate diff_missing_from_system.csv with ISO 8601 timestamps and clear column headers (FR6)
  - [ ] 5.4 Build master_key_registry.csv management with ISO 8601 timestamps for creation/updates (FR6, FR9)
  - [ ] 5.5 Implement comprehensive audit_log.csv with ISO 8601 timestamps and detailed run history (FR6, FR10)
  - [ ] 5.6 Add trend analysis reporting (optional: track discrepancy rates over time, key lifecycle patterns)

### Phase 6: State & Configuration
- [ ] 6.0 Implement configuration and state management
  - [ ] 6.1 Create YAML configuration loader supporting schedule, normalize rules, provisioning strategies, sources, simulation (seed, scenario, temporal, failures), and processing options (mode, batch_size, parallel, checkpoint_interval) (FR7)
  - [ ] 6.2 Build SQLite-based state persistence (FR9, FR11)
  - [ ] 6.3 Implement checkpoint/resume capability (Technical Spec)
  - [ ] 6.4 Track historical runs and key lifecycle (FR11)
  - [ ] 6.5 Manage master key registry with status tracking (FR9)

### Phase 7: CLI & Execution
- [ ] 7.0 Add CLI interface and execution modes
  - [ ] 7.1 Implement normal run mode (FR8)
  - [ ] 7.2 Add dry-run mode (preview without registry updates) (FR8)
  - [ ] 7.3 Create auto-approve mode for master keys (FR8)
  - [ ] 7.4 Add incremental vs full mode selection (FR12)
  - [ ] 7.5 Implement graceful error handling (FR13)

### Phase 8: Resilience & Error Handling
- [ ] 8.0 Implement failure resilience and recovery
  - [ ] 8.1 Handle missing input files gracefully (FR13)
  - [ ] 8.2 Add corrupted CSV data detection and reporting (FR13)
  - [ ] 8.3 Support partial system availability (FR13)
  - [ ] 8.4 Implement checkpoint-based recovery
  - [ ] 8.5 Add timeout and retry mechanisms

### Phase 9: Testing & Documentation
- [ ] 9.0 Write comprehensive tests and documentation
  - [ ] 9.1 Unit tests for normalization logic
  - [ ] 9.2 Integration tests for reconciliation workflow
  - [ ] 9.3 Performance tests (5000 keys in <10 seconds)
  - [ ] 9.4 Test all four scenarios (normal/drift/failure/recovery)
  - [ ] 9.5 Create user documentation and examples
  - [ ] 9.6 Validate reproducibility with seed-based tests

## Success Criteria

- All 15 functional requirements from PRD implemented
- Performance target: 5,000 keys/system in <10 seconds
- Incremental mode 10x faster than full sync
- 100% accurate discrepancy detection after normalization
- Same seed produces identical mock data
- System resumes from checkpoint within 2 seconds