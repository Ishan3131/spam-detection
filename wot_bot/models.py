"""Data models for trust registries, scoring records, and evaluation results."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Set


@dataclass
class TrustRegistry:
    """Represents a parsed trust registry file (trust_signed.json or trust-registry.json)."""
    vouches: Set[str] = field(default_factory=set)
    denouncements: Set[str] = field(default_factory=set)
    trusted_peers: List[str] = field(default_factory=list)
    project: str = ""
    version: str = "1.0.0"
    signer: str = ""
    signature: str = ""
    created_at: str = ""
    raw_data: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TrustRegistry":
        """Instantiate TrustRegistry from raw parsed JSON dictionary.

        Usernames are normalized to lowercase for case-insensitive matching.
        """
        raw_vouches = data.get("vouches", [])
        raw_denouncements = data.get("denouncements", [])
        raw_peers = data.get("trusted_peers", [])

        # Normalize usernames to lowercase for robust matching
        vouches = {
            (v.get("username", "") if isinstance(v, dict) else str(v)).strip().lower()
            for v in raw_vouches
            if v
        }
        denouncements = {
            (d.get("username", "") if isinstance(d, dict) else str(d)).strip().lower()
            for d in raw_denouncements
            if d
        }

        # Normalize peer strings ("owner/repo")
        peers: List[str] = []
        for p in raw_peers:
            if isinstance(p, dict):
                repo_name = p.get("repo") or p.get("name") or ""
            else:
                repo_name = str(p)
            cleaned = repo_name.strip()
            if cleaned and cleaned not in peers:
                peers.append(cleaned)

        return cls(
            vouches=vouches,
            denouncements=denouncements,
            trusted_peers=peers,
            project=data.get("project", ""),
            version=data.get("version", "1.0.0"),
            signer=data.get("signer", ""),
            signature=data.get("signature", ""),
            created_at=data.get("created_at", ""),
            raw_data=data,
        )


@dataclass
class ScoringRecord:
    """Audit log record for an individual vouch or denouncement observed in the graph."""
    contributor: str
    depth: int
    peer_repo: str
    action: str  # "vouch" or "denouncement"
    weight: float
    contribution: float  # +weight for vouch, -weight for denouncement


@dataclass
class EvaluationResult:
    """Final outcome of the Web-of-Trust evaluation for a contributor."""
    contributor: str
    score: float
    status: str  # "trusted", "suspicious", or "neutral"
    vouches_count: int = 0
    denouncements_count: int = 0
    records: List[ScoringRecord] = field(default_factory=list)
    visited_peers: Set[str] = field(default_factory=set)
    action_taken: str = ""
    explanation: str = ""
