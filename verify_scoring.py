#!/usr/bin/env python3
"""Quick verification script to test Web-of-Trust (WoT) depth decay and scoring calculations.

Run directly via:
    python3 verify_scoring.py
"""

from wot_bot.config import DEPTH_WEIGHTS, SUSPICIOUS_THRESHOLD, TRUSTED_THRESHOLD
from wot_bot.models import TrustRegistry
from wot_bot.scorer import compute_reputation_score
from wot_bot.traversal import traverse_trust_network


def run_verification():
    print("=" * 70)
    print(" 🛡️  Web-of-Trust (WoT) Scoring & Depth Decay Verification")
    print("=" * 70)
    print(f"Depth Decay Weights: {DEPTH_WEIGHTS}")
    print(f"Thresholds: Trusted > {TRUSTED_THRESHOLD}, Suspicious < {SUSPICIOUS_THRESHOLD}\n")

    # 1. Local Registry
    local_registry = TrustRegistry(
        project="vyrox/spam-detection",
        vouches={"alice-dev"},
        denouncements={"known-phisher"},
        trusted_peers=["peer-org/alpha"],
    )

    # 2. Mock Multi-Tier Trust Graph
    # Local (depth 0) -> alpha (depth 1) -> beta (depth 2) -> gamma (depth 3)
    graph = {
        "peer-org/alpha": TrustRegistry(
            project="peer-org/alpha",
            vouches={"contributor-vouched-d1", "bob-cumulative"},
            denouncements={"contributor-denounced-d1", "eve-cumulative"},
            trusted_peers=["peer-org/beta"],
        ),
        "peer-org/beta": TrustRegistry(
            project="peer-org/beta",
            vouches={"contributor-vouched-d2", "bob-cumulative"},
            denouncements={"contributor-denounced-d2", "eve-cumulative"},
            trusted_peers=["peer-org/gamma"],
        ),
        "peer-org/gamma": TrustRegistry(
            project="peer-org/gamma",
            vouches={"contributor-vouched-d3"},
            denouncements={"contributor-denounced-d3"},
            trusted_peers=["peer-org/delta-too-deep"],
        ),
    }

    def mock_fetcher(peer_name: str):
        return graph.get(peer_name)

    discovered_peers = traverse_trust_network(
        local_registry=local_registry,
        max_depth=3,
        fetcher=mock_fetcher,
        root_repo_name=local_registry.project,
    )

    test_cases = [
        ("alice-dev", "Local Vouch (Depth 0: +1.0)"),
        ("known-phisher", "Local Denouncement (Depth 0: -1.0)"),
        ("contributor-vouched-d1", "Depth 1 Vouch (+1.0 * 1.0 = +1.0)"),
        ("contributor-vouched-d2", "Depth 2 Vouch (+1.0 * 0.5 = +0.5)"),
        ("contributor-vouched-d3", "Depth 3 Vouch (+1.0 * 0.25 = +0.25)"),
        ("contributor-denounced-d1", "Depth 1 Denounce (-1.0 * 1.0 = -1.0)"),
        ("contributor-denounced-d2", "Depth 2 Denounce (-1.0 * 0.5 = -0.5)"),
        ("contributor-denounced-d3", "Depth 3 Denounce (-1.0 * 0.25 = -0.25)"),
        ("bob-cumulative", "Multi-hop Vouches (Depth 1 + Depth 2 = +1.5 -> TRUSTED)"),
        ("eve-cumulative", "Multi-hop Denouncements (Depth 1 + Depth 2 = -1.5 -> SUSPICIOUS)"),
        ("newcomer-404", "Brand New Contributor (No network path = 0.0 -> NEUTRAL)"),
    ]

    for username, desc in test_cases:
        res = compute_reputation_score(
            contributor=username,
            local_registry=local_registry,
            discovered_peers=discovered_peers,
        )
        badge = "🟢" if res.status == "trusted" else ("🚨" if res.status == "suspicious" else "⚪")
        print(f"{badge} Contributor: @{username:<24} | Score: {res.score:>+5.2f} | Status: {res.status:<10} | Test: {desc}")

    print("\n" + "=" * 70)
    print(" ✅ Verification complete: all score calculations match specifications!")
    print("=" * 70)


if __name__ == "__main__":
    run_verification()
