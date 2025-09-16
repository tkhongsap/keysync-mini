# KeySync Mini - Multi-System Key Reconciliation Mockup

A demonstration and testing platform that simulates multi-system key reconciliation workflows. KeySync Mini showcases how an authoritative system (System A) can be compared against multiple downstream/peer systems (B, C, D, E) to identify synchronization gaps, propose master keys, and generate comprehensive reconciliation reports.

## Features

- **Mock Data Generation**: Create synthetic test data with configurable discrepancy patterns
- **Key Normalization**: Apply consistent formatting rules across all systems
- **Discrepancy Detection**: Identify out-of-authority keys, propagation gaps, and duplicates
- **Master Key Provisioning**: Propose and manage master keys for unrecognized entries
- **Comprehensive Reporting**: Generate 5+ CSV reports with detailed reconciliation results
- **Multiple Execution Modes**: Normal, dry-run, and auto-approve modes
- **Error Resilience**: Handle missing files, corrupted data, and partial system availability
- **Performance Optimized**: Process 5,000+ keys per system in under 10 seconds

## Installation

1. Clone the repository:
```bash
git clone https://github.com/tkhongsap/keysync-mini.git
cd keysync-mini
```

2. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Quick Start

### Generate Mock Data and Run Reconciliation

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

### Using the Convenience Script

```bash
# Make script executable
chmod +x run.sh

# Run with default settings
./run.sh

# Run with options
./run.sh --generate-data --scenario drift --keys 2000
```

## Configuration

Edit `keysync-config.yaml` to customize:

- **Normalization Rules**: Uppercase, whitespace trimming, delimiter handling
- **Provisioning Strategy**: Mirror or namespaced master keys
- **Data Sources**: CSV file paths for each system
- **Simulation Settings**: Test scenarios, discrepancy rates, random seed
- **Processing Options**: Batch size, parallel processing, checkpointing

### Test Scenarios

- **normal**: 80% match, 10% missing in A, 10% missing from systems
- **drift**: Gradual key divergence (60% match rate)
- **failure**: Sudden mismatch (50% match rate)
- **recovery**: Return to normal after failure (75% match rate)

## Output Reports

All reports are generated in the `output/` directory with ISO 8601 timestamps:

1. **reconciliation_summary.csv**: High-level statistics and match rates
2. **diff_missing_in_A.csv**: Keys requiring master key provisioning
3. **diff_missing_from_system.csv**: Keys not propagated to systems
4. **master_key_registry.csv**: Proposed and active master keys
5. **audit_log.csv**: Detailed run history with all events

## Command-Line Options

```bash
python src/keysync.py --help

Options:
  -c, --config PATH          Configuration file path
  -m, --mode [full|incremental]  Reconciliation mode
  --dry-run                  Preview without updating registry
  --auto-approve            Auto-activate proposed master keys
  --generate-data           Generate mock data before reconciliation
  --scenario [normal|drift|failure|recovery]  Test scenario
  --keys INTEGER            Keys per system for mock data
  --seed INTEGER            Random seed for reproducibility
  -v, --verbose             Enable verbose logging
  -o, --output-dir PATH     Output directory for reports
```

## Testing

Run the test suite:

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/test_normalizer.py

# Run integration tests only
pytest tests/test_integration.py
```

## Project Structure

```
keysync-mini/
├── input/              # CSV input files (A.csv - E.csv)
├── output/             # Generated reports
├── src/                # Source code
│   ├── keysync.py      # Main CLI entry point
│   ├── mock_data_generator.py  # Test data generation
│   ├── normalizer.py   # Key normalization logic
│   ├── comparator.py   # System comparison engine
│   ├── reconciler.py   # Orchestration logic
│   ├── provisioner.py  # Master key management
│   ├── reporter.py     # Report generation
│   ├── database.py     # SQLite persistence
│   ├── config.py       # Configuration management
│   └── error_handler.py  # Error handling
├── tests/              # Unit and integration tests
├── data/               # SQLite database storage
├── logs/               # Application logs
├── keysync-config.yaml # Configuration file
├── requirements.txt    # Python dependencies
└── run.sh             # Convenience script
```

## Key Reconciliation Logic

1. **System A is Authoritative**: Always treated as the source of truth
2. **Normalization**: Keys are normalized before comparison (uppercase, trim, etc.)
3. **Discrepancy Types**:
   - **Out-of-Authority**: Keys in B/C/D/E but not in A (need master keys)
   - **Propagation Gaps**: Keys in A but missing from other systems
   - **Duplicates**: Multiple keys that normalize to the same value
4. **Master Key Strategies**:
   - **Mirror**: Use normalized key as master key
   - **Namespaced**: Prefix with system identifier

## Performance

- Handles up to 10,000 keys per system efficiently
- Parallel processing for system comparisons
- Batch processing for large datasets
- Incremental mode 10x faster than full sync for <5% changes
- Checkpoint/resume capability for long runs

## Development

### Adding New Features

1. Implement feature in appropriate module
2. Add unit tests in `tests/`
3. Update configuration schema if needed
4. Document in README

### Code Style

```bash
# Format code
black src/ tests/

# Check style
flake8 src/ tests/

# Type checking
mypy src/
```

## License

MIT License - See LICENSE file for details

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

## Support

For issues or questions, please open an issue on GitHub.
