"""Unit tests for sandbox state management."""

import csv
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from sandbox_state import (
    SandboxStateManager,
    SandboxValidationError,
    ensure_keys,
    ensure_systems,
    load_keys_from_file,
)


@pytest.fixture
def sandbox_paths(tmp_path: Path):
    """Provide sandbox file layout for tests."""
    input_dir = tmp_path / 'input'
    input_dir.mkdir()
    system_files = {system: input_dir / f'{system}.csv' for system in ['A', 'B', 'C', 'D', 'E']}
    snapshot_dir = tmp_path / 'snapshots'
    manager = SandboxStateManager(system_files, snapshot_dir, max_keys=100, default_key_prefix='CUST')
    return manager, system_files, snapshot_dir


def read_keys(path: Path) -> list[str]:
    with path.open('r', newline='') as handle:
        reader = csv.DictReader(handle)
        return [row['key'] for row in reader]


def test_initialize_and_summary(sandbox_paths):
    manager, system_files, _ = sandbox_paths
    manager.initialize(3)

    for system, path in system_files.items():
        assert path.exists()
        keys = read_keys(path)
        assert len(keys) == 3
        assert keys[0].startswith('CUST-')

    report = manager.build_status_report()
    assert report['total_unique_keys'] == 3
    assert report['keys_common_to_all'] == 3
    for stats in report['systems'].values():
        assert stats['total'] == 3
        assert stats['unique'] == 0


def test_add_remove_modify_and_snapshots(sandbox_paths, tmp_path):
    manager, system_files, snapshot_dir = sandbox_paths
    manager.initialize(2)

    # Add keys to B and C
    added_count, summary = manager.add_keys(['UNAUTH-001', ' UNAUTH-002 '], ['B', 'C'])
    assert added_count == 4
    assert set(summary['B']) == {'UNAUTH-001', 'UNAUTH-002'}
    assert set(summary['C']) == {'UNAUTH-001', 'UNAUTH-002'}

    # Remove by pattern across systems
    removal = manager.remove_keys(pattern='UNAUTH')
    assert removal['B']
    assert removal['C']

    # Modify key
    manager.add_keys(['LEGACY-001'], ['A'])
    changes = manager.modify_keys({'LEGACY-001': 'LEGACY-RENAMED'}, ['A'])
    assert ('LEGACY-001', 'LEGACY-RENAMED') in changes['A']

    # Save snapshot and ensure metadata
    snapshot = manager.save_snapshot('baseline', metadata={'note': 'initial sandbox'})
    assert snapshot_dir.exists()
    meta = (snapshot / 'metadata.json').read_text()
    assert 'baseline' in meta
    assert 'initial sandbox' in meta
    assert 'creator' in meta

    # Wipe and reload snapshot
    manager.state.records = {system: {} for system in manager.allowed_systems}
    manager.persist()
    manager.load_snapshot(snapshot)
    for path in system_files.values():
        assert path.exists()


def test_validation_helpers(tmp_path: Path):
    with pytest.raises(SandboxValidationError):
        ensure_keys([])
    assert ensure_keys([' K1 ', 'K1', 'K2']) == ['K1', 'K2']

    with pytest.raises(SandboxValidationError):
        ensure_systems(['Z'], ['A', 'B'])
    assert ensure_systems(['a', 'B'], ['A', 'B', 'C']) == ['A', 'B']

    text_keys = tmp_path / 'keys.txt'
    text_keys.write_text('foo\nbar\n')
    csv_keys = tmp_path / 'keys.csv'
    csv_keys.write_text('key\nfoo\nbar\n')
    assert load_keys_from_file(text_keys) == ['foo', 'bar']
    assert load_keys_from_file(csv_keys) == ['foo', 'bar']
