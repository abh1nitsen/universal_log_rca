"""
Phase 1 Tests — Scaffold
Run after completing Phase 1 cells.
All tests must pass before publishing to GitHub.
"""

import os
import sys
import yaml
import pytest
from pathlib import Path
from datetime import datetime, timezone


# ── helpers ────────────────────────────────────────────────────

def get_drive_root():
    """Get project root regardless of environment."""
    colab_path = Path("/content/drive/MyDrive/universal_log_rca")
    dev_path = Path("./dev_drive/universal_log_rca")
    if colab_path.exists():
        return colab_path
    if dev_path.exists():
        return dev_path
    pytest.fail("Drive root not found. Run scaffold cells first.")


# ── directory structure tests ───────────────────────────────────

REQUIRED_DIRS = [
    "config/business_context",
    "data/input", "data/processed", "data/quarantine",
    "vector_store/chroma",
    "knowledge/postmortems", "knowledge/domain_patterns",
    "models/embeddings",
    "output/postmortems", "output/audit",
    "checkpoints", "feedback", "logs",
    "src/ingestion", "src/parsing",
    "src/reasoning", "src/schema", "src/utils",
    "tests",
]

def test_directory_structure():
    root = get_drive_root()
    missing = [d for d in REQUIRED_DIRS if not (root / d).exists()]
    assert not missing, f"Missing directories: {missing}"


# ── config file tests ───────────────────────────────────────────

REQUIRED_CONFIGS = [
    "config/llm_config.yaml",
    "config/pipeline_config.yaml",
    "config/hitl_config.yaml",
    "config/business_context/template.yaml",
    "config/business_context/banking.yaml",
    "config/business_context/adtech.yaml",
    "config/business_context/healthcare.yaml",
]

def test_config_files_exist():
    root = get_drive_root()
    missing = [c for c in REQUIRED_CONFIGS if not (root / c).exists()]
    assert not missing, f"Missing config files: {missing}"

def test_configs_are_valid_yaml():
    root = get_drive_root()
    for config_path in REQUIRED_CONFIGS:
        with open(root / config_path) as f:
            try:
                yaml.safe_load(f)
            except yaml.YAMLError as e:
                pytest.fail(f"Invalid YAML in {config_path}: {e}")

def test_llm_config_structure():
    root = get_drive_root()
    with open(root / "config/llm_config.yaml") as f:
        config = yaml.safe_load(f)
    assert "active_mode" in config
    assert "modes" in config
    assert config["active_mode"] in config["modes"]
    mode = config["modes"][config["active_mode"]]
    assert "worker" in mode
    assert "judge" in mode
    assert mode["worker"]["model"] != mode["judge"]["model"],         "Worker and judge must use different models"


# ── schema tests ────────────────────────────────────────────────

def test_universal_event_schema():
    root = get_drive_root()
    sys.path.insert(0, str(root))
    from src.schema.universal_event import (
        UniversalEvent, Severity, ErrorClass,
        SignalType, SystemLayer
    )

    raw = "[ERROR] 2024-03-15 14:23:11 payment-svc Connection timeout"
    event = UniversalEvent(
        event_id=UniversalEvent.make_event_id(raw, "test"),
        raw_hash=UniversalEvent.make_raw_hash(raw),
        signal_type=SignalType.ERROR,
        severity=Severity.P2,
        message_normalized="Connection timeout in payment service",
        error_class=ErrorClass.TIMEOUT,
        component="payment-svc",
        layer=SystemLayer.APPLICATION,
        parsing_confidence=0.92,
    )
    assert event.event_id is not None
    assert event.raw_hash is not None
    assert event.severity == "P2"
    assert event.error_class == "timeout"

def test_event_id_is_deterministic():
    root = get_drive_root()
    sys.path.insert(0, str(root))
    from src.schema.universal_event import UniversalEvent
    raw = "test log line"
    id1 = UniversalEvent.make_event_id(raw, "source_a")
    id2 = UniversalEvent.make_event_id(raw, "source_a")
    assert id1 == id2, "Event ID must be deterministic"


# ── checkpoint system tests ─────────────────────────────────────

def test_checkpoint_system():
    root = get_drive_root()
    sys.path.insert(0, str(root))
    from src.utils.checkpoint import CheckpointManager
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        cp = CheckpointManager(Path(tmp))

        # not done initially
        assert not cp.is_done("test_stage")

        # mark running
        cp.mark_running("test_stage", input_hash="abc123")
        assert not cp.is_done("test_stage")

        # mark done
        cp.mark_done("test_stage", summary={"lines": 100})
        assert cp.is_done("test_stage", input_hash="abc123")

        # input change invalidates checkpoint
        assert not cp.is_done("test_stage", input_hash="different_hash")

        # test failure recording
        cp.mark_running("fail_stage")
        cp.mark_failed("fail_stage", Exception("test error"))
        assert cp.has_failed("fail_stage")


# ── config loader tests ─────────────────────────────────────────

def test_config_loader():
    root = get_drive_root()
    sys.path.insert(0, str(root))
    from src.utils.config_loader import ConfigLoader

    loader = ConfigLoader(root / "config")
    config = loader.load("llm_config.yaml")
    assert isinstance(config, dict)
    assert "active_mode" in config

    # second load uses cache
    config2 = loader.load("llm_config.yaml")
    assert config is config2  # same object from cache

    # missing file raises clearly
    with pytest.raises(FileNotFoundError):
        loader.load("nonexistent.yaml")
