## Relevant Files

- `src/sandbox.py` - CLI entry point for sandbox operations, summaries, and snapshot utilities.
- `src/sandbox_state.py` - Implements sandbox state manager, validation helpers, and snapshot workflows shared by CLI/dashboard.
- `src/scenario_library.py` - Defines built-in and custom scenario descriptors plus execution helpers.
- `src/config.py` - Extend configuration handling for sandbox defaults and storage locations.
- `src/keysync.py` - Integrate sandbox triggers with existing reconciliation pipeline and shared utilities.
- `src/reconciler.py` - Ensure sandbox outputs feed reconciliation without breaking existing flows.
- `webapp/app.py` - Surface sandbox state, operations, and scenario controls through the Flask dashboard.
- `webapp/templates/index.html` - Update UI layout with sandbox controls, state visualization, and tutorials.
- `webapp/static/js/sandbox.js` - Add front-end behavior for interactive sandbox actions and live updates.
- `tests/test_sandbox_cli.py` - Unit tests covering CLI operations, argument parsing, and error cases.
- `tests/test_sandbox_state.py` - Unit tests for state persistence, snapshot load/save, and validation.
- `tests/test_scenarios.py` - Unit tests for scenario library execution paths and expectations.
- `tests/test_integration.py` - Extend integration coverage for sandbox-to-reconciliation flows.
- `tests/test_keysync_frontend.py` - Capture new UI interactions and API hooks in the dashboard.

### Notes

- Persist sandbox CSV snapshots under `output/snapshots/` while keeping generated artifacts out of version control.
- Reuse existing logging patterns (`get_logger(__name__)`) and Click conventions already present in the project.
- Prefer dependency-free implementations; only add third-party packages if absolutely necessary and update `requirements.txt` accordingly.
- Document new CLI commands in `README.md` or dedicated docs once implementation stabilizes.

## Tasks

- [x] 1.0 (MVP) Establish sandbox architecture and shared utilities (2025-09-18T13:20:45Z)
  - [x] 1.1 Map existing reconciliation data flow to identify integration points for sandbox ingress/egress.
  - [x] 1.2 Design sandbox domain models (key records, system sets, snapshots) and write module docstrings outlining responsibilities.
  - [x] 1.3 Implement reusable validation, formatting, and logging helpers shared by CLI and dashboard.
  - [x] 1.4 Update configuration schema to persist sandbox defaults (storage paths, max keys, seed behavior).
- [x] 2.0 (MVP) Deliver CLI-based sandbox operations workflow (2025-09-18T13:26:35Z)
  - [x] 2.1 Implement Click command group in `src/sandbox.py` for initialize, add-key, remove-key, modify-key, reset, status, save-state, load-state.
  - [x] 2.2 Wire CLI commands to state manager with transactional updates and rollback-on-error safeguards.
  - [x] 2.3 Support bulk operations via CSV uploads or inline lists; ensure validation errors are user-friendly.
  - [x] 2.4 Generate state summary output (per-system counts, discrepancy hints) after each operation.
  - [x] 2.5 Add CLI help text, examples, and ensure `python src/sandbox.py --help` reflects PRD actions.
- [x] 3.0 (MVP) Implement sandbox state persistence (2025-09-18T13:29:12Z)
  - [x] 3.1 Build snapshot save/load APIs with metadata (creator, timestamp, description) and file locking.
  - [x] 3.2 Implement reset-to-baseline options (empty vs populated) honoring saved states.
- [ ] 4.0 (MVP) Reconciliation integration and QA coverage
  - [ ] 4.1 Integrate sandbox runs with reconciliation engine; allow chained execution via CLI flag or `run.sh`.
  - [ ] 4.2 Extend pytest coverage for sandbox operations, snapshot workflows, and reconciliation assertions.

### Post-MVP Backlog

- [ ] 3.3 Create pre-built scenarios aligned with PRD (launch, unauthorized, partition, corruption, recovery) plus expected outcomes.
- [ ] 3.4 Develop custom scenario builder bindings supporting scripted sequences and validations.
- [ ] 3.5 Provide export/import utilities to share scenarios and states across environments.
- [ ] 4.3 Capture state change history and operation logs for auditing and QA review.
- [ ] 4.4 Extend pytest coverage for scenario execution, history tracking, and reconciliation assertions.
- [ ] 4.5 Document automation pathways for CI/CD (commands, environment variables, sample scripts).
- [ ] 5.0 Extend web dashboard with interactive sandbox experience
  - [ ] 5.1 Add Flask routes/APIs for sandbox operations, state display, and scenario CRUD.
  - [ ] 5.2 Update templates with controls (initialize, add/remove/modify key, run scenario, save/load state) and real-time stats.
  - [ ] 5.3 Implement client-side interactivity (AJAX or fetch) for state updates without full page reloads.
  - [ ] 5.4 Provide guided tutorials or walkthrough modals for new users based on PRD requirements.
  - [ ] 5.5 Ensure accessibility and responsive layout; update frontend tests to cover new interactions.
