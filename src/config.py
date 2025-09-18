"""Configuration management for KeySync Mini."""

import copy
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union

logger = logging.getLogger(__name__)


class Config:
    """Configuration manager for KeySync Mini."""

    def __init__(self, config_file: Optional[str] = None):
        """Initialize configuration from YAML file or defaults."""
        initial_path = Path(config_file or 'keysync-config.yaml').expanduser()
        if not initial_path.is_absolute():
            initial_path = (Path.cwd() / initial_path).resolve()
        else:
            initial_path = initial_path.resolve()

        self.config_path = initial_path
        self.config_file = str(self.config_path)
        self._config_dir = self.config_path.parent

        self._defaults = self._get_default_config()
        self.config = self._load_config()
        self._validate_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        config_path = self.config_path

        # Start with defaults so missing sections still have sensible values
        config = copy.deepcopy(self._defaults)

        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    user_config = yaml.safe_load(f) or {}
                logger.info(f"Loaded configuration from {config_path}")
                self._deep_update(config, user_config)
                return config
            except Exception as e:
                logger.error(f"Failed to load config from {config_path}: {e}")
                logger.info("Using default configuration")
                return config
        else:
            logger.info(f"Config file {config_path} not found, using defaults")
            return config

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            'schedule': '0 2 * * *',
            'normalize': {
                'uppercase': True,
                'trim_whitespace': True,
                'strip_non_alnum': True,
                'collapse_delims': '-',
                'left_pad_numbers': True,
                'pad_length': 6
            },
            'provisioning': {
                'strategy': 'mirror',
                'auto_approve': False,
                'namespace_prefix': 'MASTER'
            },
            'sources': {
                'A': {'type': 'csv', 'path': './input/A.csv'},
                'B': {'type': 'csv', 'path': './input/B.csv'},
                'C': {'type': 'csv', 'path': './input/C.csv'},
                'D': {'type': 'csv', 'path': './input/D.csv'},
                'E': {'type': 'csv', 'path': './input/E.csv'}
            },
            'simulation': {
                'seed': 42,
                'scenario': 'normal',
                'keys_per_system': 1000,
                'temporal': {
                    'simulate_history': True,
                    'days_of_history': 30
                },
                'failures': {
                    'inject_corruption': 0.01,
                    'simulate_timeout': False
                }
            },
            'processing': {
                'mode': 'full',
                'batch_size': 1000,
                'parallel': True,
                'checkpoint_interval': 5000,
                'max_workers': 5
            },
            'output': {
                'directory': './output',
                'format': 'csv',
                'include_timestamps': True,
                'generate_trend_analysis': False
            },
            'database': {
                'path': './data/keysync.db',
                'backup_enabled': True,
                'backup_count': 5
            },
            'logging': {
                'level': 'INFO',
                'file': './logs/keysync.log',
                'max_size_mb': 10,
                'backup_count': 5
            },
            'error_handling': {
                'on_missing_file': 'skip',
                'on_corrupt_data': 'log',
                'retry_attempts': 3,
                'retry_delay_seconds': 5
            },
            'sandbox': {
                'snapshot_dir': './output/snapshots',
                'max_keys': 10000,
                'default_key_prefix': 'CUST',
                'default_key_count': 1000,
                'seed': 42
            }
        }

    def _validate_config(self):
        """Validate configuration values."""
        # Validate normalization config
        norm_config = self.config.get('normalize', {})
        if not isinstance(norm_config.get('uppercase'), bool):
            logger.warning("Invalid 'uppercase' value, using default True")
            norm_config['uppercase'] = True

        # Validate provisioning strategy
        prov_config = self.config.get('provisioning', {})
        valid_strategies = ['mirror', 'namespaced']
        if prov_config.get('strategy') not in valid_strategies:
            logger.warning(f"Invalid provisioning strategy, using 'mirror'")
            prov_config['strategy'] = 'mirror'

        # Validate simulation scenario
        sim_config = self.config.get('simulation', {})
        valid_scenarios = ['normal', 'drift', 'failure', 'recovery']
        if sim_config.get('scenario') not in valid_scenarios:
            logger.warning(f"Invalid scenario, using 'normal'")
            sim_config['scenario'] = 'normal'

        # Validate processing mode
        proc_config = self.config.get('processing', {})
        valid_modes = ['full', 'incremental']
        if proc_config.get('mode') not in valid_modes:
            logger.warning(f"Invalid processing mode, using 'full'")
            proc_config['mode'] = 'full'

        # Validate logging level
        log_config = self.config.get('logging', {})
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR']
        if log_config.get('level') not in valid_levels:
            logger.warning(f"Invalid logging level, using 'INFO'")
            log_config['level'] = 'INFO'

        sandbox_cfg = self.config.get('sandbox', {})
        try:
            sandbox_cfg['max_keys'] = max(1, int(sandbox_cfg.get('max_keys', 10000)))
        except (TypeError, ValueError):
            logger.warning("Invalid sandbox.max_keys value; defaulting to 10000")
            sandbox_cfg['max_keys'] = 10000
        try:
            sandbox_cfg['default_key_count'] = max(1, int(sandbox_cfg.get('default_key_count', 1000)))
        except (TypeError, ValueError):
            logger.warning("Invalid sandbox.default_key_count; defaulting to 1000")
            sandbox_cfg['default_key_count'] = 1000
        prefix = sandbox_cfg.get('default_key_prefix', 'CUST')
        if not isinstance(prefix, str) or not prefix.strip():
            logger.warning("Invalid sandbox.default_key_prefix; defaulting to 'CUST'")
            sandbox_cfg['default_key_prefix'] = 'CUST'

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key using dot notation."""
        keys = key.split('.')
        value = self.config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default

        return value

    def get_section(self, section: str) -> Dict[str, Any]:
        """Get entire configuration section."""
        if section in self.config:
            return copy.deepcopy(self.config[section])
        return copy.deepcopy(self._defaults.get(section, {}))

    def get_system_files(self) -> Dict[str, str]:
        """Get system file paths from sources configuration."""
        sources = self.get_section('sources')
        resolved: Dict[str, str] = {}
        for system, source in sources.items():
            if source.get('type') != 'csv':
                continue
            raw_path = source.get('path')
            if not raw_path:
                continue
            resolved_path = self.resolve_path(raw_path)
            resolved[system] = str(resolved_path)
        return resolved

    @property
    def config_dir(self) -> Path:
        """Directory containing the configuration file."""
        return self._config_dir

    def resolve_path(self, value: Union[str, Path]) -> Path:
        """Resolve paths relative to the configuration file location."""
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = (self._config_dir / path).resolve()
        else:
            path = path.resolve()
        return path

    def update(self, updates: Dict[str, Any]):
        """Update configuration with new values."""
        self._deep_update(self.config, updates)
        logger.info("Configuration updated")

    def _deep_update(self, base: dict, updates: dict):
        """Recursively merge update values into the base dictionary."""
        for key, value in updates.items():
            if (
                isinstance(value, dict)
                and key in base
                and isinstance(base[key], dict)
            ):
                self._deep_update(base[key], value)
            else:
                base[key] = value

    def save(self, file_path: Optional[str] = None):
        """Save configuration to YAML file."""
        save_target = Path(file_path).expanduser() if file_path else self.config_path
        if not save_target.is_absolute():
            save_target = (self._config_dir / save_target).resolve()
        save_path = save_target
        save_path.parent.mkdir(parents=True, exist_ok=True)

        with open(save_path, 'w') as f:
            yaml.dump(self.config, f, default_flow_style=False, sort_keys=False)

        logger.info(f"Configuration saved to {save_path}")

    def to_dict(self) -> Dict[str, Any]:
        """Get configuration as dictionary."""
        return self.config.copy()

    def __str__(self) -> str:
        """String representation of configuration."""
        return yaml.dump(self.config, default_flow_style=False)
