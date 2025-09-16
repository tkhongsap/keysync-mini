"""Unit tests for the Comparator module."""

import pytest
import sys
import tempfile
import csv
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from comparator import Comparator
from normalizer import Normalizer


class TestComparator:
    """Test suite for Comparator class."""

    @pytest.fixture
    def normalizer(self):
        """Create a normalizer instance."""
        return Normalizer()

    @pytest.fixture
    def comparator(self, normalizer):
        """Create a comparator instance."""
        return Comparator(normalizer, parallel=False, batch_size=100)

    @pytest.fixture
    def temp_csv_files(self):
        """Create temporary CSV files for testing."""
        files = {}
        temp_dir = tempfile.mkdtemp()

        # System A (authoritative)
        a_keys = ['KEY-001', 'KEY-002', 'KEY-003', 'KEY-004', 'KEY-005']
        files['A'] = Path(temp_dir) / 'A.csv'
        with open(files['A'], 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['key', 'last_seen_at'])
            writer.writeheader()
            for key in a_keys:
                writer.writerow({'key': key, 'last_seen_at': '2024-01-01T00:00:00'})

        # System B (missing KEY-005)
        b_keys = ['KEY-001', 'KEY-002', 'KEY-003', 'KEY-004', 'KEY-006']
        files['B'] = Path(temp_dir) / 'B.csv'
        with open(files['B'], 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['key', 'last_seen_at'])
            writer.writeheader()
            for key in b_keys:
                writer.writerow({'key': key, 'last_seen_at': '2024-01-01T00:00:00'})

        # System C (all keys from A)
        files['C'] = Path(temp_dir) / 'C.csv'
        with open(files['C'], 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['key', 'last_seen_at'])
            writer.writeheader()
            for key in a_keys:
                writer.writerow({'key': key, 'last_seen_at': '2024-01-01T00:00:00'})

        return files

    def test_load_system_data(self, comparator, temp_csv_files):
        """Test loading data from CSV file."""
        keys, records = comparator.load_system_data(str(temp_csv_files['A']))
        assert len(keys) == 5
        assert 'KEY-001' in keys
        assert len(records) == 5

    def test_load_missing_file(self, comparator):
        """Test handling of missing file."""
        keys, records = comparator.load_system_data('/nonexistent/file.csv')
        assert keys == []
        assert records == []

    def test_normalize_system_keys(self, comparator):
        """Test key normalization for a system."""
        keys = ['key-1', 'KEY-1', 'key_1', 'KEY-002']
        normalized = comparator.normalize_system_keys('TestSystem', keys)

        # All variations of key-1 should normalize to same key
        assert 'KEY-000001' in normalized
        assert len(normalized['KEY-000001']) == 3
        assert 'KEY-000002' in normalized

    def test_detect_duplicates(self, comparator):
        """Test duplicate detection."""
        keys = ['KEY-001', 'key-001', 'KEY-002']
        comparator.normalize_system_keys('TestSystem', keys)

        duplicates = comparator.stats['duplicates_found'].get('TestSystem', {})
        assert 'KEY-000001' in duplicates
        assert len(duplicates['KEY-000001']) == 2

    def test_compare_all_systems(self, comparator, temp_csv_files):
        """Test full system comparison."""
        system_files = {
            'A': str(temp_csv_files['A']),
            'B': str(temp_csv_files['B']),
            'C': str(temp_csv_files['C'])
        }

        results = comparator.compare_all_systems(system_files)

        # Check structure
        assert 'system_keys' in results
        assert 'comparison' in results
        assert 'statistics' in results

        # Check comparison results
        comparison = results['comparison']
        assert 'keys_only_in_a' in comparison
        assert 'keys_missing_in_a' in comparison
        assert 'system_specific_gaps' in comparison

        # KEY-005 should be missing from B
        gaps_b = comparison['system_specific_gaps'].get('B', set())
        assert 'KEY-000005' in gaps_b

        # KEY-006 should be missing in A
        assert 'KEY-000006' in comparison['keys_missing_in_a']

    def test_parallel_processing(self, normalizer):
        """Test parallel processing capability."""
        comparator = Comparator(normalizer, parallel=True, batch_size=100)
        # Would need more complex test setup for true parallel testing
        assert comparator.parallel is True

    def test_generate_comparison_summary(self, comparator):
        """Test summary DataFrame generation."""
        results = {
            'statistics': {
                'total_unique_keys': 100,
                'keys_in_a': 80,
                'keys_only_in_a': 10,
                'keys_missing_in_a': 20,
                'keys_in_all_systems': 70,
                'match_percentage': 70.0,
                'system_counts': {'A': 80, 'B': 90, 'C': 85}
            }
        }

        df = comparator.generate_comparison_summary(results)
        assert not df.empty
        assert len(df) >= 6  # At least 6 basic metrics