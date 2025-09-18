"""Sandbox state management for KeySync Mini.

The sandbox provides an interactive façade over the CSV sources consumed by the
reconciliation pipeline.  The classes in this module coordinate filesystem I/O,
state validation, and common operations (initialize, add, remove, modify) so the
CLI and future web dashboard can share a single implementation.
"""

from __future__ import annotations

import json
import csv
import os
import time
import getpass
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable, Sequence, Dict, List, Mapping, Optional, Set, Tuple
from contextlib import AbstractContextManager

from logger import get_logger

logger = get_logger(__name__)


ISO_TIMESTAMP_FMT = "%Y-%m-%dT%H:%M:%S"
DEFAULT_HEADER = ["key", "last_seen_at", "system", "status"]
ALLOWED_STATUSES = {"active", "inactive", "proposed"}


class SandboxError(Exception):
    """Base exception for sandbox operations."""


class SandboxValidationError(SandboxError):
    """Raised when sandbox input fails validation checks."""


class FileLock(AbstractContextManager):
    """Simple file-based lock supporting cross-process coordination."""

    def __init__(self, path: Path, timeout: float = 5.0, poll_interval: float = 0.1):
        self.path = path
        self.timeout = timeout
        self.poll_interval = poll_interval
        self._handle: Optional[int] = None

    def __enter__(self) -> "FileLock":
        deadline = time.time() + self.timeout
        while True:
            try:
                self._handle = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_RDWR)
                break
            except FileExistsError:
                if time.time() > deadline:
                    raise SandboxError(f"Unable to acquire lock: {self.path}")
                time.sleep(self.poll_interval)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._handle is not None:
            os.close(self._handle)
            self._handle = None
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass


@dataclass
class SandboxRecord:
    """Representation of a single sandbox entry for a system."""

    key: str
    system: str
    last_seen_at: datetime = field(default_factory=datetime.utcnow)
    status: str = "active"

    def to_row(self) -> Dict[str, str]:
        """Serialize the record into a CSV-compatible mapping."""
        return {
            "key": self.key,
            "last_seen_at": self.last_seen_at.strftime(ISO_TIMESTAMP_FMT),
            "system": self.system,
            "status": self.status,
        }

    @classmethod
    def from_row(cls, row: Mapping[str, str]) -> "SandboxRecord":
        """Create a record from a CSV row mapping."""
        key = sanitize_key(row.get("key", ""))
        system = row.get("system", "").strip().upper()
        status = (row.get("status") or "active").strip().lower()
        if status not in ALLOWED_STATUSES:
            status = "active"
        timestamp_value = row.get("last_seen_at") or datetime.utcnow().strftime(ISO_TIMESTAMP_FMT)
        try:
            last_seen = datetime.fromisoformat(timestamp_value.replace("Z", ""))
        except ValueError:
            last_seen = datetime.utcnow()
        return cls(key=key, system=system, last_seen_at=last_seen, status=status)


def sanitize_key(raw_key: str) -> str:
    """Normalize user-provided keys for consistent storage."""
    if raw_key is None:
        raise SandboxValidationError("Key value cannot be None")
    key = raw_key.strip()
    if not key:
        raise SandboxValidationError("Key value cannot be empty")
    return key


def ensure_systems(systems: Iterable[str], allowed: Sequence[str]) -> List[str]:
    """Validate requested systems and return a sorted unique list."""
    allowed_upper = {sys.upper() for sys in allowed}
    requested = {sys.strip().upper() for sys in systems if sys and sys.strip()}
    if not requested:
        raise SandboxValidationError("At least one system must be specified")
    missing = requested - allowed_upper
    if missing:
        raise SandboxValidationError(f"Unsupported systems requested: {', '.join(sorted(missing))}")
    return sorted(requested)


def ensure_keys(keys: Iterable[str]) -> List[str]:
    """Validate key payloads and return a de-duplicated list preserving order."""
    seen: Set[str] = set()
    result: List[str] = []
    for raw in keys:
        key = sanitize_key(raw)
        if key not in seen:
            seen.add(key)
            result.append(key)
    if not result:
        raise SandboxValidationError("No valid keys supplied")
    return result


def ensure_directory(path: Path) -> None:
    """Create directory if it does not exist."""
    path.mkdir(parents=True, exist_ok=True)


def load_keys_from_file(file_path: Path) -> List[str]:
    """Load keys from a text or CSV file."""
    if not file_path.exists():
        raise SandboxValidationError(f"Key source not found: {file_path}")
    keys: List[str] = []
    if file_path.suffix.lower() == '.csv':
        with file_path.open('r', newline='') as handle:
            reader = csv.DictReader(handle)
            if 'key' not in reader.fieldnames:
                raise SandboxValidationError(
                    f"CSV file {file_path} must contain a 'key' column"
                )
            for row in reader:
                keys.append(row.get('key', ''))
    else:
        with file_path.open('r', encoding='utf-8') as handle:
            keys.extend(line.strip() for line in handle if line.strip())
    return ensure_keys(keys)


class SandboxState:
    """In-memory representation of sandbox data across systems."""

    def __init__(self, system_files: Mapping[str, Path]):
        self.system_files = {system: Path(path) for system, path in system_files.items()}
        self.records: Dict[str, Dict[str, SandboxRecord]] = {
            system: {} for system in self.system_files
        }

    def load(self) -> None:
        """Load current CSV state from disk."""
        for system, path in self.system_files.items():
            if not path.exists():
                logger.debug("Sandbox load: %s missing, treating as empty", path)
                self.records[system] = {}
                continue
            with path.open("r", newline="") as handle:
                reader = csv.DictReader(handle)
                system_records: Dict[str, SandboxRecord] = {}
                for row in reader:
                    record = SandboxRecord.from_row(row)
                    system_records[record.key] = record
                self.records[system] = system_records

    def write(self) -> None:
        """Persist current state to CSV files."""
        for system, path in self.system_files.items():
            ensure_directory(path.parent)
            temp_path = path.with_suffix(path.suffix + ".tmp")
            lock_path = path.with_suffix(path.suffix + ".lock")
            with FileLock(lock_path):
                with temp_path.open("w", newline="") as handle:
                    writer = csv.DictWriter(handle, fieldnames=DEFAULT_HEADER)
                    writer.writeheader()
                    for record in sorted(self.records[system].values(), key=lambda r: r.key):
                        writer.writerow(record.to_row())
                temp_path.replace(path)

    def get_union(self) -> Set[str]:
        """Return the union of keys across all systems."""
        union: Set[str] = set()
        for records in self.records.values():
            union.update(records.keys())
        return union

    def get_intersection(self) -> Set[str]:
        """Return the intersection of keys across all systems."""
        iterator = iter(self.records.values())
        try:
            intersection = set(next(iterator).keys())
        except StopIteration:
            return set()
        for records in iterator:
            intersection &= set(records.keys())
        return intersection

    def key_frequencies(self) -> Dict[str, int]:
        """Return a mapping of key -> occurrence count across systems."""
        frequencies: Dict[str, int] = {}
        for records in self.records.values():
            for key in records.keys():
                frequencies[key] = frequencies.get(key, 0) + 1
        return frequencies

    def summary(self) -> Dict[str, Dict[str, int]]:
        """Produce summary statistics per system."""
        union = self.get_union()
        frequencies = self.key_frequencies()
        summary: Dict[str, Dict[str, int]] = {}
        for system, records in self.records.items():
            keys = set(records.keys())
            unique_count = sum(1 for key in keys if frequencies.get(key, 0) == 1)
            summary[system] = {
                "total": len(keys),
                "unique": unique_count,
                "missing_from_union": len(union - keys),
            }
        return summary

    def ensure_capacity(self, max_keys: int) -> None:
        """Validate the total keys per system stay under configured caps."""
        for system, records in self.records.items():
            if len(records) > max_keys:
                raise SandboxValidationError(
                    f"System {system} exceeds maximum of {max_keys} keys"
                )


class SandboxStateManager:
    """High-level façade for sandbox workflows."""

    def __init__(
        self,
        system_files: Mapping[str, Path],
        snapshot_dir: Path,
        max_keys: int = 10000,
        default_key_prefix: str = "CUST",
    ):
        self.state = SandboxState(system_files)
        self.snapshot_dir = snapshot_dir
        self.max_keys = max_keys
        self.default_key_prefix = default_key_prefix
        self.allowed_systems = sorted(system_files.keys())

    # ------------------------------------------------------------------
    # State lifecycle
    # ------------------------------------------------------------------
    def load(self) -> None:
        """Load state from CSV files."""
        self.state.load()

    def persist(self) -> None:
        """Persist current state back to CSV files."""
        self.state.ensure_capacity(self.max_keys)
        self.state.write()

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------
    def initialize(self, key_count: int) -> None:
        """Initialize synchronized state across all systems."""
        if key_count <= 0:
            raise SandboxValidationError("Key count must be greater than zero")
        timestamp = datetime.utcnow()
        self.state.records = {system: {} for system in self.allowed_systems}
        for idx in range(1, key_count + 1):
            key = f"{self.default_key_prefix}-{idx:05d}"
            for system in self.allowed_systems:
                self.state.records[system][key] = SandboxRecord(
                    key=key,
                    system=system,
                    last_seen_at=timestamp,
                    status="active",
                )
        self.persist()
        logger.info("Initialized sandbox with %s keys per system", key_count)

    def add_keys(self, keys: Iterable[str], systems: Iterable[str]) -> Tuple[int, Dict[str, List[str]]]:
        """Add keys to selected systems.

        Returns the count of new keys added and a mapping of system -> added keys.
        """
        ensured_keys = ensure_keys(keys)
        target_systems = ensure_systems(systems, self.allowed_systems)
        summary: Dict[str, List[str]] = {system: [] for system in target_systems}
        timestamp = datetime.utcnow()
        for system in target_systems:
            records = self.state.records.setdefault(system, {})
            for key in ensured_keys:
                if key not in records:
                    records[key] = SandboxRecord(
                        key=key,
                        system=system,
                        last_seen_at=timestamp,
                        status="active",
                    )
                    summary[system].append(key)
        self.persist()
        added_count = sum(len(keys) for keys in summary.values())
        logger.info("Added %s keys across systems %s", added_count, ", ".join(target_systems))
        return added_count, summary

    def remove_keys(
        self,
        keys: Iterable[str] = (),
        systems: Iterable[str] | None = None,
        pattern: str | None = None,
    ) -> Dict[str, List[str]]:
        """Remove keys from selected systems.

        Args:
            keys: Explicit collection of keys to remove.
            systems: Target systems; defaults to all systems.
            pattern: Optional substring pattern to match for removal.
        """
        target_systems = ensure_systems(
            systems or self.allowed_systems,
            self.allowed_systems,
        )
        keys_to_remove: Set[str] = set(ensure_keys(keys)) if keys else set()
        if pattern:
            pattern_upper = pattern.upper()
        summary: Dict[str, List[str]] = {system: [] for system in target_systems}

        for system in target_systems:
            records = self.state.records.get(system, {})
            removal_candidates = set(keys_to_remove)
            if pattern:
                for key in records.keys():
                    if pattern_upper in key.upper():
                        removal_candidates.add(key)
            for key in removal_candidates:
                if key in records:
                    del records[key]
                    summary[system].append(key)
        self.persist()
        logger.info("Removed keys across systems %s", ", ".join(target_systems))
        return summary

    def modify_keys(
        self,
        replacements: Mapping[str, str],
        systems: Iterable[str] | None = None,
    ) -> Dict[str, List[Tuple[str, str]]]:
        """Rename keys in selected systems using the provided mapping."""
        if not replacements:
            raise SandboxValidationError("No replacements provided")
        target_systems = ensure_systems(
            systems or self.allowed_systems,
            self.allowed_systems,
        )
        changes: Dict[str, List[Tuple[str, str]]] = {system: [] for system in target_systems}
        timestamp = datetime.utcnow()
        for old_raw, new_raw in replacements.items():
            old_key = sanitize_key(old_raw)
            new_key = sanitize_key(new_raw)
            if old_key == new_key:
                continue
            for system in target_systems:
                records = self.state.records.get(system, {})
                if old_key in records:
                    record = records.pop(old_key)
                    record.key = new_key
                    record.last_seen_at = timestamp
                    records[new_key] = record
                    changes[system].append((old_key, new_key))
        self.persist()
        return changes

    # ------------------------------------------------------------------
    # Snapshots
    # ------------------------------------------------------------------
    def save_snapshot(self, name: str, metadata: Optional[Dict[str, str]] = None) -> Path:
        """Persist a snapshot of the current state under the given name."""
        if not name:
            raise SandboxValidationError("Snapshot name is required")
        ensure_directory(self.snapshot_dir)
        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        safe_name = name.replace(" ", "_")
        snapshot_path = self.snapshot_dir / f"{timestamp}_{safe_name}"
        ensure_directory(snapshot_path)
        lock = FileLock(self.snapshot_dir / ".sandbox_snapshot.lock")
        with lock:
            for system, path in self.state.system_files.items():
                target = snapshot_path / Path(path.name)
                ensure_directory(target.parent)
                with target.open("w", newline="") as handle:
                    writer = csv.DictWriter(handle, fieldnames=DEFAULT_HEADER)
                    writer.writeheader()
                    for record in sorted(self.state.records[system].values(), key=lambda r: r.key):
                        writer.writerow(record.to_row())
        metadata_payload = {
            "created_at": datetime.utcnow().strftime(ISO_TIMESTAMP_FMT),
            "systems": self.allowed_systems,
            "creator": getpass.getuser(),
            "name": name,
        }
        if metadata:
            metadata_payload.update(metadata)
        description = metadata_payload.get('description') or metadata_payload.get('note')
        if description:
            metadata_payload['description'] = description
        with (snapshot_path / "metadata.json").open("w", encoding="utf-8") as meta_file:
            json.dump(metadata_payload, meta_file, indent=2)
        logger.info("Saved snapshot to %s", snapshot_path)
        return snapshot_path

    def load_snapshot(self, snapshot_path: Path) -> None:
        """Load a previously saved snapshot and overwrite current state."""
        snapshot_path = snapshot_path.expanduser().resolve()
        if not snapshot_path.exists() or not snapshot_path.is_dir():
            raise SandboxValidationError(f"Snapshot directory not found: {snapshot_path}")
        lock = FileLock(self.snapshot_dir / ".sandbox_snapshot.lock")
        with lock:
            for system, target_path in self.state.system_files.items():
                source = snapshot_path / target_path.name
                if not source.exists():
                    raise SandboxValidationError(
                        f"Snapshot missing data for system {system}: {source}"
                    )
                ensure_directory(target_path.parent)
                target_path.write_bytes(source.read_bytes())
        self.load()
        logger.info("Loaded snapshot from %s", snapshot_path)

    def list_snapshots(self) -> List[Path]:
        """Return available snapshots sorted by newest first."""
        if not self.snapshot_dir.exists():
            return []
        snapshots = [
            path for path in self.snapshot_dir.iterdir() if path.is_dir()
        ]
        return sorted(snapshots, reverse=True)

    # ------------------------------------------------------------------
    # Reporting helpers
    # ------------------------------------------------------------------
    def build_status_report(self) -> Dict[str, object]:
        """Assemble structured status information for callers."""
        self.state.ensure_capacity(self.max_keys)
        summary = self.state.summary()
        union = self.state.get_union()
        intersection = self.state.get_intersection()
        discrepancies = {
            system: list(sorted(union - set(self.state.records[system].keys())))
            for system in self.allowed_systems
        }
        return {
            "systems": summary,
            "total_unique_keys": len(union),
            "keys_common_to_all": len(intersection),
            "discrepancies": discrepancies,
            "snapshot_count": len(self.list_snapshots()),
        }


def build_manager_from_config(config: "Config") -> SandboxStateManager:
    """Factory helper to create a manager using ``Config`` defaults."""
    system_files = {
        system: Path(path)
        for system, path in config.get_system_files().items()
    }
    sandbox_cfg = config.get_section("sandbox")
    snapshot_dir = config.resolve_path(
        sandbox_cfg.get("snapshot_dir", "./output/snapshots")
    )
    max_keys = int(sandbox_cfg.get("max_keys", 10000))
    key_prefix = sandbox_cfg.get("default_key_prefix", "CUST")
    manager = SandboxStateManager(
        system_files=system_files,
        snapshot_dir=snapshot_dir,
        max_keys=max_keys,
        default_key_prefix=key_prefix,
    )
    manager.load()
    return manager


__all__ = [
    "SandboxError",
    "SandboxValidationError",
    "SandboxRecord",
    "SandboxState",
    "SandboxStateManager",
    "build_manager_from_config",
    "ensure_keys",
    "ensure_systems",
    "sanitize_key",
    "load_keys_from_file",
]
