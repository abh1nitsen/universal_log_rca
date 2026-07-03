"""
Universal Event Schema.
Every log line from every source normalizes to this.
This is the contract the entire system is built around.
"""

from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator
import hashlib
import uuid


class Severity(str, Enum):
    P1 = "P1"  # system down, data loss, security breach
    P2 = "P2"  # major degradation, significant user impact
    P3 = "P3"  # partial degradation, some users affected
    P4 = "P4"  # minor issue, workaround exists
    P5 = "P5"  # informational, no user impact


class SignalType(str, Enum):
    ERROR        = "error"
    WARNING      = "warning"
    ANOMALY      = "anomaly"
    STATE_CHANGE = "state_change"
    INFO         = "info"


class SystemLayer(str, Enum):
    INFRASTRUCTURE = "infrastructure"
    APPLICATION    = "application"
    BUSINESS       = "business"
    SECURITY       = "security"


class ErrorClass(str, Enum):
    TIMEOUT    = "timeout"
    CONNECTION = "connection"
    RESOURCE   = "resource"
    DEPENDENCY = "dependency"
    ASSERTION  = "assertion"
    LOGIC      = "logic"
    SECURITY   = "security"
    DATA       = "data"
    UNKNOWN    = "unknown"


class TimestampConfidence(str, Enum):
    EXACT       = "exact"       # timestamp explicitly in log
    INFERRED    = "inferred"    # derived from context
    APPROXIMATE = "approximate" # estimated from file metadata


class HallucinationVerdict(str, Enum):
    PASS              = "pass"
    PARTIAL           = "partial"
    FAIL              = "fail"
    NOT_CHECKED       = "not_checked"


class UniversalEvent(BaseModel):
    """
    The universal schema every log line normalizes to.
    Raw log content is never stored — only its hash.
    """

    # Identity
    event_id: str = Field(
        description="Deterministic hash of content. Enables deduplication."
    )

    # Time
    timestamp_utc: Optional[datetime] = Field(
        default=None,
        description="Always UTC. None if no timestamp could be extracted."
    )
    timestamp_confidence: TimestampConfidence = Field(
        default=TimestampConfidence.APPROXIMATE
    )

    # What happened
    signal_type: SignalType
    severity: Severity
    message_normalized: str = Field(
        description="PII-stripped, human-readable description."
    )

    # Where it happened
    layer: Optional[SystemLayer] = None
    component: Optional[str] = Field(
        default=None,
        description="Normalized service/component name."
    )
    environment: Optional[str] = Field(
        default=None,
        description="prod | staging | dev | dr"
    )

    # Technical fingerprint
    error_class: ErrorClass = ErrorClass.UNKNOWN
    error_code: Optional[str] = None

    # Domain context
    domain: Optional[str] = None
    business_impact: Optional[str] = None
    logical_context: dict = Field(default_factory=dict)

    # Provenance — audit trail
    source_format: Optional[str] = None
    source_system: Optional[str] = None
    raw_hash: str = Field(
        description="SHA256 of original log line. Raw content never stored."
    )

    # Governance
    pii_detected: bool = False
    pii_fields_removed: list[str] = Field(default_factory=list)
    sanitized: bool = False

    # Quality
    parsing_confidence: float = Field(
        default=0.0,
        ge=0.0, le=1.0,
        description="Confidence score from parsing pipeline."
    )
    hallucination_verdict: HallucinationVerdict = HallucinationVerdict.NOT_CHECKED

    @classmethod
    def make_event_id(cls, raw_line: str, source: str) -> str:
        """Deterministic event ID from content. Same line = same ID."""
        content = f"{source}:{raw_line}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    @classmethod
    def make_raw_hash(cls, raw_line: str) -> str:
        """Hash of raw content for audit trail. Content not stored."""
        return hashlib.sha256(raw_line.encode()).hexdigest()[:32]

    model_config = {"use_enum_values": True}
