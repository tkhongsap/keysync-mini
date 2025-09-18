"""CLI tests for sandbox commands."""

import sys
from pathlib import Path
from unittest import mock

from click.testing import CliRunner

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from sandbox import cli


def build_config_text(base_dir: Path) -> str:
    input_dir = base_dir / 'input'
    input_dir.mkdir()
    lines = [
        'sources:',
    ]
    for system in ['A', 'B', 'C', 'D', 'E']:
        lines.append(f"  {system}:")
        lines.append("    type: csv")
        lines.append(f"    path: ./input/{system}.csv")
    lines.extend(
        [
            'sandbox:',
            '  snapshot_dir: ./snapshots',
            '  default_key_count: 2',
            '  max_keys: 100',
            'logging:',
            '  level: INFO',
        ]
    )
    return "\n".join(lines)


def test_cli_end_to_end(tmp_path: Path):
    config_path = tmp_path / 'config.yaml'
    config_path.write_text(build_config_text(tmp_path))
    runner = CliRunner()

    # init command
    result = runner.invoke(cli, ['--config', str(config_path), 'init', '--keys', '3'])
    assert result.exit_code == 0
    assert 'Initialized 3 synchronized keys' in result.output

    # add-key command
    result = runner.invoke(
        cli,
        [
            '--config',
            str(config_path),
            'add-key',
            '--key',
            'UNAUTH-001',
            '--systems',
            'B',
            '--systems',
            'C',
        ],
    )
    assert result.exit_code == 0
    assert 'UNAUTH-001' in result.output

    # save-state command
    result = runner.invoke(
        cli,
        ['--config', str(config_path), 'save-state', '--name', 'checkpoint', '--note', 'unit test'],
    )
    assert result.exit_code == 0
    assert 'Snapshot saved' in result.output
    snapshots = list((tmp_path / 'snapshots').iterdir())
    assert snapshots

    # load-state command
    snapshot_dir = snapshots[0]
    result = runner.invoke(
        cli,
        ['--config', str(config_path), 'load-state', str(snapshot_dir)],
    )
    assert result.exit_code == 0
    assert 'Loaded snapshot' in result.output

    # status output
    result = runner.invoke(cli, ['--config', str(config_path), 'status'])
    assert result.exit_code == 0
    assert 'Sandbox summary' in result.output

    # reset with reconciliation flag
    with mock.patch('sandbox.run_reconciliation', return_value={'run_id': 99, 'status': 'success', 'final_stats': {}}) as mock_run:
        result = runner.invoke(cli, ['--config', str(config_path), 'reset', '--reconcile'])
        assert result.exit_code == 0
        assert mock_run.called
        assert 'Reconciliation run' in result.output
