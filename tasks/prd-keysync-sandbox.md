# Product Requirements Document: KeySync Mini Sandbox/Simulation Environment

## 1. Executive Summary

### 1.1 Product Overview
The KeySync Mini Sandbox is an interactive simulation environment that allows users to manually manipulate data across multiple systems (A, B, C, D, E) to test and demonstrate the reconciliation system's capabilities. This feature transforms KeySync Mini from a static demonstration tool into a dynamic testing and learning platform.

### 1.2 Business Context
Currently, KeySync Mini generates mock data with predefined scenarios (normal, drift, failure, recovery). While useful, this approach lacks the flexibility needed for:
- Interactive demonstrations to stakeholders
- Specific edge case testing
- Educational purposes for new team members
- Quality assurance of reconciliation logic
- Customer-specific scenario modeling

### 1.3 Goals
- **Primary Goal**: Enable interactive manipulation of system data to test reconciliation capabilities
- **Secondary Goals**:
  - Provide educational value for understanding data synchronization
  - Support reproducible test scenarios for QA
  - Enable customer demonstration of specific use cases

### 1.4 Non-Goals
- Not replacing the existing mock data generator (they complement each other)
- Not providing production data manipulation capabilities
- Not implementing real-time synchronization between systems
- Not creating a full CRUD database interface

### 1.5 MVP Scope
- **In Scope (MVP)**: CLI-driven sandbox initialization, key add/remove/modify/reset operations, state summaries, baseline snapshot save/load, and optional hand-off into the existing reconciliation run.
- **Post-MVP**: Scenario library and builder, REST/API surfaces, dashboard integration, collaboration features, history analytics, advanced performance targets beyond CSV workflows, and guided tutorials.

### 1.6 MVP Acceptance Criteria
- CLI commands (`init`, `add-key`, `remove-key`, `modify-key`, `reset`, `status`, `save-state`, `load-state`) execute against Systems A–E CSVs with validation and rollback on failure.
- State snapshots persist to a configurable location and can be restored without manual file edits.
- Post-operation summaries report per-system totals and discrepancy hints consistent with reconciliation expectations.
- Reconciliation entry point (`keysync.py`) can consume sandbox state without regression to existing flows.
- Automated tests cover core state transitions and error handling for the in-scope commands.

## 2. User Stories

### 2.1 As a Developer
- I want to **create specific data discrepancies** so that I can test edge cases in the reconciliation logic
- I want to **save and reload test scenarios** so that I can reproduce bugs consistently
- I want to **see real-time system state** so that I can understand how my changes affect the data

### 2.2 As a QA Engineer
- I want to **systematically test all discrepancy types** so that I can ensure comprehensive coverage
- I want to **automate scenario execution** so that I can include them in CI/CD pipelines
- I want to **track changes over time** so that I can verify the reconciliation history

### 2.3 As a Solution Architect
- I want to **demonstrate specific customer scenarios** so that stakeholders understand the solution
- I want to **simulate failure modes** so that I can show system resilience
- I want to **visualize data flow** so that I can explain the reconciliation process

### 2.4 As a New Team Member
- I want to **interactively learn the system** so that I understand how reconciliation works
- I want to **experiment safely** so that I can learn without breaking anything
- I want to **follow guided tutorials** so that I can learn systematically

## 3. Functional Requirements

Requirements below are tagged as **(MVP)** or **(Post-MVP)** to reflect delivery scope.

### 3.1 Core Sandbox Operations

#### FR-1 (MVP): Initialize Synchronized State
- System SHALL provide ability to create perfectly synchronized data across all systems
- User SHALL specify the number of keys (default: 1000)
- System SHALL use consistent key format across all systems
- System SHALL clear any existing data before initialization

#### FR-2 (MVP): Add Keys to Specific Systems
- User SHALL be able to add one or more keys to specified systems
- System SHALL support adding to multiple systems in a single operation
- System SHALL maintain CSV format consistency
- System SHALL support bulk addition via file upload or list input

#### FR-3 (MVP): Remove Keys from Specific Systems
- User SHALL be able to remove specific keys from selected systems
- System SHALL support pattern-based removal (e.g., remove all keys starting with "CUST-")
- System SHALL provide confirmation before destructive operations
- System SHALL log all removal operations

#### FR-4 (MVP): Modify Keys in Systems
- User SHALL be able to modify key values (e.g., change case, add spaces)
- System SHALL support introducing formatting variations for normalization testing
- System SHALL allow corruption injection (malformed keys)

### 3.2 State Management

#### FR-5 (MVP): Show Current State
- System SHALL display current key distribution across all systems
- Display SHALL include:
  - Total keys per system
  - Keys unique to each system
  - Keys common across systems
  - Detected discrepancies
- System SHALL support export of state summary

#### FR-6 (MVP): Save and Load States
- User SHALL be able to save current sandbox state with a name
- System SHALL store state as snapshot including all CSV data
- User SHALL be able to load previously saved states
- System SHALL support sharing states between users

#### FR-7 (MVP): Reset to Baseline
- System SHALL provide one-click reset to synchronized state
- User SHALL be able to choose between empty reset or populated reset
- System SHALL preserve saved states during reset

### 3.3 Scenario Management (Post-MVP)

#### FR-8 (Post-MVP): Pre-built Test Scenarios
- System SHALL include library of common test scenarios:
  - New Product Launch (propagation from A)
  - Unauthorized Keys (additions to non-A systems)
  - Network Partition (missed updates)
  - Data Corruption (malformed keys)
  - Recovery Process (convergence to sync)
- Each scenario SHALL include description and expected outcomes

#### FR-9 (Post-MVP): Custom Scenario Builder
- User SHALL be able to create custom scenarios with multiple steps
- System SHALL support scenario scripting with:
  - Sequential operations
  - Conditional logic
  - Validation checkpoints
- User SHALL be able to save and share custom scenarios

#### FR-10 (Post-MVP): Scenario Execution
- System SHALL execute scenarios step-by-step or all-at-once
- System SHALL provide pause/resume capability
- System SHALL log all scenario actions
- System SHALL validate expected vs actual outcomes

### 3.4 Integration Features

#### FR-11 (MVP): CLI Interface
- System SHALL provide command-line interface for all sandbox operations
- CLI SHALL support:
  - Interactive mode with prompts
  - Non-interactive mode with parameters
  - Batch operations via script files
- CLI SHALL provide comprehensive help documentation

#### FR-12 (Post-MVP): Web Dashboard Integration
- System SHALL integrate sandbox controls into existing web dashboard
- Dashboard SHALL provide:
  - Visual data editor for CSV files
  - Drag-and-drop interface for moving keys between systems
  - Real-time diff viewer
  - Scenario execution controls
- Changes SHALL be immediately reflected in backend CSV files

#### FR-13 (Post-MVP): API Endpoints
- System SHALL expose REST API for sandbox operations
- API SHALL support:
  - All CRUD operations on keys
  - State management operations
  - Scenario execution
- API SHALL return structured JSON responses

### 3.5 Monitoring and Analytics (Post-MVP)

#### FR-14 (Post-MVP): Change History
- System SHALL maintain history of all sandbox operations
- History SHALL include:
  - Timestamp
  - Operation type
  - Affected systems
  - Key details
  - User/source of change
- System SHALL support history export

#### FR-15 (Post-MVP): Reconciliation Impact Analysis
- System SHALL predict reconciliation outcomes before execution
- Analysis SHALL show:
  - Expected discrepancies to be found
  - Master keys to be created
  - Systems to be updated
- System SHALL compare predictions with actual results

## 4. Non-Functional Requirements

### 4.1 Performance
- NFR-1: Sandbox operations SHALL complete within 2 seconds for up to 10,000 keys per system
- NFR-2: State save/load SHALL complete within 5 seconds
- NFR-3 (Post-MVP): Web dashboard SHALL update within 500ms of changes

### 4.2 Usability
- NFR-4: CLI commands SHALL follow Unix conventions
- NFR-5 (Post-MVP): Web interface SHALL be responsive on screens ≥768px width
- NFR-6: Error messages SHALL provide actionable guidance

### 4.3 Reliability
- NFR-7: System SHALL handle concurrent sandbox operations safely
- NFR-8: System SHALL validate CSV integrity after each operation
- NFR-9: System SHALL provide rollback capability for last operation

### 4.4 Security
- NFR-10: System SHALL validate all input to prevent injection attacks
- NFR-11: System SHALL limit bulk operations to prevent resource exhaustion
- NFR-12: System SHALL sanitize keys before display

## 5. Technical Requirements

### 5.1 Architecture Considerations
- Sandbox manager as separate module from core reconciliation
- Stateless operations with filesystem as source of truth
- Event-driven architecture for change notifications (Post-MVP)
- Modular design for easy extension

### 5.2 Data Storage
- CSV files remain primary storage (consistency with existing system)
- Sandbox states stored in `sandbox_states/` directory
- Scenarios stored as JSON in `sandbox_scenarios/` directory (Post-MVP)
- History stored in SQLite database (Post-MVP)

### 5.3 Dependencies
- No new external dependencies required
- Utilize existing: pandas, PyYAML, Flask, Click
- Optional: colorama for CLI colors, rich for better CLI tables

## 6. User Interface Mockups

### 6.1 CLI Interface Example
```
$ python src/sandbox.py init --keys 1000
✓ Initialized 1000 synchronized keys across all systems

$ python src/sandbox.py status
╔════════╦═══════════╦═════════╦═══════════╗
║ System ║ Total Keys║ Unique  ║ Missing   ║
╠════════╬═══════════╬═════════╬═══════════╣
║ A      ║ 1000      ║ 0       ║ 0         ║
║ B      ║ 1000      ║ 0       ║ 0         ║
║ C      ║ 1000      ║ 0       ║ 0         ║
║ D      ║ 1000      ║ 0       ║ 0         ║
║ E      ║ 1000      ║ 0       ║ 0         ║
╚════════╩═══════════╩═════════╩═══════════╝

$ python src/sandbox.py add-key "UNAUTH-001" --systems B,C
✓ Added key 'UNAUTH-001' to systems: B, C

$ python src/sandbox.py remove-key "CUST-00100" --systems D,E
✓ Removed key 'CUST-00100' from systems: D, E
```

### 6.2 Web Dashboard Mockup
```
┌─────────────────────────────────────────────────┐
│ KeySync Mini - Sandbox Environment              │
├─────────────────────────────────────────────────┤
│ [Initialize] [Reset] [Save State] [Load State]  │
├─────────────────────────────────────────────────┤
│ System A (1000)  System B (1000)  System C (1000)│
│ ┌──────────┐     ┌──────────┐     ┌──────────┐ │
│ │CUST-00001│     │CUST-00001│     │CUST-00001│ │
│ │CUST-00002│ --> │CUST-00002│     │CUST-00002│ │
│ │CUST-00003│     │CUST-00003│     │CUST-00003│ │
│ │...       │     │UNAUTH-001│     │UNAUTH-001│ │
│ └──────────┘     └──────────┘     └──────────┘ │
│                                                  │
│ [Add Key] [Remove Key] [Modify Key] [Run Scenario]│
└─────────────────────────────────────────────────┘
```

## 7. Success Metrics

### 7.1 Quantitative Metrics
- Time to create test scenario: < 5 minutes (vs 15+ minutes manually)
- Test coverage: 100% of discrepancy types testable
- Scenario reproducibility: 100% consistent results
- User adoption: 80% of team using sandbox for testing

### 7.2 Qualitative Metrics
- Developer satisfaction with testing capabilities
- QA confidence in test coverage
- Stakeholder understanding of reconciliation process
- Reduced time to diagnose reconciliation issues

## 8. Implementation Phases

### Phase 1 (MVP): Core Sandbox (Week 1-2)
- Basic CLI implementation
- Add/remove/modify operations
- State management
- Status display

### Phase 2 (MVP): CLI Workflow Enhancements (Week 3)
- Extend CLI operations (bulk inputs, validation UX)
- Implement transactional safeguards with rollback-on-error
- Produce state summaries after every command
- Finalize snapshot save/load and baseline reset behavior
- Document commands and examples in CLI help output

### Phase 3 (Post-MVP): Scenario System (Week TBD)
- Pre-built scenarios
- Scenario builder
- Execution engine
- Validation framework

### Phase 4 (Post-MVP): Web Integration (Week TBD)
- Dashboard integration
- Visual editor
- Real-time updates
- API endpoints

### Phase 5 (Post-MVP): Advanced Features (Week TBD)
- History tracking
- Impact analysis
- Batch operations
- Performance optimization

## 9. Testing Strategy

### 9.1 Unit Testing
- Test each sandbox operation in isolation
- Verify CSV file integrity after operations
- Test state save/load functionality

### 9.2 Integration Testing
- Test sandbox with reconciliation engine
- Verify scenario execution end-to-end (Post-MVP)
- Test concurrent operations (Post-MVP)

### 9.3 User Acceptance Testing
- Developer workflow testing
- QA scenario testing (Post-MVP)
- Performance benchmarking (Post-MVP)

## 10. Risks and Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Data corruption during manipulation | High | Low | Implement transaction-like operations with rollback |
| Performance degradation with large datasets | Medium | Medium | Implement pagination and lazy loading |
| Complexity overwhelming new users | Medium | Medium | Provide guided tutorials and templates |
| State management conflicts | Low | Low | Use file locking and atomic operations |

## 11. Open Questions (Post-MVP)

1. Should sandbox operations be reversible (undo/redo)?
2. Should we support real-time collaboration (multiple users)?
3. Should scenarios support branching/conditional logic?
4. Should we provide a scenario marketplace for sharing?
5. Should sandbox integrate with version control for states?

## 12. Appendix

### A. Glossary
- **Sandbox**: Isolated testing environment for data manipulation
- **State**: Snapshot of all system data at a point in time
- **Scenario**: Scripted sequence of operations for testing
- **Discrepancy**: Difference in keys between systems

### B. Related Documents
- Original KeySync Mini PRD: `/keysync_mini_prd.md`
- Implementation PRD: `/tasks/prd-keysync-mini-mockup.md`
- Task Breakdown: `/tasks/tasks-prd-keysync-mini-mockup.md`

### C. Competitive Analysis
- Similar tools: DataDiffer, SyncTest, MockDB
- Unique value: Domain-specific for key reconciliation

---

*Document Version: 1.0*
*Date: 2025-01-18*
*Author: KeySync Mini Team*
*Status: Draft for Review*
