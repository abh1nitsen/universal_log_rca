"""
Checkpoint system for fail-safe, fail-point-resume pipeline execution.
Every stage writes a checkpoint before starting and on completion.
On startup, incomplete checkpoints are detected and user is informed.
"""

import json
import hashlib
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from enum import Enum


class StageStatus(str, Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    DONE      = "done"
    FAILED    = "failed"
    SKIPPED   = "skipped"


class CheckpointManager:
    """
    Manages pipeline stage checkpoints on Google Drive.

    Usage:
        cp = CheckpointManager(drive_root / "checkpoints")
        with cp.stage("statistical_filter", input_hash=hash_of_input):
            # do work
            # if exception raised, checkpoint records failure
            # if completes, checkpoint records success
    """

    def __init__(self, checkpoint_dir: Path):
        self.dir = Path(checkpoint_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.dir / "pipeline_state.json"
        self._state = self._load_state()

    def _load_state(self) -> dict:
        if self.state_file.exists():
            try:
                return json.loads(self.state_file.read_text())
            except json.JSONDecodeError:
                return {}
        return {}

    def _save_state(self):
        tmp = self.state_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._state, indent=2, default=str))
        tmp.rename(self.state_file)  # atomic write

    def is_done(self, stage_name: str, input_hash: str = None) -> bool:
        """
        Returns True if stage completed successfully.
        If input_hash provided, also checks input hasn't changed.
        """
        stage = self._state.get(stage_name, {})
        if stage.get("status") != StageStatus.DONE:
            return False
        if input_hash and stage.get("input_hash") != input_hash:
            return False  # input changed — re-run
        return True

    def has_failed(self, stage_name: str) -> bool:
        return self._state.get(stage_name, {}).get("status") == StageStatus.FAILED

    def mark_running(self, stage_name: str, input_hash: str = None):
        self._state[stage_name] = {
            "status": StageStatus.RUNNING,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "input_hash": input_hash,
        }
        self._save_state()

    def mark_done(self, stage_name: str, summary: dict = None):
        self._state[stage_name].update({
            "status": StageStatus.DONE,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "summary": summary or {},
        })
        self._save_state()

    def mark_failed(self, stage_name: str, error: Exception):
        self._state[stage_name].update({
            "status": StageStatus.FAILED,
            "failed_at": datetime.now(timezone.utc).isoformat(),
            "error": str(error),
            "traceback": traceback.format_exc(),
        })
        self._save_state()

    def get_incomplete_stages(self) -> list:
        return [
            name for name, data in self._state.items()
            if data.get("status") == StageStatus.RUNNING
        ]

    def summary(self) -> dict:
        return {
            name: data.get("status") 
            for name, data in self._state.items()
        }


def file_hash(path: Path) -> str:
    """SHA256 hash of a file. Used to detect input changes."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:16]
