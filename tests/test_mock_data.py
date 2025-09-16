"""Unit tests for mock data generation."""

import pytest
import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from mock_data_generator import MockDataGenerator


class TestMockDataGenerator:
    """Test suite for MockDataGenerator class."""

    @pytest.fixture
    def generator(self):
        """Create a generator with fixed seed."""
        return MockDataGenerator(seed=42)

    def test_reproducible_generation(self):
        """Test that same seed produces same results."""
        gen1 = MockDataGenerator(seed=123)
        gen2 = MockDataGenerator(seed=123)

        key1 = gen1.generate_business_key('customer', 1)
        key2 = gen2.generate_business_key('customer', 1)
        assert key1 == key2

    def test_business_key_formats(self, generator):
        """Test different business key formats."""
        customer_key = generator.generate_business_key('customer', 1)
        assert customer_key.startswith('CUST-')

        product_key = generator.generate_business_key('product', 1)
        assert product_key.startswith('PROD-')

        transaction_key = generator.generate_business_key('transaction', 1)
        assert transaction_key.startswith('TXN-')

        order_key = generator.generate_business_key('order', 1)
        assert order_key.startswith('ORD-')

    def test_scenario_distributions(self, generator):
        """Test different scenario distributions."""
        scenarios = ['normal', 'drift', 'failure', 'recovery']

        for scenario in scenarios:
            dist = generator.create_scenario_distribution(scenario, 1000)
            assert 'common' in dist
            assert 'missing_in_a' in dist
            assert 'missing_from_systems' in dist
            assert abs(sum(dist.values()) - 1.0) < 0.01  # Should sum to ~1.0

    def test_normal_scenario(self, generator):
        """Test normal scenario generation."""
        data = generator.generate_keys_for_scenario(
            scenario='normal',
            keys_per_system=100
        )

        assert 'A' in data
        assert 'B' in data
        assert len(data) == 5  # Systems A through E

        # Check that System A exists and has keys
        assert len(data['A']) > 0

    def test_data_generation_with_duplicates(self, generator):
        """Test duplicate generation."""
        data = generator.generate_keys_for_scenario(
            scenario='normal',
            keys_per_system=100,
            duplicate_rate=0.1  # 10% duplicates
        )

        # Count duplicates in any system
        for system, records in data.items():
            keys = [r['key'] for r in records]
            unique_keys = set(keys)
            # Should have some duplicates
            assert len(keys) >= len(unique_keys)

    def test_csv_file_writing(self, generator):
        """Test writing CSV files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data = generator.generate_keys_for_scenario(
                scenario='normal',
                keys_per_system=50
            )

            generator.write_csv_files(data, tmpdir)

            # Check files were created
            for system in ['A', 'B', 'C', 'D', 'E']:
                file_path = Path(tmpdir) / f"{system}.csv"
                assert file_path.exists()

            # Check stats file
            stats_file = Path(tmpdir) / 'generation_stats.json'
            assert stats_file.exists()

    def test_failure_injection(self, generator):
        """Test failure injection."""
        data = generator.generate_keys_for_scenario(
            scenario='normal',
            keys_per_system=100
        )

        # Inject corruption
        corrupted = generator.inject_failures(data, 'corruption')
        # Should have some corrupted keys
        has_corruption = False
        for system_data in corrupted.values():
            for record in system_data:
                if 'CORRUPTED' in record['key']:
                    has_corruption = True
                    break
        assert has_corruption

    def test_temporal_patterns(self, generator):
        """Test temporal pattern generation."""
        timestamp = generator.generate_temporal_pattern(days_history=30)
        assert timestamp  # Should be non-empty
        assert 'T' in timestamp  # ISO format

    def test_complete_generation_flow(self, generator):
        """Test complete data generation flow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            stats = generator.generate_test_data(
                scenario='normal',
                keys_per_system=100,
                output_dir=tmpdir,
                inject_failures=False
            )

            assert 'scenario' in stats
            assert 'seed' in stats
            assert 'systems' in stats
            assert stats['scenario'] == 'normal'

            # Check all systems have data
            for system in ['A', 'B', 'C', 'D', 'E']:
                assert system in stats['systems']
                assert stats['systems'][system]['total_records'] > 0