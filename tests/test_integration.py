"""End-to-end integration and CLI execution tests."""

import json
import tempfile
import unittest

from wot_bot.main import run
from wot_bot.models import TrustRegistry
from wot_bot.scorer import compute_reputation_score
from wot_bot.traversal import traverse_trust_network


class TestIntegration(unittest.TestCase):
    def test_end_to_end_evaluation_flow(self):
        """Verify full pipeline: local registry -> BFS traversal -> depth scoring -> decision."""
        # 1. Local registry
        local = TrustRegistry(
            vouches={"alice-local"},
            denouncements={"eve-local"},
            trusted_peers=["peer/tier1"],
            project="acme/my-project",
        )

        # 2. Mock network: tier1 trusts tier2, tier2 trusts tier3
        network = {
            "peer/tier1": TrustRegistry(
                vouches={"bob-peer1"},
                denouncements={"mallory-peer1"},
                trusted_peers=["peer/tier2"],
                project="peer/tier1",
            ),
            "peer/tier2": TrustRegistry(
                vouches={"bob-peer1", "carol-peer2"},
                denouncements={"eve-local"},
                trusted_peers=["peer/tier3"],
                project="peer/tier2",
            ),
            "peer/tier3": TrustRegistry(
                vouches={"dave-peer3"},
                trusted_peers=[],
                project="peer/tier3",
            ),
        }

        def mock_fetcher(p):
            return network.get(p)

        peers = traverse_trust_network(local, max_depth=3, fetcher=mock_fetcher)
        self.assertEqual(len(peers), 3)

        # Alice: Local vouch (Depth 0) -> +1.0
        r_alice = compute_reputation_score("alice-local", local, peers)
        self.assertAlmostEqual(r_alice.score, 1.0)
        self.assertEqual(r_alice.status, "neutral")  # 1.0 is boundary, > 1.0 is trusted

        # Bob: Depth 1 vouch (+1.0) + Depth 2 vouch (+0.5) -> +1.5 -> trusted
        r_bob = compute_reputation_score("bob-peer1", local, peers)
        self.assertAlmostEqual(r_bob.score, 1.5)
        self.assertEqual(r_bob.status, "trusted")

        # Eve: Local denouncement (Depth 0: -1.0) + Depth 2 denouncement (Depth 2: -0.5) -> -1.5 -> suspicious
        r_eve = compute_reputation_score("eve-local", local, peers)
        self.assertAlmostEqual(r_eve.score, -1.5)
        self.assertEqual(r_eve.status, "suspicious")

        # Dave: Depth 3 vouch (+0.25) -> neutral
        r_dave = compute_reputation_score("dave-peer3", local, peers)
        self.assertAlmostEqual(r_dave.score, 0.25)
        self.assertEqual(r_dave.status, "neutral")

    def test_cli_dry_run_invocation(self):
        """Verify CLI execution with temporary event file and registry."""
        event_payload = {
            "action": "opened",
            "pull_request": {
                "number": 12,
                "user": {"login": "alice-dev"},
            },
            "repository": {
                "full_name": "acme/demo-repo",
            },
        }

        registry_payload = {
            "version": "1.0.0",
            "project": "acme/demo-repo",
            "vouches": ["alice-dev"],
            "denouncements": [],
            "trusted_peers": [],
        }

        with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".json") as ev_f, \
             tempfile.NamedTemporaryFile("w+", delete=False, suffix=".json") as reg_f:
            json.dump(event_payload, ev_f)
            json.dump(registry_payload, reg_f)
            ev_f.flush()
            reg_f.flush()
            ev_path = ev_f.name
            reg_path = reg_f.name

        exit_code = run([
            "--event-path", ev_path,
            "--registry", reg_path,
            "--dry-run",
            "--output-json",
        ])
        self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
