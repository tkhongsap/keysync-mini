"""Report generation module for KeySync Mini."""

import csv
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
# import pandas as pd  # Not used

from database import Database

logger = logging.getLogger(__name__)


class Reporter:
    """Generate CSV reports for reconciliation results."""

    def __init__(self, database: Database, output_dir: str = 'output'):
        """Initialize reporter with database and output directory."""
        self.db = database
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.reports_generated = []

    def generate_all_reports(
        self,
        run_id: int,
        reconciliation_results: Dict[str, Any]
    ) -> List[str]:
        """Generate all required CSV reports."""
        self.reports_generated = []

        # 1. Reconciliation Summary
        summary_file = self.generate_reconciliation_summary(run_id, reconciliation_results)
        self.reports_generated.append(summary_file)

        # 2. Keys missing in A (need master key provisioning)
        if reconciliation_results.get('discrepancies'):
            missing_in_a_file = self.generate_missing_in_a_report(
                run_id,
                reconciliation_results['discrepancies']
            )
            self.reports_generated.append(missing_in_a_file)

        # 3. Keys missing from systems (propagation gaps)
        if reconciliation_results.get('discrepancies'):
            missing_from_systems_file = self.generate_missing_from_systems_report(
                run_id,
                reconciliation_results['discrepancies']
            )
            self.reports_generated.append(missing_from_systems_file)

        # 4. Master key registry
        registry_file = self.generate_master_key_registry(run_id)
        self.reports_generated.append(registry_file)

        # 5. Audit log
        audit_file = self.generate_audit_log(run_id)
        self.reports_generated.append(audit_file)

        # 6. Optional: Trend analysis (if enabled)
        if reconciliation_results.get('enable_trend_analysis'):
            trend_file = self.generate_trend_analysis(run_id)
            if trend_file:
                self.reports_generated.append(trend_file)

        logger.info(f"Generated {len(self.reports_generated)} reports for run {run_id}")
        return self.reports_generated

    def generate_reconciliation_summary(
        self,
        run_id: int,
        results: Dict[str, Any]
    ) -> str:
        """Generate reconciliation summary CSV with statistics."""
        file_path = self.output_dir / 'reconciliation_summary.csv'

        comparison = results.get('comparison', {})
        stats = comparison.get('statistics', {})
        discrepancies = results.get('discrepancies', {}).get('summary', {})

        # Prepare summary data
        summary_rows = [
            ['Metric', 'Value', 'Timestamp'],
            ['Run ID', run_id, datetime.now().isoformat()],
            ['Total Unique Keys', stats.get('total_unique_keys', 0), datetime.now().isoformat()],
            ['Keys in System A', stats.get('keys_in_a', 0), datetime.now().isoformat()],
            ['Keys Only in A (Propagation Gaps)', stats.get('keys_only_in_a', 0), datetime.now().isoformat()],
            ['Keys Missing in A (Out of Authority)', stats.get('keys_missing_in_a', 0), datetime.now().isoformat()],
            ['Keys in All Systems', stats.get('keys_in_all_systems', 0), datetime.now().isoformat()],
            ['Overall Match Rate', f"{stats.get('match_percentage', 0):.1f}%", datetime.now().isoformat()],
            ['Total Out of Authority Keys', discrepancies.get('total_out_of_authority', 0), datetime.now().isoformat()],
            ['Total Propagation Gaps', discrepancies.get('total_propagation_gaps', 0), datetime.now().isoformat()],
            ['Total Duplicate Groups', discrepancies.get('total_duplicate_groups', 0), datetime.now().isoformat()],
        ]

        # Add system-specific counts
        system_counts = stats.get('system_counts', {})
        for system, count in sorted(system_counts.items()):
            summary_rows.append([
                f'Keys in System {system}',
                count,
                datetime.now().isoformat()
            ])

        # Write CSV
        with open(file_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(summary_rows)

        logger.info(f"Generated reconciliation summary: {file_path}")
        return str(file_path)

    def generate_missing_in_a_report(
        self,
        run_id: int,
        discrepancies: Dict[str, Any]
    ) -> str:
        """Generate report of keys missing in A that need master key provisioning."""
        file_path = self.output_dir / 'diff_missing_in_A.csv'

        out_of_authority = discrepancies.get('out_of_authority_keys', {})

        rows = []
        rows.append([
            'Normalized Key',
            'Source System',
            'Original Key',
            'Proposed Master Key',
            'Provisioning Strategy',
            'Status',
            'Timestamp'
        ])

        # Get proposed master keys from database
        master_keys = self.db.get_master_keys()
        master_key_map = {
            mk['source_key']: mk
            for mk in master_keys
            if mk.get('run_id') == run_id
        }

        for normalized_key, source_systems in out_of_authority.items():
            for system_name, original_key in source_systems:
                master_info = master_key_map.get(original_key, {})

                rows.append([
                    normalized_key,
                    system_name,
                    original_key,
                    master_info.get('master_key', f'PROPOSED-{normalized_key}'),
                    master_info.get('provisioning_strategy', 'mirror'),
                    master_info.get('status', 'pending'),
                    datetime.now().isoformat()
                ])

        # Write CSV
        with open(file_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(rows)

        logger.info(f"Generated missing in A report: {file_path} ({len(rows)-1} keys)")
        return str(file_path)

    def generate_missing_from_systems_report(
        self,
        run_id: int,
        discrepancies: Dict[str, Any]
    ) -> str:
        """Generate report of keys missing from specific systems (propagation gaps)."""
        file_path = self.output_dir / 'diff_missing_from_system.csv'

        propagation_gaps = discrepancies.get('propagation_gaps', {})

        rows = []
        rows.append([
            'System',
            'Normalized Key',
            'Present in System A',
            'Action Required',
            'Timestamp'
        ])

        for system_name, missing_keys in propagation_gaps.items():
            for key in missing_keys:
                rows.append([
                    system_name,
                    key,
                    'Yes',
                    'Propagate from A',
                    datetime.now().isoformat()
                ])

        # Write CSV
        with open(file_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(rows)

        logger.info(f"Generated missing from systems report: {file_path} ({len(rows)-1} gaps)")
        return str(file_path)

    def generate_master_key_registry(self, run_id: int) -> str:
        """Generate master key registry CSV."""
        file_path = self.output_dir / 'master_key_registry.csv'

        # Get all master keys
        master_keys = self.db.get_master_keys()

        rows = []
        rows.append([
            'Master Key ID',
            'Master Key',
            'Source System',
            'Source Key',
            'Status',
            'Provisioning Strategy',
            'Created At',
            'Activated At',
            'Run ID'
        ])

        for mk in master_keys:
            rows.append([
                mk['master_key_id'],
                mk['master_key'],
                mk['source_system'],
                mk['source_key'],
                mk['status'],
                mk['provisioning_strategy'],
                mk['created_at'],
                mk.get('activated_at', ''),
                mk.get('run_id', '')
            ])

        # Write CSV
        with open(file_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(rows)

        logger.info(f"Generated master key registry: {file_path} ({len(rows)-1} keys)")
        return str(file_path)

    def generate_audit_log(self, run_id: int) -> str:
        """Generate audit log CSV for the run."""
        file_path = self.output_dir / 'audit_log.csv'

        # Query audit log from database
        cursor = self.db.conn.execute("""
            SELECT * FROM audit_log
            WHERE run_id = ?
            ORDER BY timestamp DESC
        """, (run_id,))

        rows = []
        rows.append([
            'Audit ID',
            'Timestamp',
            'Event Type',
            'Event Details',
            'System',
            'Key',
            'Action Taken',
            'Result'
        ])

        for row in cursor:
            rows.append([
                row['audit_id'],
                row['timestamp'],
                row['event_type'],
                row['event_details'],
                row['system_name'] or '',
                row['key_value'] or '',
                row['action_taken'] or '',
                row['result'] or ''
            ])

        # Write CSV
        with open(file_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(rows)

        logger.info(f"Generated audit log: {file_path} ({len(rows)-1} events)")
        return str(file_path)

    def generate_trend_analysis(self, run_id: int) -> Optional[str]:
        """Generate optional trend analysis report."""
        try:
            file_path = self.output_dir / 'trend_analysis.csv'

            # Query historical runs
            cursor = self.db.conn.execute("""
                SELECT run_id, run_timestamp, stats_json
                FROM reconciliation_runs
                WHERE status = 'completed'
                ORDER BY run_timestamp DESC
                LIMIT 30
            """)

            rows = []
            rows.append([
                'Run ID',
                'Timestamp',
                'Total Keys',
                'Match Rate',
                'Out of Authority',
                'Propagation Gaps',
                'Trend'
            ])

            prev_match_rate = None
            for row in cursor:
                stats = json.loads(row['stats_json'] or '{}')

                match_rate = stats.get('match_percentage', 0)
                trend = ''
                if prev_match_rate is not None:
                    if match_rate > prev_match_rate:
                        trend = '↑ Improving'
                    elif match_rate < prev_match_rate:
                        trend = '↓ Degrading'
                    else:
                        trend = '→ Stable'

                rows.append([
                    row['run_id'],
                    row['run_timestamp'],
                    stats.get('total_unique_keys', 0),
                    f"{match_rate:.1f}%",
                    stats.get('keys_missing_in_a', 0),
                    stats.get('keys_only_in_a', 0),
                    trend
                ])

                prev_match_rate = match_rate

            if len(rows) > 1:
                # Write CSV
                with open(file_path, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerows(rows)

                logger.info(f"Generated trend analysis: {file_path}")
                return str(file_path)

        except Exception as e:
            logger.warning(f"Could not generate trend analysis: {e}")

        return None

    def write_json_report(self, file_name: str, data: Dict[str, Any]):
        """Write a JSON report for detailed analysis."""
        file_path = self.output_dir / file_name

        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)

        logger.info(f"Generated JSON report: {file_path}")
        return str(file_path)