"""Command-line sandbox utilities for KeySync Mini."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import click

from config import Config
from logger import setup_logging, get_logger
from sandbox_state import (
    SandboxValidationError,
    build_manager_from_config,
    ensure_systems,
    ensure_keys,
    load_keys_from_file,
)

logger = get_logger(__name__)


def _load_config(config_path: str, verbose: bool) -> Config:
    """Load configuration and initialize logging."""
    cfg = Config(config_file=config_path)
    log_level = cfg.get('logging.level', 'INFO')
    log_file = cfg.get('logging.file')
    if verbose:
        log_level = 'DEBUG'
    setup_logging(log_level=log_level, log_file=log_file)
    return cfg


def _resolve_keys(key_values: Tuple[str, ...], key_file: Path | None) -> List[str]:
    """Collect keys from CLI options and optional file inputs."""
    keys: List[str] = []
    if key_file:
        keys.extend(load_keys_from_file(key_file))
    if key_values:
        keys.extend(ensure_keys(key_values))
    if not keys:
        raise SandboxValidationError("At least one key must be supplied")
    return ensure_keys(keys)


def _display_report(report: Dict[str, Any]) -> None:
    """Render sandbox summary information to stdout."""
    click.echo("Sandbox summary:")
    for system, stats in report['systems'].items():
        missing = len(report['discrepancies'].get(system, []))
        click.echo(
            f"  {system}: total={stats['total']} unique={stats['unique']} missing={missing}"
        )
    click.echo(
        f"\nTotal unique keys: {report['total_unique_keys']}"
    )
    click.echo(
        f"Keys common to all systems: {report['keys_common_to_all']}"
    )
    click.echo(f"Snapshots available: {report['snapshot_count']}")


@click.group()
@click.option(
    '-c',
    '--config',
    'config_path',
    default='keysync-config.yaml',
    show_default=True,
    help='Path to configuration file.',
)
@click.option('-v', '--verbose', is_flag=True, help='Enable debug logging output.')
@click.pass_context
def cli(ctx: click.Context, config_path: str, verbose: bool) -> None:
    """Sandbox CLI for manipulating reconciliation input data."""
    ctx.ensure_object(dict)
    ctx.obj['config_path'] = config_path
    ctx.obj['verbose'] = verbose


def _get_manager(ctx: click.Context):
    cfg = _load_config(ctx.obj['config_path'], ctx.obj['verbose'])
    manager = build_manager_from_config(cfg)
    sandbox_defaults = cfg.get_section('sandbox')
    return cfg, manager, sandbox_defaults


@cli.command(name='init')
@click.option(
    '--keys',
    type=int,
    help='Number of synchronized keys to generate across all systems.',
)
@click.pass_context
def initialize(ctx: click.Context, keys: int | None) -> None:
    """Create a synchronized baseline across all systems."""
    cfg, manager, sandbox_defaults = _get_manager(ctx)
    default_count = sandbox_defaults.get('default_key_count', 1000)
    key_count = keys or default_count
    try:
        manager.initialize(key_count)
        click.echo(f"✓ Initialized {key_count} synchronized keys across systems")
        _display_report(manager.build_status_report())
    except SandboxValidationError as exc:
        raise click.ClickException(str(exc)) from exc


@cli.command(name='status')
@click.pass_context
def status(ctx: click.Context) -> None:
    """Display sandbox status summary."""
    _, manager, _ = _get_manager(ctx)
    report = manager.build_status_report()
    _display_report(report)


@cli.command(name='add-key')
@click.option('--key', 'keys', multiple=True, help='Key value to add. Repeat for multiple keys.')
@click.option(
    '--key-file',
    type=click.Path(path_type=Path),
    help='Path to a file containing keys (newline-delimited or CSV with a key column).'
)
@click.option(
    '--systems',
    multiple=True,
    help='Target systems (default: all systems).',
)
@click.pass_context
def add_key(ctx: click.Context, keys: Tuple[str, ...], key_file: Path | None, systems: Tuple[str, ...]):
    """Add keys to specified systems."""
    _, manager, _ = _get_manager(ctx)
    try:
        key_values = _resolve_keys(keys, key_file)
        target_systems = systems or tuple(manager.allowed_systems)
        target_systems = ensure_systems(target_systems, manager.allowed_systems)
        added_count, summary = manager.add_keys(key_values, target_systems)
        click.echo(f"✓ Added {added_count} key entries")
        for system, system_keys in summary.items():
            if system_keys:
                click.echo(f"  {system}: {', '.join(system_keys)}")
        _display_report(manager.build_status_report())
    except SandboxValidationError as exc:
        raise click.ClickException(str(exc)) from exc


@cli.command(name='remove-key')
@click.option('--key', 'keys', multiple=True, help='Key value to remove. Repeat as needed.')
@click.option(
    '--key-file',
    type=click.Path(path_type=Path),
    help='File with keys to remove (newline-delimited or CSV with key column).'
)
@click.option('--pattern', help='Substring pattern to match keys for removal.')
@click.option('--systems', multiple=True, help='Systems to remove keys from (default: all).')
@click.pass_context
def remove_key(
    ctx: click.Context,
    keys: Tuple[str, ...],
    key_file: Path | None,
    pattern: str | None,
    systems: Tuple[str, ...],
) -> None:
    """Remove keys from selected systems."""
    if not keys and not key_file and not pattern:
        raise click.ClickException('Specify --key/--key-file and/or --pattern to remove keys')
    _, manager, _ = _get_manager(ctx)
    try:
        key_values = _resolve_keys(keys, key_file) if (keys or key_file) else []
        target_systems = systems or tuple(manager.allowed_systems)
        summary = manager.remove_keys(key_values, target_systems, pattern)
        click.echo("✓ Removal summary")
        for system, removed in summary.items():
            if removed:
                click.echo(f"  {system}: {', '.join(removed)}")
        _display_report(manager.build_status_report())
    except SandboxValidationError as exc:
        raise click.ClickException(str(exc)) from exc


@cli.command(name='modify-key')
@click.option(
    '--rename',
    nargs=2,
    multiple=True,
    metavar='OLD NEW',
    help='Rename a key from OLD to NEW. Repeat for multiple renames.'
)
@click.option('--systems', multiple=True, help='Systems to apply the rename to (default: all).')
@click.pass_context
def modify_key(ctx: click.Context, rename: Tuple[Tuple[str, str], ...], systems: Tuple[str, ...]) -> None:
    """Modify keys by renaming them across systems."""
    if not rename:
        raise click.ClickException('Provide at least one --rename OLD NEW pairing')
    _, manager, _ = _get_manager(ctx)
    try:
        replacements = {old: new for old, new in rename}
        target_systems = systems or tuple(manager.allowed_systems)
        changes = manager.modify_keys(replacements, target_systems)
        click.echo("✓ Modified keys")
        for system, updates in changes.items():
            for old_key, new_key in updates:
                click.echo(f"  {system}: {old_key} -> {new_key}")
        _display_report(manager.build_status_report())
    except SandboxValidationError as exc:
        raise click.ClickException(str(exc)) from exc


@cli.command(name='reset')
@click.option('--empty', is_flag=True, help='Reset sandbox to an empty state instead of populated baseline.')
@click.pass_context
def reset(ctx: click.Context, empty: bool) -> None:
    """Reset sandbox to baseline state."""
    cfg, manager, sandbox_defaults = _get_manager(ctx)
    default_count = sandbox_defaults.get('default_key_count', 1000)
    try:
        if empty:
            manager.state.records = {system: {} for system in manager.allowed_systems}
            manager.persist()
            click.echo('✓ Reset sandbox to empty state')
        else:
            manager.initialize(default_count)
            click.echo(f"✓ Reset sandbox with {default_count} synchronized keys")
        _display_report(manager.build_status_report())
    except SandboxValidationError as exc:
        raise click.ClickException(str(exc)) from exc


@cli.command(name='save-state')
@click.option('--name', required=True, help='Snapshot name.')
@click.option('--note', help='Optional note stored with snapshot metadata.')
@click.pass_context
def save_state(ctx: click.Context, name: str, note: str | None) -> None:
    """Save current sandbox state as a snapshot."""
    _, manager, _ = _get_manager(ctx)
    metadata: Dict[str, Any] = {}
    if note:
        metadata['note'] = note
    try:
        snapshot_path = manager.save_snapshot(name=name, metadata=metadata)
        click.echo(f"✓ Snapshot saved at {snapshot_path}")
    except SandboxValidationError as exc:
        raise click.ClickException(str(exc)) from exc


@cli.command(name='load-state')
@click.argument('snapshot', type=click.Path(path_type=Path))
@click.pass_context
def load_state(ctx: click.Context, snapshot: Path) -> None:
    """Load a previously saved snapshot."""
    _, manager, _ = _get_manager(ctx)
    try:
        manager.load_snapshot(snapshot)
        click.echo(f"✓ Loaded snapshot from {snapshot}")
        _display_report(manager.build_status_report())
    except SandboxValidationError as exc:
        raise click.ClickException(str(exc)) from exc


if __name__ == '__main__':
    cli()
