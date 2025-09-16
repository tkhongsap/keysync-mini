"""Unit tests for the Normalizer module."""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from normalizer import Normalizer


class TestNormalizer:
    """Test suite for Normalizer class."""

    def test_default_config(self):
        """Test normalizer with default configuration."""
        normalizer = Normalizer()
        assert normalizer.config['uppercase'] is True
        assert normalizer.config['strip_non_alnum'] is True

    def test_uppercase_normalization(self):
        """Test uppercase transformation."""
        normalizer = Normalizer({'uppercase': True})
        assert normalizer.normalize('abc123') == 'ABC123'
        assert normalizer.normalize('AbC123') == 'ABC123'

    def test_trim_whitespace(self):
        """Test whitespace trimming."""
        normalizer = Normalizer({'trim_whitespace': True})
        assert normalizer.normalize('  test  ') == 'TEST'
        assert normalizer.normalize('\ttest\n') == 'TEST'

    def test_strip_non_alphanumeric(self):
        """Test stripping non-alphanumeric characters."""
        normalizer = Normalizer({'strip_non_alnum': True, 'collapse_delims': '-'})
        assert normalizer.normalize('test@#$123') == 'TEST123'
        assert normalizer.normalize('test-123') == 'TEST-123'  # Delimiter preserved

    def test_collapse_delimiters(self):
        """Test delimiter collapsing."""
        normalizer = Normalizer({'collapse_delims': '-'})
        assert normalizer.normalize('test___123') == 'TEST-123'
        assert normalizer.normalize('test   123') == 'TEST-123'
        assert normalizer.normalize('test--123') == 'TEST-123'

    def test_left_pad_numbers(self):
        """Test number padding."""
        normalizer = Normalizer({'left_pad_numbers': True, 'pad_length': 6})
        assert normalizer.normalize('CUST-123') == 'CUST-000123'
        assert normalizer.normalize('CUST-1234567') == 'CUST-1234567'  # No truncation

    def test_complex_normalization(self):
        """Test complex normalization with all rules."""
        normalizer = Normalizer()
        test_cases = [
            ('  cust-123  ', 'CUST-000123'),
            ('PROD__ABC__789', 'PROD-ABC-000789'),
            ('txn 2024 001', 'TXN-002024-000001'),
            ('ORD#999999', 'ORD999999'),
        ]

        for input_key, expected in test_cases:
            assert normalizer.normalize(input_key) == expected

    def test_normalize_batch(self):
        """Test batch normalization."""
        normalizer = Normalizer()
        keys = ['test1', 'TEST2', '  test3  ']
        normalized = normalizer.normalize_batch(keys)
        assert normalized == ['TEST1', 'TEST2', 'TEST3']

    def test_normalize_with_mapping(self):
        """Test normalization with mapping."""
        normalizer = Normalizer()
        keys = ['test1', 'TEST-1', '  test_1  ']
        mapping = normalizer.normalize_with_mapping(keys)

        assert mapping['test1'] == 'TEST1'
        assert mapping['TEST-1'] == 'TEST-000001'
        assert mapping['  test_1  '] == 'TEST-000001'

    def test_statistics_tracking(self):
        """Test that statistics are tracked correctly."""
        normalizer = Normalizer()
        normalizer.reset_statistics()

        normalizer.normalize('  test  ')  # trim, uppercase
        normalizer.normalize('test@123')  # strip_non_alnum
        normalizer.normalize('test')      # uppercase only

        stats = normalizer.get_statistics()
        assert stats['total_normalized'] == 3
        assert 'uppercase' in stats['transformations']