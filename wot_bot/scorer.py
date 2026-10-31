"""Weighted reputation scoring engine with depth-decay multipliers."""

import logging
from typing import Dict, List, Optional, Tuple

from wot_bot.config import (
    DEPTH_WEIGHTS,
    LABEL_SUSPICIOUS,
    LABEL_TRUSTED,
    SUSPICIOUS_THRESHOLD,
    TRUSTED_THRESHOLD,
)
from wot_bot.models import EvaluationResult, ScoringRecord, TrustRegistry

logger = logging.getLogger(__name__)


def compute_reputation_score(
    contributor: str,
    local_registry: TrustRegistry,
    discovered_peers: List[Tuple[int, str, TrustRegistry]],
    depth_weights: Optional[Dict[int, float]] = None,
    trusted_threshold: float = TRUSTED_THRESHOLD,
    suspicious_threshold: float = SUSPICIOUS_THRESHOLD,
) -> EvaluationResult:
    """Compute the net confidence score for a contributor across the WoT graph.

    Graph Depth Decay Formula:
        For each repository in the traversal graph at depth `d`:
            weight_d = depth_weights.get(d, 0.0)
            if contributor in vouches:
                score += 1.0 * weight_d
            if contributor in denouncements:
                score -= 1.0 * weight_d

    Standard Depth Weights:
        - Depth 0 (Local Repository): weight = 1.0
        - Depth 1 (Direct Peer): weight = 1.0
        - Depth 2 (2nd-degree Peer): weight = 0.5
        - Depth 3 (3rd-degree Peer): weight = 0.25

    Decision Rules:
        - Net Score > 1.0: "trusted" -> label PR `trusted-contributor`
        - Net Score < -1.0: "suspicious" -> post warning comment & label PR `suspicious`
        - -1.0 <= Net Score <= 1.0: "neutral" -> untouched for human review (protects newcomers)

    Args:
        contributor: GitHub username / handle of the PR author.
        local_registry: The repository's local TrustRegistry (evaluated at depth 0).
        discovered_peers: Output of `traverse_trust_network`: list of (depth, peer_name, registry).
        depth_weights: Custom depth weight mapping (defaults to DEPTH_WEIGHTS).
        trusted_threshold: Upper score threshold for trusted status.
        suspicious_threshold: Lower score threshold for suspicious status.

    Returns:
        EvaluationResult containing net score, status, audit trail, and explanation.
    """
    if depth_weights is None:
        depth_weights = DEPTH_WEIGHTS

    norm_user = contributor.strip().lower()
    records: List[ScoringRecord] = []
    visited_repos: set = set()

    # 1. Evaluate Depth 0: Local Repository Ground Truth
    local_name = local_registry.project or "local-registry"
    visited_repos.add(local_name.lower())
    local_weight = depth_weights.get(0, 1.0)

    if norm_user in local_registry.vouches:
        contrib = 1.0 * local_weight
        records.append(
            ScoringRecord(
                contributor=contributor,
                depth=0,
                peer_repo=local_name,
                action="vouch",
                weight=local_weight,
                contribution=contrib,
            )
        )
        logger.debug("Local vouch for %s (+%.2f)", contributor, contrib)

    if norm_user in local_registry.denouncements:
        contrib = -1.0 * local_weight
        records.append(
            ScoringRecord(
                contributor=contributor,
                depth=0,
                peer_repo=local_name,
                action="denouncement",
                weight=local_weight,
                contribution=contrib,
            )
        )
        logger.debug("Local denouncement for %s (%.2f)", contributor, contrib)

    # 2. Evaluate Discovered Peers at Depth 1, 2, 3
    for depth, peer_name, peer_registry in discovered_peers:
        norm_peer = peer_name.lower().strip()
        visited_repos.add(norm_peer)
        weight = depth_weights.get(depth, 0.0)

        # Check if peer vouched for contributor
        if norm_user in peer_registry.vouches:
            contrib = 1.0 * weight
            records.append(
                ScoringRecord(
                    contributor=contributor,
                    depth=depth,
                    peer_repo=peer_name,
                    action="vouch",
                    weight=weight,
                    contribution=contrib,
                )
            )
            logger.debug(
                "Peer %s at depth %d vouched for %s (+%.2f)",
                peer_name,
                depth,
                contributor,
                contrib,
            )

        # Check if peer denounced contributor
        if norm_user in peer_registry.denouncements:
            contrib = -1.0 * weight
            records.append(
                ScoringRecord(
                    contributor=contributor,
                    depth=depth,
                    peer_repo=peer_name,
                    action="denouncement",
                    weight=weight,
                    contribution=contrib,
                )
            )
            logger.debug(
                "Peer %s at depth %d denounced %s (%.2f)",
                peer_name,
                depth,
                contributor,
                contrib,
            )

    # 3. Sum total net confidence score
    total_score = sum(r.contribution for r in records)
    total_score = round(total_score, 4)

    vouches_count = sum(1 for r in records if r.action == "vouch")
    denouncements_count = sum(1 for r in records if r.action == "denouncement")

    # 4. Determine Action Status based on Thresholds
    if total_score > trusted_threshold:
        status = "trusted"
        action_taken = f"Apply label '{LABEL_TRUSTED}'"
    elif total_score < suspicious_threshold:
        status = "suspicious"
        action_taken = f"Apply label '{LABEL_SUSPICIOUS}' and post warning comment"
    else:
        status = "neutral"
        action_taken = "No automated action taken (neutral newcomer review)"

    # 5. Build human-readable markdown audit trail
    explanation = _build_explanation_markdown(
        contributor=contributor,
        score=total_score,
        status=status,
        records=records,
        trusted_threshold=trusted_threshold,
        suspicious_threshold=suspicious_threshold,
    )

    return EvaluationResult(
        contributor=contributor,
        score=total_score,
        status=status,
        vouches_count=vouches_count,
        denouncements_count=denouncements_count,
        records=records,
        visited_peers=visited_repos,
        action_taken=action_taken,
        explanation=explanation,
    )


def _build_explanation_markdown(
    contributor: str,
    score: float,
    status: str,
    records: List[ScoringRecord],
    trusted_threshold: float,
    suspicious_threshold: float,
) -> str:
    """Generate Markdown formatted evaluation summary for PR comments."""
    status_emojis = {
        "trusted": "🟢 **TRUSTED CONTRIBUTOR**",
        "suspicious": "⚠️ **SUSPICIOUS CONTRIBUTOR FLAGGED**",
        "neutral": "⚪ **NEUTRAL CONTRIBUTOR (NEWCOMER)**",
    }
    header_status = status_emojis.get(status, status.upper())

    lines = [
        "### 🛡️ Decentralized Web-of-Trust (WoT) Reputation Report",
        f"- **Contributor**: `@{contributor}`",
        f"- **Net Trust Score**: `{score:+.2f}`",
        f"- **Classification**: {header_status}",
        "",
        "#### Scoring Breakdown & Graph Trail",
    ]

    if not records:
        lines.append(
            "_No vouch or denouncement records found across the local registry or traversed peers._"
        )
        lines.append(
            "This contributor is evaluated as **neutral** (~0.0). Newcomers are not penalized."
        )
    else:
        lines.append("| Depth | Peer Project | Event | Weight | Net Impact |")
        lines.append("|:-----:|:-------------|:-----:|:------:|:----------:|")
        for r in records:
            event_badge = "✅ Vouch" if r.action == "vouch" else "🚨 Denounce"
            lines.append(
                f"| {r.depth} | `{r.peer_repo}` | {event_badge} | {r.weight:.2f}x | {r.contribution:+.2f} |"
            )

    lines.append("")
    lines.append("#### Threshold Parameters")
    lines.append(f"- Trusted threshold: `score > {trusted_threshold:.1f}`")
    lines.append(f"- Suspicious threshold: `score < {suspicious_threshold:.1f}`")

    if status == "suspicious":
        lines.append("")
        lines.append(
            "> ⚠️ **Maintainer Notice**: This pull request author has accumulated negative "
            "reputation from decentralized peer project denouncements. Please audit this PR carefully "
            "before executing workflow runs or merging."
        )

    return "\n".join(lines)
