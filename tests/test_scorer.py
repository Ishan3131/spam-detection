"""Unit tests for the weighted reputation scoring and depth decay logic."""

import unittest

from wot_bot.models import TrustRegistry
from wot_bot.scorer import compute_reputation_score


class TestScorer(unittest.TestCase):
    def setUp(self):
        self.empty_local = TrustRegistry(
            vouches=set(),
            denouncements=set(),
            trusted_peers=[],
            project="acme/local-project",
        )

    def test_depth_decay_weights(self):
        """Verify weights decay at depth 1 (1.0), depth 2 (0.5), depth 3 (0.25)."""
        peer_depth_1 = TrustRegistry(vouches={"alice-dev"}, project="peer/depth-1")
        peer_depth_2 = TrustRegistry(vouches={"bob-dev"}, project="peer/depth-2")
        peer_depth_3 = TrustRegistry(vouches={"charlie-dev"}, project="peer/depth-3")

        discovered = [
            (1, "peer/depth-1", peer_depth_1),
            (2, "peer/depth-2", peer_depth_2),
            (3, "peer/depth-3", peer_depth_3),
        ]

        # Test Depth 1 vouch: +1.0
        res_alice = compute_reputation_score("alice-dev", self.empty_local, discovered)
        self.assertAlmostEqual(res_alice.score, 1.0)

        # Test Depth 2 vouch: +0.5
        res_bob = compute_reputation_score("bob-dev", self.empty_local, discovered)
        self.assertAlmostEqual(res_bob.score, 0.5)

        # Test Depth 3 vouch: +0.25
        res_charlie = compute_reputation_score("charlie-dev", self.empty_local, discovered)
        self.assertAlmostEqual(res_charlie.score, 0.25)

    def test_denouncements_decay(self):
        """Verify denouncements subtract score based on depth decay."""
        peer_depth_1 = TrustRegistry(denouncements={"spammer-x"}, project="peer/depth-1")
        peer_depth_2 = TrustRegistry(denouncements={"spammer-y"}, project="peer/depth-2")
        peer_depth_3 = TrustRegistry(denouncements={"spammer-z"}, project="peer/depth-3")

        discovered = [
            (1, "peer/depth-1", peer_depth_1),
            (2, "peer/depth-2", peer_depth_2),
            (3, "peer/depth-3", peer_depth_3),
        ]

        res_x = compute_reputation_score("spammer-x", self.empty_local, discovered)
        self.assertAlmostEqual(res_x.score, -1.0)
        self.assertEqual(res_x.status, "neutral")  # exactly -1.0 is neutral boundary

        res_y = compute_reputation_score("spammer-y", self.empty_local, discovered)
        self.assertAlmostEqual(res_y.score, -0.5)

        res_z = compute_reputation_score("spammer-z", self.empty_local, discovered)
        self.assertAlmostEqual(res_z.score, -0.25)

    def test_cumulative_scoring_trusted(self):
        """Verify multiple vouches exceed threshold (> 1.0) and yield 'trusted' status."""
        peer1 = TrustRegistry(vouches={"good-contributor"}, project="org1/repo")
        peer2 = TrustRegistry(vouches={"good-contributor"}, project="org2/repo")

        # Depth 1 vouch (+1.0) + Depth 2 vouch (+0.5) = +1.5 > 1.0
        discovered = [
            (1, "org1/repo", peer1),
            (2, "org2/repo", peer2),
        ]
        result = compute_reputation_score("good-contributor", self.empty_local, discovered)
        self.assertAlmostEqual(result.score, 1.5)
        self.assertEqual(result.status, "trusted")
        self.assertEqual(result.vouches_count, 2)
        self.assertIn("trusted-contributor", result.action_taken)

    def test_cumulative_scoring_suspicious(self):
        """Verify multiple denouncements drop below threshold (< -1.0) and flag 'suspicious'."""
        peer1 = TrustRegistry(denouncements={"bad-actor"}, project="org1/repo")
        peer2 = TrustRegistry(denouncements={"bad-actor"}, project="org2/repo")

        # Depth 1 denouncement (-1.0) + Depth 2 denouncement (-0.5) = -1.5 < -1.0
        discovered = [
            (1, "org1/repo", peer1),
            (2, "org2/repo", peer2),
        ]
        result = compute_reputation_score("bad-actor", self.empty_local, discovered)
        self.assertAlmostEqual(result.score, -1.5)
        self.assertEqual(result.status, "suspicious")
        self.assertEqual(result.denouncements_count, 2)
        self.assertIn("suspicious", result.action_taken)

    def test_newcomer_neutral_protection(self):
        """Brand new contributor with zero network vouches/denouncements must remain neutral (~0.0)."""
        peer1 = TrustRegistry(vouches={"other-user"}, project="org1/repo")
        discovered = [(1, "org1/repo", peer1)]

        result = compute_reputation_score("brand-new-user", self.empty_local, discovered)
        self.assertAlmostEqual(result.score, 0.0)
        self.assertEqual(result.status, "neutral")
        self.assertEqual(result.vouches_count, 0)
        self.assertEqual(result.denouncements_count, 0)
        self.assertIn("neutral", result.action_taken.lower())

    def test_case_insensitive_matching(self):
        """Username matching must be case-insensitive (e.g. Alice-Dev == alice-dev)."""
        local = TrustRegistry(vouches={"alice-dev"}, project="local/repo")
        result = compute_reputation_score("Alice-DEV", local, [])
        self.assertAlmostEqual(result.score, 1.0)
        self.assertEqual(result.vouches_count, 1)


if __name__ == "__main__":
    unittest.main()
