"""Reconciliation engine for KeySync Mini."""

import logging
from typing import Dict, List, Set, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path

from database import Database
from normalizer import Normalizer
from comparator import Comparator
from provisioner import Provisioner

logger = logging.getLogger(__name__)


class Reconciler:
    """Main reconciliation engine orchestrating the comparison and provisioning process."""

    def __init__(
        self,
        database: Database,
        normalizer: Normalizer,
        comparator: Comparator,
        provisioner: Provisioner,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize reconciler with component modules."""
        self.db = database
        self.normalizer = normalizer
        self.comparator = comparator
        self.provisioner = provisioner
        self.config = config or {}
        self.run_id = None
        self.checkpoint_data = {}

    def start_reconciliation(
        self,
        mode: str = 'full',
        execution_mode: str = 'normal',
        system_files: Optional[Dict[str, str]] = None
    ) -> int:
        """Start a new reconciliation run.

        Args:
            mode: 'full' or 'incremental'
            execution_mode: 'normal', 'dry-run', or 'auto-approve'
            system_files: Dict of system_name -> file_path

        Returns:
            Run ID
        """
        # Default system files if not provided
        if not system_files:
            input_dir = Path(self.config.get('input_dir', 'input'))
            system_files = {
                system: str(input_dir / f"{system}.csv")
                for system in ['A', 'B', 'C', 'D', 'E']
            }

        # Start run in database
        self.run_id = self.db.start_run(
            run_mode=mode,
            execution_mode=execution_mode,
            config={'system_files': system_files, **self.config}
        )

        logger.info(f"Started reconciliation run {self.run_id} (mode={mode}, exec={execution_mode})")

        # Log start event
        self.db.log_event(
            run_id=self.run_id,
            event_type='run_started',
            event_details=f"Reconciliation started in {mode} mode with {execution_mode} execution"
        )

        return self.run_id

    def perform_reconciliation(self, system_files: Dict[str, str]) -> Dict[str, Any]:
        """Perform the main reconciliation process."""
        results = {
            'run_id': self.run_id,
            'timestamp': datetime.now().isoformat(),
            'comparison': None,
            'discrepancies': None,
            'provisioning': None,
            'incremental_changes': None
        }

        try:
            # Step 1: Compare all systems
            logger.info("Starting system comparison...")
            comparison_results = self.comparator.compare_all_systems(system_files)
            results['comparison'] = comparison_results

            # Save checkpoint
            self.save_checkpoint('comparison_complete', comparison_results)

            # Step 2: Analyze discrepancies
            logger.info("Analyzing discrepancies...")
            discrepancies = self.analyze_discrepancies(comparison_results)
            results['discrepancies'] = discrepancies

            # Save checkpoint
            self.save_checkpoint('discrepancy_analysis_complete', discrepancies)

            # Step 3: Track keys for temporal analysis
            self.track_keys(comparison_results)

            # Step 4: Provision master keys for out-of-authority keys
            if discrepancies['out_of_authority_keys']:
                logger.info("Provisioning master keys...")
                provisioning_results = self.provisioner.propose_master_keys(
                    run_id=self.run_id,
                    out_of_authority_keys=discrepancies['out_of_authority_keys']
                )
                results['provisioning'] = provisioning_results

                # Auto-approve if configured
                execution_mode = self.config.get('execution_mode', 'normal')
                if execution_mode == 'auto-approve':
                    self.provisioner.activate_proposed_keys(self.run_id, auto_approve=True)

            # Step 5: Handle incremental mode
            if self.config.get('mode') == 'incremental':
                last_run = self.db.get_last_successful_run()
                if last_run:
                    incremental_changes = self.calculate_incremental_changes(
                        comparison_results,
                        last_run
                    )
                    results['incremental_changes'] = incremental_changes

            # Log completion
            self.db.log_event(
                run_id=self.run_id,
                event_type='reconciliation_complete',
                event_details=f"Reconciliation completed successfully",
                result='success'
            )

        except Exception as e:
            logger.error(f"Reconciliation failed: {e}")
            self.db.log_event(
                run_id=self.run_id,
                event_type='reconciliation_failed',
                event_details=str(e),
                result='failure'
            )
            raise

        return results

    def analyze_discrepancies(self, comparison_results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze comparison results to identify specific discrepancy types."""
        discrepancies = {
            'out_of_authority_keys': {},  # Keys in B/C/D/E but not in A
            'propagation_gaps': {},  # Keys in A but missing from systems
            'duplicate_keys': {},  # Duplicate keys within systems
            'summary': {}
        }

        comparison = comparison_results.get('comparison', {})
        system_keys = comparison_results.get('system_keys', {})

        # Out-of-authority keys (need master key provisioning)
        keys_missing_in_a = comparison.get('keys_missing_in_a', set())
        for key in keys_missing_in_a:
            source_systems = []
            for system_name, norm_map in system_keys.items():
                if system_name != 'A' and key in norm_map:
                    # Get original keys for this normalized key
                    for orig_key in norm_map[key]:
                        source_systems.append((system_name, orig_key))

            if source_systems:
                discrepancies['out_of_authority_keys'][key] = source_systems

        # Propagation gaps (keys in A but not fully propagated)
        system_gaps = comparison.get('system_specific_gaps', {})
        for system_name, missing_keys in system_gaps.items():
            if missing_keys:
                discrepancies['propagation_gaps'][system_name] = list(missing_keys)

        # Duplicate keys
        duplicates = comparison_results.get('statistics', {}).get('duplicates', {})
        for system_name, dup_groups in duplicates.items():
            discrepancies['duplicate_keys'][system_name] = dup_groups

        # Summary statistics
        discrepancies['summary'] = {
            'total_out_of_authority': len(discrepancies['out_of_authority_keys']),
            'total_propagation_gaps': sum(
                len(gaps) for gaps in discrepancies['propagation_gaps'].values()
            ),
            'total_duplicate_groups': sum(
                len(dups) for dups in discrepancies['duplicate_keys'].values()
            ),
            'affected_systems': list(set(
                list(discrepancies['propagation_gaps'].keys()) +
                list(discrepancies['duplicate_keys'].keys())
            ))
        }

        logger.info(f"Discrepancy analysis complete: {discrepancies['summary']}")

        return discrepancies

    def track_keys(self, comparison_results: Dict[str, Any]):
        """Track keys in database for temporal analysis."""
        system_keys = comparison_results.get('system_keys', {})

        for system_name, norm_map in system_keys.items():
            for normalized_key, original_keys in norm_map.items():
                for orig_key in original_keys:
                    self.db.track_key(
                        run_id=self.run_id,
                        system_name=system_name,
                        key_value=orig_key,
                        normalized_key=normalized_key
                    )

        logger.info(f"Tracked {sum(len(m) for m in system_keys.values())} keys for temporal analysis")

    def calculate_incremental_changes(
        self,
        current_results: Dict[str, Any],
        last_run: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate changes since last run for incremental mode."""
        changes = {
            'new_keys': set(),
            'removed_keys': set(),
            'newly_synchronized': set(),
            'newly_diverged': set()
        }

        # This would compare current results with last run's results
        # For now, returning a placeholder structure
        logger.info("Calculating incremental changes from last run")

        return changes

    def save_checkpoint(self, checkpoint_name: str, data: Any):
        """Save checkpoint for recovery."""
        self.checkpoint_data[checkpoint_name] = {
            'timestamp': datetime.now().isoformat(),
            'data_summary': {
                'type': type(data).__name__,
                'size': len(str(data))
            }
        }

        if self.run_id:
            self.db.save_checkpoint(self.run_id, self.checkpoint_data)
            logger.debug(f"Checkpoint saved: {checkpoint_name}")

    def complete_reconciliation(self, stats: Dict[str, Any], error: Optional[str] = None):
        """Mark reconciliation run as complete."""
        if self.run_id:
            self.db.complete_run(self.run_id, stats, error)
            logger.info(f"Reconciliation run {self.run_id} completed")

    def get_run_summary(self) -> Dict[str, Any]:
        """Get summary of the current reconciliation run."""
        if not self.run_id:
            return {}

        return {
            'run_id': self.run_id,
            'normalizer_stats': self.normalizer.get_statistics(),
            'comparator_stats': self.comparator.stats,
            'provisioner_stats': self.provisioner.get_statistics(),
            'checkpoints': list(self.checkpoint_data.keys())
        }