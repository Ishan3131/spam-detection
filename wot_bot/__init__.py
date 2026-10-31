"""Decentralized Web-of-Trust (WoT) reputation network bot for Pull Requests.

Implements graph traversal over peer trust registries with depth-decay
scoring to evaluate contributor trustworthiness on GitHub PRs.
"""

from wot_bot.config import (
    DEFAULT_BRANCH,
    DEPTH_WEIGHTS,
    LABEL_SUSPICIOUS,
    LABEL_TRUSTED,
    MAX_TRAVERSAL_DEPTH,
    SUSPICIOUS_THRESHOLD,
    TRUSTED_THRESHOLD,
)
from wot_bot.models import EvaluationResult, ScoringRecord, TrustRegistry
from wot_bot.scorer import compute_reputation_score
from wot_bot.traversal import fetch_remote_registry, traverse_trust_network

__all__ = [
    "DEFAULT_BRANCH",
    "DEPTH_WEIGHTS",
    "LABEL_SUSPICIOUS",
    "LABEL_TRUSTED",
    "MAX_TRAVERSAL_DEPTH",
    "SUSPICIOUS_THRESHOLD",
    "TRUSTED_THRESHOLD",
    "EvaluationResult",
    "ScoringRecord",
    "TrustRegistry",
    "compute_reputation_score",
    "fetch_remote_registry",
    "traverse_trust_network",
]
