"""Mock data generator for KeySync Mini testing."""

import random
import csv
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, List, Dict, Set, Tuple, Optional, Union
import logging

logger = logging.getLogger(__name__)


class MockDataGenerator:
    """Generate synthetic CSV data for testing reconciliation scenarios."""

    def __init__(self, seed: int = 42):
        """Initialize generator with seed for reproducibility."""
        self.seed = seed
        random.seed(seed)
        self.systems = ['A', 'B', 'C', 'D', 'E']

    def generate_business_key(self, key_type: str, index: int, variation: bool = False) -> str:
        """Generate realistic business keys with optional variations."""
        if variation:
            # Add variations for testing normalization
            variations = [
                lambda s: s.lower(),
                lambda s: s.upper(),
                lambda s: f" {s} ",
                lambda s: s.replace("-", "_"),
                lambda s: s.replace("-", "  "),
            ]
            transform = random.choice(variations)
        else:
            transform = lambda s: s

        if key_type == 'customer':
            base = f"CUST-{str(index).zfill(5)}"
        elif key_type == 'product':
            letters = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=3))
            base = f"PROD-{letters}-{str(index).zfill(3)}"
        elif key_type == 'transaction':
            year = 2023 + (index // 1000)
            base = f"TXN-{year}-{str(index % 1000).zfill(3)}"
        elif key_type == 'order':
            base = f"ORD-{random.randint(100000, 999999)}"
        else:
            base = f"KEY-{str(index).zfill(6)}"

        return transform(base)

    def generate_temporal_pattern(self, days_history: int = 30) -> str:
        """Generate last_seen_at timestamp for temporal tracking."""
        # Use a fixed base time for reproducibility when seed is set
        base_time = datetime(2025, 1, 1, 12, 0, 0)
        days_ago = random.randint(0, days_history)
        hours_ago = random.randint(0, 23)
        timestamp = base_time - timedelta(days=days_ago, hours=hours_ago)
        return timestamp.isoformat()

    def create_scenario_distribution(self, scenario: str, total_keys: int) -> Dict[str, float]:
        """Define key distribution based on scenario."""
        distributions = {
            'normal': {
                'common': 0.80,  # Keys in all systems
                'missing_in_a': 0.10,  # Keys in B/C/D/E but not A
                'missing_from_systems': 0.10,  # Keys in A but missing from others
            },
            'drift': {
                'common': 0.60,
                'missing_in_a': 0.20,
                'missing_from_systems': 0.20,
            },
            'failure': {
                'common': 0.50,
                'missing_in_a': 0.25,
                'missing_from_systems': 0.25,
            },
            'recovery': {
                'common': 0.75,
                'missing_in_a': 0.12,
                'missing_from_systems': 0.13,
            }
        }
        return distributions.get(scenario, distributions['normal'])

    def generate_keys_for_scenario(
        self,
        scenario: str = 'normal',
        keys_per_system: int = 1000,
        duplicate_rate: float = 0.01,
        corruption_rate: float = 0.01
    ) -> Dict[str, List[Dict[str, str]]]:
        """Generate keys for all systems based on scenario."""
        distribution = self.create_scenario_distribution(scenario, keys_per_system)

        # Calculate key counts for each category
        common_count = int(keys_per_system * distribution['common'])
        missing_in_a_count = int(keys_per_system * distribution['missing_in_a'])
        missing_from_systems_count = int(keys_per_system * distribution['missing_from_systems'])

        # Generate common keys (present in all systems)
        common_keys = []
        key_types = ['customer', 'product', 'transaction', 'order']
        for i in range(common_count):
            key_type = key_types[i % len(key_types)]
            common_keys.append(self.generate_business_key(key_type, i))

        # Generate keys missing in A (out-of-authority)
        missing_in_a_keys = []
        for i in range(missing_in_a_count):
            key_type = key_types[i % len(key_types)]
            missing_in_a_keys.append(
                self.generate_business_key(key_type, i + common_count)
            )

        # Generate keys only in A (propagation gaps)
        a_only_keys = []
        for i in range(missing_from_systems_count):
            key_type = key_types[i % len(key_types)]
            a_only_keys.append(
                self.generate_business_key(key_type, i + common_count + missing_in_a_count)
            )

        # Build system datasets
        system_data = {}

        # System A: common keys + A-only keys
        system_a_keys = common_keys + a_only_keys
        random.shuffle(system_a_keys)

        # Other systems: common keys + missing-in-A keys
        for system in self.systems:
            if system == 'A':
                keys = system_a_keys.copy()
            else:
                # Each system gets common keys
                keys = common_keys.copy()

                # Add subset of missing_in_a_keys (not all systems have all of them)
                if missing_in_a_keys:
                    subset_size = int(len(missing_in_a_keys) * random.uniform(0.7, 1.0))
                    keys.extend(random.sample(missing_in_a_keys, subset_size))

                # Randomly remove some common keys to simulate propagation gaps
                if random.random() < 0.3:  # 30% chance to have propagation gaps
                    remove_count = int(len(a_only_keys) * random.uniform(0.5, 1.0))
                    for _ in range(min(remove_count, len(keys) // 10)):
                        if keys:
                            keys.pop(random.randint(0, len(keys) - 1))

            # Add variations for normalization testing
            final_keys = []
            for key in keys:
                # Add variation to some keys
                if random.random() < 0.2:  # 20% chance of variation
                    key = self.generate_business_key('', 0, variation=True).replace("KEY-000000", key)

                # Add duplicates
                if random.random() < duplicate_rate:
                    final_keys.append(key)

                # Simulate corruption
                if random.random() < corruption_rate:
                    key = key + "!@#$%"

                final_keys.append(key)

            random.shuffle(final_keys)

            # Create records with metadata
            records = []
            for key in final_keys:
                record = {
                    'key': key,
                    'last_seen_at': self.generate_temporal_pattern(),
                    'system': system,
                    'status': 'active'
                }
                records.append(record)

            system_data[system] = records

        logger.info(f"Generated data for scenario '{scenario}':")
        for system, records in system_data.items():
            logger.info(f"  System {system}: {len(records)} keys")

        return system_data

    def inject_failures(
        self,
        system_data: Dict[str, List[Dict[str, str]]],
        failure_type: str = 'corruption'
    ) -> Dict[str, List[Dict[str, str]]]:
        """Inject specific failure patterns for testing."""
        if failure_type == 'corruption':
            # Corrupt random keys in random systems
            for system in random.sample(list(system_data.keys()), 2):
                if system_data[system]:
                    for _ in range(min(5, len(system_data[system]))):
                        idx = random.randint(0, len(system_data[system]) - 1)
                        system_data[system][idx]['key'] = "CORRUPTED_" + str(random.randint(1000, 9999))

        elif failure_type == 'missing_file':
            # Remove one system's data entirely
            system_to_remove = random.choice([s for s in self.systems if s != 'A'])
            system_data[system_to_remove] = []

        elif failure_type == 'massive_duplication':
            # Add massive duplicates to one system
            system = random.choice(self.systems)
            if system_data[system]:
                original = system_data[system].copy()
                for _ in range(3):  # Triple the data with duplicates
                    system_data[system].extend(original)

        return system_data

    def write_csv_files(
        self,
        system_data: Dict[str, List[Dict[str, str]]],
        output_dir: str = 'input',
        write_stats: bool = True,
        scenario: Optional[str] = None,
        timestamp: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Write system data to CSV files and optionally emit stats."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        for system, records in system_data.items():
            file_path = output_path / f"{system}.csv"

            if records:
                with open(file_path, 'w', newline='') as f:
                    fieldnames = ['key', 'last_seen_at', 'system', 'status']
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(records)
                logger.info(f"Wrote {len(records)} records to {file_path}")
            else:
                # Create empty file for missing system scenario
                open(file_path, 'w').close()
                logger.info(f"Created empty file at {file_path}")

        if write_stats:
            stats = self._build_generation_stats(
                system_data,
                scenario=scenario or 'unspecified',
                timestamp=timestamp
            )
            stats_file = output_path / 'generation_stats.json'
            self._write_stats_file(stats, stats_file)
            return stats

        return None

    def generate_test_data(
        self,
        scenario: str = 'normal',
        keys_per_system: int = 1000,
        output_dir: str = 'input',
        inject_failures: Union[bool, float] = 0.0,
        corruption_rate: float = 0.01
    ) -> Dict[str, Any]:
        """Main method to generate test data."""
        logger.info(f"Generating test data: scenario={scenario}, keys_per_system={keys_per_system}")

        # Generate base data
        system_data = self.generate_keys_for_scenario(
            scenario=scenario,
            keys_per_system=keys_per_system,
            corruption_rate=corruption_rate
        )

        # Optionally inject failures
        if isinstance(inject_failures, bool):
            failure_chance = 1.0 if inject_failures else 0.0
        else:
            try:
                failure_chance = float(inject_failures)
            except (TypeError, ValueError):
                logger.warning(
                    "Invalid failure injection value %r; defaulting to 0", inject_failures
                )
                failure_chance = 0.0
            failure_chance = max(0.0, min(1.0, failure_chance))

        if failure_chance > 0:
            roll = random.random()
            logger.debug(
                "Failure injection check: chance=%.3f roll=%.3f", failure_chance, roll
            )
            if roll < failure_chance:
                failure_types = ['corruption', 'missing_file', 'massive_duplication']
                failure_type = random.choice(failure_types)
                logger.info(
                    "Injecting failure type: %s (chance %.2f%%)",
                    failure_type,
                    failure_chance * 100,
                )
                system_data = self.inject_failures(system_data, failure_type)

        # Write to CSV files
        self.write_csv_files(system_data, output_dir, write_stats=False)

        # Generate summary statistics
        stats = self._build_generation_stats(
            system_data,
            scenario=scenario,
            timestamp=datetime(2025, 1, 1, 12, 0, 0).isoformat(),
        )

        # Write stats file
        stats_file = Path(output_dir) / 'generation_stats.json'
        self._write_stats_file(stats, stats_file)

        logger.info(f"Data generation complete. Stats written to {stats_file}")
        return stats

    def _build_generation_stats(
        self,
        system_data: Dict[str, List[Dict[str, str]]],
        scenario: str,
        timestamp: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Construct the generation statistics payload."""
        stats = {
            'scenario': scenario,
            'seed': self.seed,
            'timestamp': timestamp or datetime(2025, 1, 1, 12, 0, 0).isoformat(),
            'systems': {},
        }

        for system, records in system_data.items():
            unique_keys = set(r['key'] for r in records)
            stats['systems'][system] = {
                'total_records': len(records),
                'unique_keys': len(unique_keys),
                'duplicates': len(records) - len(unique_keys),
            }

        return stats

    def _write_stats_file(self, stats: Dict[str, Any], stats_path: Path):
        """Persist generation statistics to disk."""
        with open(stats_path, 'w') as f:
            json.dump(stats, f, indent=2)

        logger.info(f"Data generation statistics written to {stats_path}")


def main():
    """CLI entry point for standalone mock data generation."""
    import argparse
    from logger import setup_logging

    parser = argparse.ArgumentParser(description='Generate mock data for KeySync testing')
    parser.add_argument('--scenario', choices=['normal', 'drift', 'failure', 'recovery'],
                       default='normal', help='Test scenario to generate')
    parser.add_argument('--keys', type=int, default=1000,
                       help='Number of keys per system')
    parser.add_argument('--seed', type=int, default=42,
                       help='Random seed for reproducibility')
    parser.add_argument('--output', default='input',
                       help='Output directory for CSV files')
    parser.add_argument('--inject-failures', action='store_true',
                       help='Inject random failures for testing')

    args = parser.parse_args()

    setup_logging()

    generator = MockDataGenerator(seed=args.seed)
    generator.generate_test_data(
        scenario=args.scenario,
        keys_per_system=args.keys,
        output_dir=args.output,
        inject_failures=args.inject_failures
    )


if __name__ == '__main__':
    main()