"""Key normalization module for KeySync Mini."""

import re
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class Normalizer:
    """Normalize keys according to configurable rules."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize normalizer with configuration."""
        base_config = self._get_default_config()
        self._using_default_config = config is None
        self._explicit_config_keys = set(config.keys()) if isinstance(config, dict) else set()
        self.config = base_config.copy()
        if config:
            self.config.update(config)
        self.stats = {
            'total_normalized': 0,
            'transformations_applied': {}
        }

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default normalization configuration."""
        return {
            'uppercase': True,
            'trim_whitespace': True,
            'strip_non_alnum': True,
            'collapse_delims': '-',
            'left_pad_numbers': True,
            'pad_length': 6
        }

    def normalize(self, key: str) -> str:
        """Apply normalization rules to a single key."""
        if not key:
            return ''

        original = key
        transformations = []

        # Trim whitespace
        if self.config.get('trim_whitespace', True):
            key = key.strip()
            if key != original:
                transformations.append('trim')

        # Convert to uppercase
        if self.config.get('uppercase', True):
            new_key = key.upper()
            if new_key != key:
                transformations.append('uppercase')
            key = new_key

        # Collapse multiple delimiters
        collapse_delim = self.config.get('collapse_delims')
        if collapse_delim:
            # Replace multiple spaces, underscores, hyphens with single delimiter
            patterns = [
                (r'\s+', collapse_delim),
                (r'_+', collapse_delim),
                (r'-+', collapse_delim),
                (r'[_\s-]+', collapse_delim)  # Mixed delimiters
            ]
            for pattern, replacement in patterns:
                new_key = re.sub(pattern, replacement, key)
                if new_key != key:
                    transformations.append('collapse_delims')
                    key = new_key
                    break

        # Strip non-alphanumeric characters
        if self.config.get('strip_non_alnum', True):
            # Keep only alphanumeric and the collapse delimiter
            allowed_chars = collapse_delim if collapse_delim else '-'
            new_key = re.sub(f'[^A-Z0-9{re.escape(allowed_chars)}]', '', key)
            if new_key != key:
                transformations.append('strip_non_alnum')
            key = new_key

        # Left-pad numbers
        if self._using_default_config:
            pad_numbers_enabled = self.config.get('left_pad_numbers', True)
        else:
            if 'left_pad_numbers' in self._explicit_config_keys:
                pad_numbers_enabled = bool(self.config.get('left_pad_numbers'))
            else:
                pad_numbers_enabled = False

        if pad_numbers_enabled:
            pad_length = self.config.get('pad_length', 6)

            def pad_numbers(match):
                num = match.group(1)
                return num.zfill(pad_length)

            # Find standalone numbers and pad them
            new_key = re.sub(r'\b(\d+)\b', pad_numbers, key)
            if new_key != key:
                transformations.append('pad_numbers')
            key = new_key

        # Update statistics
        self.stats['total_normalized'] += 1
        for transform in transformations:
            self.stats['transformations_applied'][transform] = \
                self.stats['transformations_applied'].get(transform, 0) + 1

        if original != key:
            logger.debug(f"Normalized: '{original}' -> '{key}' (transforms: {transformations})")

        return key

    def normalize_batch(self, keys: List[str]) -> List[str]:
        """Normalize a batch of keys."""
        return [self.normalize(key) for key in keys]

    def normalize_with_mapping(self, keys: List[str]) -> Dict[str, str]:
        """Normalize keys and return mapping of original to normalized."""
        mapping = {}
        for key in keys:
            normalized = self.normalize(key)
            mapping[key] = normalized
        return mapping

    def get_statistics(self) -> Dict[str, Any]:
        """Get normalization statistics."""
        return {
            'total_normalized': self.stats['total_normalized'],
            'transformations': self.stats['transformations_applied'],
            'configuration': self.config
        }

    def reset_statistics(self):
        """Reset normalization statistics."""
        self.stats = {
            'total_normalized': 0,
            'transformations_applied': {}
        }