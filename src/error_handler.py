"""Error handling and resilience module for KeySync Mini."""

import logging
import time
import csv
from pathlib import Path
from typing import Any, Callable, Optional, Dict, List
from functools import wraps

logger = logging.getLogger(__name__)


class ReconciliationError(Exception):
    """Base exception for reconciliation errors."""
    pass


class DataValidationError(ReconciliationError):
    """Exception for data validation errors."""
    pass


class SystemUnavailableError(ReconciliationError):
    """Exception for system availability issues."""
    pass


class CheckpointRecoveryError(ReconciliationError):
    """Exception for checkpoint recovery failures."""
    pass


class ErrorHandler:
    """Centralized error handling and recovery mechanisms."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize error handler with configuration."""
        self.config = config or self._get_default_config()
        self.error_log = []
        self.recovery_attempts = {}

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default error handling configuration."""
        return {
            'on_missing_file': 'skip',  # skip, fail
            'on_corrupt_data': 'log',   # log, fail, skip
            'retry_attempts': 3,
            'retry_delay_seconds': 5,
            'max_errors_before_fail': 100,
            'enable_partial_processing': True
        }

    def handle_missing_file(self, file_path: str, system_name: str) -> Optional[List]:
        """Handle missing input file based on configuration."""
        policy = self.config.get('on_missing_file', 'skip')

        self.error_log.append({
            'type': 'missing_file',
            'file': file_path,
            'system': system_name,
            'action': policy
        })

        if policy == 'skip':
            logger.warning(f"File not found for system {system_name}: {file_path} - skipping")
            return []  # Return empty data
        elif policy == 'fail':
            raise SystemUnavailableError(f"Required file missing: {file_path}")
        else:
            logger.error(f"Unknown policy '{policy}' for missing file")
            return []

    def handle_corrupt_data(self, file_path: str, row_num: int, error: Exception) -> bool:
        """Handle corrupted CSV data based on configuration."""
        policy = self.config.get('on_corrupt_data', 'log')

        self.error_log.append({
            'type': 'corrupt_data',
            'file': file_path,
            'row': row_num,
            'error': str(error),
            'action': policy
        })

        if policy == 'log':
            logger.warning(f"Corrupt data in {file_path} row {row_num}: {error}")
            return True  # Continue processing
        elif policy == 'skip':
            logger.debug(f"Skipping corrupt row {row_num} in {file_path}")
            return True  # Continue processing
        elif policy == 'fail':
            raise DataValidationError(f"Corrupt data in {file_path} row {row_num}: {error}")
        else:
            logger.error(f"Unknown policy '{policy}' for corrupt data")
            return True

    def validate_csv_file(self, file_path: str) -> Dict[str, Any]:
        """Validate CSV file and return validation results."""
        validation_result = {
            'valid': True,
            'total_rows': 0,
            'valid_rows': 0,
            'error_rows': [],
            'warnings': []
        }

        path = Path(file_path)
        if not path.exists():
            validation_result['valid'] = False
            validation_result['warnings'].append('File does not exist')
            return validation_result

        try:
            with open(path, 'r', newline='') as f:
                reader = csv.DictReader(f)

                # Check for required headers
                if 'key' not in reader.fieldnames:
                    validation_result['warnings'].append("Missing 'key' column")

                for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is 1)
                    validation_result['total_rows'] += 1

                    try:
                        # Validate row has key field
                        if not row.get('key'):
                            validation_result['error_rows'].append({
                                'row': row_num,
                                'error': 'Empty key field'
                            })
                        else:
                            validation_result['valid_rows'] += 1

                    except Exception as e:
                        validation_result['error_rows'].append({
                            'row': row_num,
                            'error': str(e)
                        })

        except Exception as e:
            validation_result['valid'] = False
            validation_result['warnings'].append(f"File read error: {e}")

        # Determine if file is usable
        if validation_result['valid_rows'] == 0 and validation_result['total_rows'] > 0:
            validation_result['valid'] = False

        return validation_result

    def with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with retry logic."""
        max_attempts = self.config.get('retry_attempts', 3)
        delay = self.config.get('retry_delay_seconds', 5)

        func_name = func.__name__
        if func_name not in self.recovery_attempts:
            self.recovery_attempts[func_name] = 0

        last_error = None
        for attempt in range(1, max_attempts + 1):
            try:
                result = func(*args, **kwargs)
                if attempt > 1:
                    logger.info(f"Successfully executed {func_name} after {attempt} attempts")
                return result

            except Exception as e:
                last_error = e
                self.recovery_attempts[func_name] += 1

                if attempt < max_attempts:
                    logger.warning(f"Attempt {attempt}/{max_attempts} failed for {func_name}: {e}")
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    logger.error(f"All {max_attempts} attempts failed for {func_name}")

        raise last_error

    def handle_partial_system_availability(
        self,
        available_systems: List[str],
        required_systems: List[str]
    ) -> bool:
        """Determine if processing should continue with partial systems."""
        if 'A' not in available_systems:
            logger.error("System A is required but not available")
            return False

        missing = set(required_systems) - set(available_systems)
        if missing:
            logger.warning(f"Missing systems: {missing}")

            if self.config.get('enable_partial_processing', True):
                logger.info("Continuing with partial system availability")
                return True
            else:
                logger.error("Partial processing disabled - all systems required")
                return False

        return True

    def recover_from_checkpoint(self, checkpoint_data: Dict[str, Any]) -> Dict[str, Any]:
        """Attempt to recover from a saved checkpoint."""
        try:
            logger.info(f"Attempting recovery from checkpoint: {list(checkpoint_data.keys())}")

            # Validate checkpoint data
            if not checkpoint_data:
                raise CheckpointRecoveryError("No checkpoint data available")

            # Find the latest valid checkpoint
            latest_checkpoint = None
            for checkpoint_name in reversed(list(checkpoint_data.keys())):
                checkpoint = checkpoint_data[checkpoint_name]
                if self._validate_checkpoint(checkpoint):
                    latest_checkpoint = checkpoint_name
                    break

            if not latest_checkpoint:
                raise CheckpointRecoveryError("No valid checkpoint found")

            logger.info(f"Recovering from checkpoint: {latest_checkpoint}")
            return {
                'checkpoint_name': latest_checkpoint,
                'checkpoint_data': checkpoint_data[latest_checkpoint],
                'recovery_successful': True
            }

        except Exception as e:
            logger.error(f"Checkpoint recovery failed: {e}")
            raise CheckpointRecoveryError(f"Recovery failed: {e}")

    def _validate_checkpoint(self, checkpoint: Dict[str, Any]) -> bool:
        """Validate checkpoint data integrity."""
        required_fields = ['timestamp', 'data_summary']
        return all(field in checkpoint for field in required_fields)

    def create_error_report(self, output_dir: str = 'output') -> str:
        """Create an error report CSV file."""
        if not self.error_log:
            logger.info("No errors to report")
            return None

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        file_path = output_path / 'error_report.csv'

        with open(file_path, 'w', newline='') as f:
            fieldnames = ['timestamp', 'type', 'file', 'system', 'row', 'error', 'action']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            from datetime import datetime
            for error in self.error_log:
                error['timestamp'] = datetime.now().isoformat()
                writer.writerow({k: error.get(k, '') for k in fieldnames})

        logger.info(f"Error report created: {file_path}")
        return str(file_path)

    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of all errors encountered."""
        summary = {
            'total_errors': len(self.error_log),
            'errors_by_type': {},
            'recovery_attempts': self.recovery_attempts.copy(),
            'can_continue': len(self.error_log) < self.config.get('max_errors_before_fail', 100)
        }

        for error in self.error_log:
            error_type = error.get('type', 'unknown')
            summary['errors_by_type'][error_type] = \
                summary['errors_by_type'].get(error_type, 0) + 1

        return summary


def resilient_operation(error_handler: ErrorHandler):
    """Decorator for making operations resilient with error handling."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return error_handler.with_retry(func, *args, **kwargs)
            except Exception as e:
                logger.error(f"Resilient operation failed: {func.__name__} - {e}")
                error_handler.error_log.append({
                    'type': 'operation_failure',
                    'function': func.__name__,
                    'error': str(e)
                })
                raise

        return wrapper
    return decorator