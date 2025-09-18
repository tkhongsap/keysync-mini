"""Tests for the shared reconciliation runner and dashboard utilities."""

from pathlib import Path

from src.keysync import run_reconciliation
from webapp.app import build_view_model


def test_run_reconciliation_dry_run(tmp_path: Path):
    """run_reconciliation should return structured results for consumers."""
    output_dir = tmp_path / 'reports'

    result = run_reconciliation(
        config='keysync-config.yaml',
        mode='full',
        dry_run=True,
        auto_approve=False,
        generate_data=False,
        scenario='normal',
        keys=100,
        seed=42,
        output_dir=str(output_dir),
    )

    assert result['status'] == 'success'
    assert result['results']
    assert 'statistics' in result['results']['comparison']
    assert result['reports'] == []  # dry-run skips report generation
    assert result['generated_data'] is None
    assert result['output_dir'] == str(output_dir)


def test_build_view_model_handles_reconciliation_payload():
    """build_view_model should normalize reconciliation payload structures."""
    mock_results = {
        'results': {
            'timestamp': '2025-01-01T00:00:00',
            'comparison': {
                'statistics': {
                    'total_unique_keys': 10,
                    'keys_in_a': 8,
                    'keys_in_all_systems': 6,
                    'keys_only_in_a': 2,
                    'keys_missing_in_a': 1,
                    'match_percentage': 60.0,
                    'system_counts': {'A': 8, 'B': 7},
                    'duplicates': {'B': [['dup']]}},
                'comparison': {
                    'keys_only_in_a': {'A1'},
                    'keys_missing_in_a': {'B1'}
                },
                'system_specific_gaps': {'B': {'A1', 'A2'}},
            },
            'discrepancies': {
                'summary': {
                    'total_out_of_authority': 1,
                    'total_propagation_gaps': 2,
                    'total_duplicate_groups': 1,
                },
                'propagation_gaps': {'B': ['A1']},
                'out_of_authority_keys': {'B1': [('B', 'b1')]},
                'duplicate_keys': {'B': [['dup']]},
            },
            'provisioning': [
                {
                    'master_key': 'B1',
                    'source_system': 'B',
                    'source_key': 'b1',
                    'affected_systems': ['C'],
                    'status': 'proposed',
                }
            ],
        }
    }

    view = build_view_model(mock_results)

    assert view['stats_items'][0][0] == 'Total Unique Keys'
    assert view['propagation_gaps']['B'] == ['A1']
    assert view['out_of_authority'][0]['normalized_key'] == 'B1'
    assert view['provisioning'][0]['master_key'] == 'B1'
    assert view['keys_only_in_a'] == ['A1']
    assert view['keys_missing_in_a'] == ['B1']
