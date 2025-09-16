"""Master key provisioning module for KeySync Mini."""

import logging
from typing import Dict, List, Set, Any, Optional, Tuple
from datetime import datetime
from database import Database

logger = logging.getLogger(__name__)


class Provisioner:
    """Manage master key provisioning for out-of-authority keys."""

    def __init__(self, database: Database, config: Optional[Dict[str, Any]] = None):
        """Initialize provisioner with database and configuration."""
        self.db = database
        self.config = config or self._get_default_config()
        self.stats = {
            'keys_proposed': 0,
            'keys_activated': 0,
            'keys_skipped': 0,
            'strategy_used': {}
        }

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default provisioning configuration."""
        return {
            'strategy': 'mirror',  # mirror or namespaced
            'auto_approve': False,
            'namespace_prefix': 'MASTER'
        }

    def generate_master_key(self, source_system: str, source_key: str, normalized_key: str) -> str:
        """Generate a master key based on the configured strategy."""
        strategy = self.config.get('strategy', 'mirror')

        if strategy == 'mirror':
            # Use the normalized source key as the master key
            master_key = normalized_key
        elif strategy == 'namespaced':
            # Prefix with system identifier
            prefix = self.config.get('namespace_prefix', 'MASTER')
            master_key = f"{prefix}-{source_system}-{normalized_key}"
        else:
            # Fallback to mirror strategy
            logger.warning(f"Unknown strategy '{strategy}', using mirror strategy")
            master_key = normalized_key

        # Track strategy usage
        self.stats['strategy_used'][strategy] = self.stats['strategy_used'].get(strategy, 0) + 1

        return master_key

    def propose_master_keys(
        self,
        run_id: int,
        out_of_authority_keys: Dict[str, List[Tuple[str, str]]]
    ) -> List[Dict[str, Any]]:
        """Propose master keys for out-of-authority keys.

        Args:
            run_id: Current reconciliation run ID
            out_of_authority_keys: Dict of normalized_key -> [(system, original_key), ...]

        Returns:
            List of proposed master key records
        """
        proposed_keys = []

        for normalized_key, system_keys in out_of_authority_keys.items():
            # Check if master key already exists
            existing_masters = self.db.get_master_keys()
            existing_normalized = {
                master['master_key']: master
                for master in existing_masters
                if master['status'] in ['proposed', 'active']
            }

            if normalized_key in existing_normalized:
                logger.info(f"Master key already exists for '{normalized_key}', skipping")
                self.stats['keys_skipped'] += 1
                continue

            # Use first system as source (could be configurable)
            source_system, source_key = system_keys[0]

            # Generate master key
            master_key = self.generate_master_key(source_system, source_key, normalized_key)

            # Propose the master key
            try:
                master_key_id = self.db.propose_master_key(
                    run_id=run_id,
                    master_key=master_key,
                    source_system=source_system,
                    source_key=source_key,
                    strategy=self.config.get('strategy', 'mirror')
                )

                proposed_keys.append({
                    'master_key_id': master_key_id,
                    'master_key': master_key,
                    'source_system': source_system,
                    'source_key': source_key,
                    'normalized_key': normalized_key,
                    'affected_systems': [s for s, _ in system_keys],
                    'status': 'proposed'
                })

                self.stats['keys_proposed'] += 1
                logger.info(f"Proposed master key: '{master_key}' for normalized key '{normalized_key}'")

            except Exception as e:
                logger.error(f"Failed to propose master key for '{normalized_key}': {e}")

        return proposed_keys

    def activate_proposed_keys(self, run_id: int, auto_approve: Optional[bool] = None) -> int:
        """Activate proposed master keys from a run.

        Args:
            run_id: Run ID with proposed keys
            auto_approve: Override config auto_approve setting

        Returns:
            Number of keys activated
        """
        if auto_approve is None:
            auto_approve = self.config.get('auto_approve', False)

        if not auto_approve:
            logger.info("Auto-approve is disabled, keys remain in proposed state")
            return 0

        try:
            self.db.activate_master_keys(run_id)

            # Count activated keys
            activated = len([
                k for k in self.db.get_master_keys()
                if k.get('run_id') == run_id and k['status'] == 'active'
            ])

            self.stats['keys_activated'] += activated
            logger.info(f"Activated {activated} master keys from run {run_id}")
            return activated

        except Exception as e:
            logger.error(f"Failed to activate master keys: {e}")
            return 0

    def get_provisioning_summary(self, run_id: int) -> Dict[str, Any]:
        """Get summary of provisioning for a run."""
        all_masters = self.db.get_master_keys()

        run_masters = [k for k in all_masters if k.get('run_id') == run_id]

        summary = {
            'run_id': run_id,
            'total_proposed': len([k for k in run_masters if k['status'] == 'proposed']),
            'total_activated': len([k for k in run_masters if k['status'] == 'active']),
            'strategy': self.config.get('strategy', 'mirror'),
            'auto_approve': self.config.get('auto_approve', False),
            'stats': self.stats.copy()
        }

        return summary

    def get_statistics(self) -> Dict[str, Any]:
        """Get provisioning statistics."""
        return self.stats.copy()

    def reset_statistics(self):
        """Reset provisioning statistics."""
        self.stats = {
            'keys_proposed': 0,
            'keys_activated': 0,
            'keys_skipped': 0,
            'strategy_used': {}
        }