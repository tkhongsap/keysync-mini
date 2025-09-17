#!/usr/bin/env python3
"""KeySync Mini - Multi-system key reconciliation mockup."""

import click
import logging
import sys
from pathlib import Path
from datetime import datetime
import json

from config import Config
from database import Database
from logger import setup_logging, get_logger
from mock_data_generator import MockDataGenerator
from normalizer import Normalizer
from comparator import Comparator
from provisioner import Provisioner
from reconciler import Reconciler
from reporter import Reporter

logger = get_logger(__name__)


@click.command()
@click.option('--config', '-c', default='keysync-config.yaml',
              help='Path to configuration file')
@click.option('--mode', '-m', type=click.Choice(['full', 'incremental']),
              default='full', help='Reconciliation mode')
@click.option('--dry-run', is_flag=True,
              help='Preview changes without updating registry')
@click.option('--auto-approve', is_flag=True,
              help='Automatically activate proposed master keys')
@click.option('--generate-data', is_flag=True,
              help='Generate mock data before reconciliation')
@click.option('--scenario', type=click.Choice(['normal', 'drift', 'failure', 'recovery']),
              default='normal', help='Test scenario for mock data')
@click.option('--keys', type=int, default=1000,
              help='Number of keys per system for mock data')
@click.option('--seed', type=int, default=None,
              help='Random seed for reproducible mock data')
@click.option('--verbose', '-v', is_flag=True,
              help='Enable verbose logging')
@click.option('--output-dir', '-o', default='output',
              help='Directory for output reports')
def main(config, mode, dry_run, auto_approve, generate_data, scenario, keys, seed, verbose, output_dir):
    """KeySync Mini - Multi-system key reconciliation mockup.

    This tool demonstrates key synchronization across multiple systems,
    with System A as the authoritative source.
    """
    # Set up logging
    log_level = 'DEBUG' if verbose else 'INFO'
    setup_logging(log_level=log_level, log_file='logs/keysync.log')

    logger.info("=" * 60)
    logger.info("KeySync Mini - Starting reconciliation")
    logger.info("=" * 60)

    try:
        # Load configuration
        cfg = Config(config_file=config)

        # Override config with command-line options
        if seed is not None:
            cfg.update({'simulation': {'seed': seed}})
        if output_dir:
            cfg.update({'output': {'directory': output_dir}})

        # Determine execution mode
        execution_mode = 'normal'
        if dry_run:
            execution_mode = 'dry-run'
            logger.info("DRY-RUN MODE: No changes will be persisted")
        elif auto_approve:
            execution_mode = 'auto-approve'
            logger.info("AUTO-APPROVE MODE: Master keys will be activated automatically")

        # Generate mock data if requested
        if generate_data:
            logger.info(f"Generating mock data (scenario={scenario}, keys={keys})")
            generator = MockDataGenerator(seed=cfg.get('simulation.seed', 42))
            failure_setting = cfg.get('simulation.failures.inject_corruption', 0.0)
            try:
                failure_chance = float(failure_setting)
            except (TypeError, ValueError):
                logger.warning(
                    "Invalid failure injection setting %r; defaulting to 0", failure_setting
                )
                failure_chance = 0.0
            failure_chance = max(0.0, min(1.0, failure_chance))

            stats = generator.generate_test_data(
                scenario=scenario,
                keys_per_system=keys,
                output_dir='input',
                inject_failures=failure_chance,
                corruption_rate=failure_chance
            )
            logger.info(f"Mock data generated: {json.dumps(stats['systems'], indent=2)}")

        # Initialize components
        logger.info("Initializing components...")
        db = Database(db_path=cfg.get('database.path', 'data/keysync.db'))
        normalizer = Normalizer(config=cfg.get_section('normalize'))
        comparator = Comparator(
            normalizer=normalizer,
            parallel=cfg.get('processing.parallel', True),
            batch_size=cfg.get('processing.batch_size', 1000)
        )
        provisioner = Provisioner(
            database=db,
            config={
                **cfg.get_section('provisioning'),
                'auto_approve': auto_approve
            }
        )
        reconciler = Reconciler(
            database=db,
            normalizer=normalizer,
            comparator=comparator,
            provisioner=provisioner,
            config={
                'mode': mode,
                'execution_mode': execution_mode,
                'input_dir': 'input',
                **cfg.get_section('processing')
            }
        )
        reporter = Reporter(
            database=db,
            output_dir=cfg.get('output.directory', 'output')
        )

        system_files = cfg.get_system_files()
        if not system_files:
            input_dir = Path(reconciler.config.get('input_dir', 'input'))
            system_files = {
                system: str(input_dir / f"{system}.csv")
                for system in ['A', 'B', 'C', 'D', 'E']
            }

        # Start reconciliation
        logger.info(f"Starting {mode} reconciliation...")
        run_id = reconciler.start_reconciliation(
            mode=mode,
            execution_mode=execution_mode,
            system_files=system_files
        )

        # Perform reconciliation
        results = reconciler.perform_reconciliation(system_files)

        # Generate reports (unless in dry-run mode)
        if not dry_run:
            logger.info("Generating reports...")
            results['enable_trend_analysis'] = cfg.get('output.generate_trend_analysis', False)
            reports = reporter.generate_all_reports(run_id, results)
            logger.info(f"Generated {len(reports)} reports in {reporter.output_dir}")

            # Save detailed JSON report
            json_file = reporter.write_json_report(
                f'reconciliation_run_{run_id}_details.json',
                results
            )
            logger.info(f"Detailed results saved to {json_file}")

        # Complete reconciliation
        stats = results.get('comparison', {}).get('statistics', {})
        reconciler.complete_reconciliation(stats)

        # Print summary
        print_summary(results, dry_run)

        # Get final statistics
        final_stats = reconciler.get_run_summary()
        logger.info(f"Run {run_id} completed successfully")
        logger.info(f"Statistics: {json.dumps(final_stats, indent=2, default=str)}")

        # Clean up
        db.close()

        return 0

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1


def print_summary(results: dict, dry_run: bool = False):
    """Print reconciliation summary to console."""
    print("\n" + "=" * 60)
    print("RECONCILIATION SUMMARY")
    print("=" * 60)

    stats = results.get('comparison', {}).get('statistics', {})
    discrepancies = results.get('discrepancies', {}).get('summary', {})

    print(f"Timestamp: {results.get('timestamp', datetime.now().isoformat())}")
    print(f"Mode: {'DRY-RUN' if dry_run else 'NORMAL'}")
    print()

    print("KEY STATISTICS:")
    print(f"  Total Unique Keys: {stats.get('total_unique_keys', 0)}")
    print(f"  Keys in System A: {stats.get('keys_in_a', 0)}")
    print(f"  Keys in All Systems: {stats.get('keys_in_all_systems', 0)}")
    print(f"  Overall Match Rate: {stats.get('match_percentage', 0):.1f}%")
    print()

    print("DISCREPANCIES FOUND:")
    print(f"  Out of Authority Keys: {discrepancies.get('total_out_of_authority', 0)}")
    print(f"  Propagation Gaps: {discrepancies.get('total_propagation_gaps', 0)}")
    print(f"  Duplicate Key Groups: {discrepancies.get('total_duplicate_groups', 0)}")
    print()

    if results.get('provisioning'):
        prov_count = len(results['provisioning'])
        print(f"MASTER KEYS PROPOSED: {prov_count}")
        if dry_run:
            print("  (Not persisted - dry run mode)")
    else:
        print("MASTER KEYS PROPOSED: 0")

    print()
    print("SYSTEM COUNTS:")
    for system, count in sorted(stats.get('system_counts', {}).items()):
        print(f"  System {system}: {count} keys")

    print("=" * 60 + "\n")


if __name__ == '__main__':
    sys.exit(main())