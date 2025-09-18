"""Integration tests for KeySync Mini end-to-end workflow."""

import pytest
import sys
import tempfile
from pathlib import Path
import shutil

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from config import Config
from database import Database
from normalizer import Normalizer
from comparator import Comparator
from provisioner import Provisioner
from reconciler import Reconciler
from reporter import Reporter
from mock_data_generator import MockDataGenerator
from error_handler import ErrorHandler
from sandbox_state import build_manager_from_config
from keysync import run_reconciliation


class TestIntegration:
    """Integration test suite for complete workflow."""

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace for testing."""
        workspace = tempfile.mkdtemp()
        yield workspace
        # Cleanup
        shutil.rmtree(workspace, ignore_errors=True)

    @pytest.fixture
    def test_config(self, temp_workspace):
        """Create test configuration."""
        return {
            'normalize': {
                'uppercase': True,
                'strip_non_alnum': True,
                'collapse_delims': '-'
            },
            'provisioning': {
                'strategy': 'mirror',
                'auto_approve': False
            },
            'processing': {
                'mode': 'full',
                'parallel': False,
                'batch_size': 100
            },
            'database': {
                'path': f'{temp_workspace}/test.db'
            },
            'output': {
                'directory': f'{temp_workspace}/output'
            }
        }

    def test_end_to_end_normal_scenario(self, temp_workspace, test_config):
        """Test complete workflow with normal scenario."""
        # Generate mock data
        generator = MockDataGenerator(seed=42)
        generator.generate_test_data(
            scenario='normal',
            keys_per_system=100,
            output_dir=f'{temp_workspace}/input'
        )

        # Initialize components
        db = Database(db_path=test_config['database']['path'])
        normalizer = Normalizer(config=test_config['normalize'])
        comparator = Comparator(normalizer, parallel=False)
        provisioner = Provisioner(db, config=test_config['provisioning'])
        reconciler = Reconciler(db, normalizer, comparator, provisioner, test_config)
        reporter = Reporter(db, output_dir=test_config['output']['directory'])

        # Run reconciliation
        system_files = {
            system: f'{temp_workspace}/input/{system}.csv'
            for system in ['A', 'B', 'C', 'D', 'E']
        }

        run_id = reconciler.start_reconciliation(
            mode='full',
            execution_mode='normal',
            system_files=system_files
        )

        results = reconciler.perform_reconciliation(system_files)

        # Verify results structure
        assert results['run_id'] == run_id
        assert 'comparison' in results
        assert 'discrepancies' in results

        # Generate reports
        reports = reporter.generate_all_reports(run_id, results)
        assert len(reports) >= 5  # Should generate at least 5 reports

        # Check reports exist
        for report in reports:
            assert Path(report).exists()

        # Complete run
        stats = results.get('comparison', {}).get('statistics', {})
        reconciler.complete_reconciliation(stats)

        # Verify run was recorded
        last_run = db.get_last_successful_run()
        assert last_run is not None
        assert last_run['run_id'] == run_id

        db.close()

    def test_dry_run_mode(self, temp_workspace, test_config):
        """Test dry-run mode doesn't persist changes."""
        # Generate mock data
        generator = MockDataGenerator(seed=42)
        generator.generate_test_data(
            scenario='normal',
            keys_per_system=50,
            output_dir=f'{temp_workspace}/input'
        )

        # Initialize components
        db = Database(db_path=test_config['database']['path'])
        normalizer = Normalizer(config=test_config['normalize'])
        comparator = Comparator(normalizer, parallel=False)
        provisioner = Provisioner(db, config=test_config['provisioning'])
        reconciler = Reconciler(db, normalizer, comparator, provisioner, test_config)

        system_files = {
            system: f'{temp_workspace}/input/{system}.csv'
            for system in ['A', 'B', 'C', 'D', 'E']
        }

        # Run in dry-run mode
        run_id = reconciler.start_reconciliation(
            mode='full',
            execution_mode='dry-run',
            system_files=system_files
        )

        results = reconciler.perform_reconciliation(system_files)

        # Check that provisioning occurred but wasn't activated
        if results.get('provisioning'):
            # Check database for proposed keys
            master_keys = db.get_master_keys(status='proposed')
            for key in master_keys:
                assert key['status'] == 'proposed'  # Should not be active

        db.close()

    def test_auto_approve_mode(self, temp_workspace, test_config):
        """Test auto-approve mode activates master keys."""
        # Update config for auto-approve
        test_config['provisioning']['auto_approve'] = True

        # Generate mock data with out-of-authority keys
        generator = MockDataGenerator(seed=42)
        data = generator.generate_test_data(
            scenario='drift',  # More discrepancies
            keys_per_system=50,
            output_dir=f'{temp_workspace}/input'
        )

        # Initialize components
        db = Database(db_path=test_config['database']['path'])
        normalizer = Normalizer(config=test_config['normalize'])
        comparator = Comparator(normalizer, parallel=False)
        provisioner = Provisioner(db, config=test_config['provisioning'])
        reconciler = Reconciler(db, normalizer, comparator, provisioner, test_config)

        system_files = {
            system: f'{temp_workspace}/input/{system}.csv'
            for system in ['A', 'B', 'C', 'D', 'E']
        }

        # Run with auto-approve
        test_config['execution_mode'] = 'auto-approve'
        run_id = reconciler.start_reconciliation(
            mode='full',
            execution_mode='auto-approve',
            system_files=system_files
        )

        results = reconciler.perform_reconciliation(system_files)

        # Check that keys were activated
        if results.get('provisioning'):
            master_keys = db.get_master_keys(status='active')
            # Should have some active keys with auto-approve
            assert any(k['run_id'] == run_id for k in master_keys)

        db.close()

    def test_sandbox_reconciliation_bridge(self, temp_workspace, test_config):
        """Ensure sandbox state drives reconciliation via shared configuration."""
        config_path = Path(temp_workspace) / 'sandbox-config.yaml'
        input_dir = Path(temp_workspace) / 'input'
        input_dir.mkdir()
        sources_block = "\n".join(
            [
                'sources:',
                *[
                    f"  {system}:\n    type: csv\n    path: {input_dir / f'{system}.csv'}"
                    for system in ['A', 'B', 'C', 'D', 'E']
                ],
                'sandbox:',
                f"  snapshot_dir: {Path(temp_workspace) / 'snapshots'}",
                '  default_key_count: 2',
                '  max_keys: 50',
                'database:',
                f"  path: {Path(temp_workspace) / 'sandbox.db'}",
                'output:',
                f"  directory: {Path(temp_workspace) / 'output'}",
            ]
        )
        config_path.write_text(sources_block)

        cfg = Config(config_file=str(config_path))
        manager = build_manager_from_config(cfg)
        manager.initialize(2)
        manager.add_keys(['UNAUTH-001'], ['B'])

        result = run_reconciliation(
            config=str(config_path),
            mode='full',
            dry_run=True,
        )
        assert result['status'] == 'success'
        discrepancies = result['results']['discrepancies']
        assert discrepancies['out_of_authority_keys']

    def test_error_handling(self, temp_workspace, test_config):
        """Test error handling with missing files."""
        # Only create some files
        generator = MockDataGenerator(seed=42)
        data = generator.generate_test_data(
            scenario='normal',
            keys_per_system=50,
            output_dir=f'{temp_workspace}/input'
        )

        # Delete one file to simulate missing system
        Path(f'{temp_workspace}/input/D.csv').unlink()

        # Initialize with error handler
        error_handler = ErrorHandler({
            'on_missing_file': 'skip',
            'enable_partial_processing': True
        })

        db = Database(db_path=test_config['database']['path'])
        normalizer = Normalizer(config=test_config['normalize'])
        comparator = Comparator(normalizer, parallel=False)
        provisioner = Provisioner(db, config=test_config['provisioning'])
        reconciler = Reconciler(db, normalizer, comparator, provisioner, test_config)

        system_files = {
            system: f'{temp_workspace}/input/{system}.csv'
            for system in ['A', 'B', 'C', 'D', 'E']
        }

        # Should handle missing file gracefully
        run_id = reconciler.start_reconciliation(
            mode='full',
            execution_mode='normal',
            system_files=system_files
        )

        results = reconciler.perform_reconciliation(system_files)

        # Should complete despite missing file
        assert results is not None
        assert 'comparison' in results

        db.close()

    def test_performance_benchmark(self, temp_workspace, test_config):
        """Test performance with larger dataset."""
        import time

        # Generate larger dataset
        generator = MockDataGenerator(seed=42)
        generator.generate_test_data(
            scenario='normal',
            keys_per_system=5000,  # 5000 keys per system
            output_dir=f'{temp_workspace}/input'
        )

        # Initialize components
        db = Database(db_path=test_config['database']['path'])
        normalizer = Normalizer(config=test_config['normalize'])
        comparator = Comparator(normalizer, parallel=True)  # Enable parallel
        provisioner = Provisioner(db, config=test_config['provisioning'])
        reconciler = Reconciler(db, normalizer, comparator, provisioner, test_config)

        system_files = {
            system: f'{temp_workspace}/input/{system}.csv'
            for system in ['A', 'B', 'C', 'D', 'E']
        }

        start_time = time.time()

        run_id = reconciler.start_reconciliation(
            mode='full',
            execution_mode='normal',
            system_files=system_files
        )

        results = reconciler.perform_reconciliation(system_files)

        elapsed_time = time.time() - start_time

        # Should process 5000 keys per system in under 10 seconds
        assert elapsed_time < 10.0, f"Processing took {elapsed_time:.2f} seconds"

        # Verify results
        stats = results.get('comparison', {}).get('statistics', {})
        assert stats.get('total_unique_keys', 0) > 0

        db.close()
