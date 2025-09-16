"""Key comparison engine for KeySync Mini."""

import logging
from typing import Dict, List, Set, Tuple, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
# import pandas as pd  # Not used in core functionality
from pathlib import Path
import csv

from normalizer import Normalizer

logger = logging.getLogger(__name__)


class Comparator:
    """Compare keys across multiple systems after normalization."""

    def __init__(self, normalizer: Normalizer, parallel: bool = True, batch_size: int = 1000):
        """Initialize comparator with normalizer."""
        self.normalizer = normalizer
        self.parallel = parallel
        self.batch_size = batch_size
        self.stats_lock = Lock()
        self.stats = self._reset_stats()

    def _reset_stats(self) -> Dict[str, Any]:
        """Reset comparison statistics."""
        return {
            'total_keys_processed': 0,
            'systems_compared': [],
            'duplicates_found': {},
            'processing_errors': []
        }

    def load_system_data(self, file_path: str) -> Tuple[List[str], List[Dict[str, str]]]:
        """Load keys from a CSV file."""
        keys = []
        records = []

        try:
            path = Path(file_path)
            if not path.exists():
                logger.warning(f"File not found: {file_path}")
                return keys, records

            with open(path, 'r', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if 'key' in row and row['key']:
                        keys.append(row['key'])
                        records.append(row)

            logger.info(f"Loaded {len(keys)} keys from {file_path}")

        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
            self.stats['processing_errors'].append({
                'file': file_path,
                'error': str(e)
            })

        return keys, records

    def normalize_system_keys(self, system_name: str, keys: List[str]) -> Dict[str, Set[str]]:
        """Normalize keys from a system and track duplicates."""
        normalized_map = {}  # normalized -> set of original keys

        for key in keys:
            normalized = self.normalizer.normalize(key)
            if normalized not in normalized_map:
                normalized_map[normalized] = set()
            normalized_map[normalized].add(key)

        # Identify duplicates (multiple original keys mapping to same normalized key)
        duplicates = {
            norm_key: orig_keys
            for norm_key, orig_keys in normalized_map.items()
            if len(orig_keys) > 1
        }

        if duplicates:
            with self.stats_lock:
                self.stats['duplicates_found'][system_name] = duplicates
                logger.info(f"Found {len(duplicates)} duplicate groups in system {system_name}")

        return normalized_map

    def process_system_batch(self, system_name: str, keys_batch: List[str]) -> Dict[str, Set[str]]:
        """Process a batch of keys for a system."""
        return self.normalize_system_keys(system_name, keys_batch)

    def compare_all_systems(self, system_files: Dict[str, str]) -> Dict[str, Any]:
        """Compare all systems and identify discrepancies."""
        results = {
            'system_keys': {},  # system -> {normalized_key -> set(original_keys)}
            'all_keys': {},     # All unique normalized keys across systems
            'comparison': {
                'keys_only_in_a': set(),
                'keys_missing_in_a': set(),
                'keys_in_all_systems': set(),
                'system_specific_gaps': {}  # system -> missing keys
            },
            'statistics': {}
        }

        # Load and normalize all systems
        system_data = {}

        if self.parallel:
            # Parallel processing
            with ThreadPoolExecutor(max_workers=5) as executor:
                future_to_system = {}

                for system_name, file_path in system_files.items():
                    future = executor.submit(self.load_and_normalize_system, system_name, file_path)
                    future_to_system[future] = system_name

                for future in as_completed(future_to_system):
                    system_name = future_to_system[future]
                    try:
                        normalized_map, records = future.result()
                        system_data[system_name] = {
                            'normalized': normalized_map,
                            'records': records
                        }
                        results['system_keys'][system_name] = normalized_map
                    except Exception as e:
                        logger.error(f"Error processing system {system_name}: {e}")
        else:
            # Sequential processing
            for system_name, file_path in system_files.items():
                normalized_map, records = self.load_and_normalize_system(system_name, file_path)
                system_data[system_name] = {
                    'normalized': normalized_map,
                    'records': records
                }
                results['system_keys'][system_name] = normalized_map

        # Perform comparison
        if 'A' not in system_data:
            logger.error("System A data not found - cannot perform comparison")
            return results

        # Get all unique normalized keys
        all_keys = set()
        for system_name, data in system_data.items():
            all_keys.update(data['normalized'].keys())

        results['all_keys'] = all_keys

        # System A keys (authoritative)
        a_keys = set(system_data['A']['normalized'].keys())

        # Keys only in A (propagation gaps)
        keys_only_in_a = a_keys.copy()
        for system_name in ['B', 'C', 'D', 'E']:
            if system_name in system_data:
                keys_only_in_a -= set(system_data[system_name]['normalized'].keys())

        results['comparison']['keys_only_in_a'] = keys_only_in_a

        # Keys missing in A (out-of-authority)
        keys_in_others = set()
        for system_name in ['B', 'C', 'D', 'E']:
            if system_name in system_data:
                keys_in_others.update(system_data[system_name]['normalized'].keys())

        keys_missing_in_a = keys_in_others - a_keys
        results['comparison']['keys_missing_in_a'] = keys_missing_in_a

        # Keys present in all systems
        keys_in_all = a_keys.copy()
        for system_name in ['B', 'C', 'D', 'E']:
            if system_name in system_data:
                keys_in_all &= set(system_data[system_name]['normalized'].keys())

        results['comparison']['keys_in_all_systems'] = keys_in_all

        # System-specific gaps (keys in A but missing from specific systems)
        for system_name in ['B', 'C', 'D', 'E']:
            if system_name in system_data:
                system_keys = set(system_data[system_name]['normalized'].keys())
                missing_from_system = a_keys - system_keys
                results['comparison']['system_specific_gaps'][system_name] = missing_from_system

        # Calculate statistics
        total_unique = len(all_keys)
        results['statistics'] = {
            'total_unique_keys': total_unique,
            'keys_in_a': len(a_keys),
            'keys_only_in_a': len(keys_only_in_a),
            'keys_missing_in_a': len(keys_missing_in_a),
            'keys_in_all_systems': len(keys_in_all),
            'match_percentage': (len(keys_in_all) / total_unique * 100) if total_unique > 0 else 0,
            'system_counts': {
                system: len(data['normalized'])
                for system, data in system_data.items()
            },
            'duplicates': self.stats['duplicates_found']
        }

        logger.info(f"Comparison complete: {results['statistics']['match_percentage']:.1f}% match rate")

        return results

    def load_and_normalize_system(self, system_name: str, file_path: str) -> Tuple[Dict[str, Set[str]], List[Dict]]:
        """Load and normalize keys for a system."""
        keys, records = self.load_system_data(file_path)

        with self.stats_lock:
            self.stats['total_keys_processed'] += len(keys)
            self.stats['systems_compared'].append(system_name)

        # Process in batches
        normalized_map = {}
        for i in range(0, len(keys), self.batch_size):
            batch = keys[i:i + self.batch_size]
            batch_map = self.normalize_system_keys(system_name, batch)

            # Merge batch results
            for norm_key, orig_keys in batch_map.items():
                if norm_key not in normalized_map:
                    normalized_map[norm_key] = set()
                normalized_map[norm_key].update(orig_keys)

        return normalized_map, records

    def generate_comparison_summary(self, results: Dict[str, Any]) -> Dict[str, List]:
        """Generate a summary of comparison results."""
        stats = results['statistics']

        summary_data = {
            'Metric': [
                'Total Unique Keys',
                'Keys in System A',
                'Keys Only in A (Propagation Gaps)',
                'Keys Missing in A (Out of Authority)',
                'Keys in All Systems',
                'Overall Match Rate'
            ],
            'Value': [
                stats['total_unique_keys'],
                stats['keys_in_a'],
                stats['keys_only_in_a'],
                stats['keys_missing_in_a'],
                stats['keys_in_all_systems'],
                f"{stats['match_percentage']:.1f}%"
            ]
        }

        # Add system-specific counts
        for system, count in stats['system_counts'].items():
            summary_data['Metric'].append(f'Keys in System {system}')
            summary_data['Value'].append(count)

        return summary_data