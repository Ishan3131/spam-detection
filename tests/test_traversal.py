"""Unit tests for BFS graph traversal and cycle detection."""

import unittest

from wot_bot.models import TrustRegistry
from wot_bot.traversal import build_raw_registry_url, traverse_trust_network


class TestTraversal(unittest.TestCase):
    def test_build_raw_registry_url(self):
        """Verify GitHub raw URL generation."""
        url = build_raw_registry_url("acme/app")
        self.assertEqual(
            url,
            "https://raw.githubusercontent.com/acme/app/main/trust-registry.json",
        )

        url_custom = build_raw_registry_url("acme/app@devel")
        self.assertEqual(
            url_custom,
            "https://raw.githubusercontent.com/acme/app/devel/trust-registry.json",
        )

        with self.assertRaises(ValueError):
            build_raw_registry_url("invalid-name-without-slash")

    def test_bfs_traversal_and_depth_limits(self):
        """Verify BFS explores level-by-level up to max_depth."""
        # Setup mock graph:
        # root -> [peer1 (depth 1)]
        # peer1 -> [peer2 (depth 2)]
        # peer2 -> [peer3 (depth 3)]
        # peer3 -> [peer4 (depth 4 - should NOT be reached)]
        mock_registries = {
            "org/peer1": TrustRegistry(
                trusted_peers=["org/peer2"], project="org/peer1", vouches={"user1"}
            ),
            "org/peer2": TrustRegistry(
                trusted_peers=["org/peer3"], project="org/peer2", vouches={"user2"}
            ),
            "org/peer3": TrustRegistry(
                trusted_peers=["org/peer4"], project="org/peer3", vouches={"user3"}
            ),
            "org/peer4": TrustRegistry(
                trusted_peers=[], project="org/peer4", vouches={"user4"}
            ),
        }

        def mock_fetcher(peer_name: str):
            return mock_registries.get(peer_name)

        root = TrustRegistry(trusted_peers=["org/peer1"], project="org/root")
        discovered = traverse_trust_network(
            local_registry=root,
            max_depth=3,
            fetcher=mock_fetcher,
            root_repo_name="org/root",
        )

        depths = [d for d, _, _ in discovered]
        peers = [p for _, p, _ in discovered]

        # Depth 1, 2, 3 should be discovered
        self.assertEqual(depths, [1, 2, 3])
        self.assertEqual(peers, ["org/peer1", "org/peer2", "org/peer3"])
        # Peer 4 (depth 4) must NOT be visited
        self.assertNotIn("org/peer4", peers)

    def test_cycle_detection(self):
        """Verify cyclic peer references do not cause infinite loops."""
        # A -> B -> C -> A (cycle)
        mock_registries = {
            "org/a": TrustRegistry(trusted_peers=["org/b"], project="org/a"),
            "org/b": TrustRegistry(trusted_peers=["org/c"], project="org/b"),
            "org/c": TrustRegistry(trusted_peers=["org/a", "org/d"], project="org/c"),
            "org/d": TrustRegistry(trusted_peers=[], project="org/d"),
        }

        def mock_fetcher(peer_name: str):
            return mock_registries.get(peer_name)

        root = TrustRegistry(trusted_peers=["org/a"], project="org/root")
        discovered = traverse_trust_network(
            local_registry=root,
            max_depth=3,
            fetcher=mock_fetcher,
            root_repo_name="org/root",
        )

        visited_peers = [p for _, p, _ in discovered]
        # Each peer should only be visited once
        self.assertEqual(len(visited_peers), len(set(visited_peers)))
        self.assertIn("org/a", visited_peers)
        self.assertIn("org/b", visited_peers)
        self.assertIn("org/c", visited_peers)

    def test_unreachable_peer_graceful_handling(self):
        """Unreachable peer (fetcher returning None) should not halt traversal."""
        mock_registries = {
            "org/live": TrustRegistry(trusted_peers=[], project="org/live"),
        }

        def mock_fetcher(peer_name: str):
            return mock_registries.get(peer_name)

        root = TrustRegistry(
            trusted_peers=["org/offline-peer", "org/live"], project="org/root"
        )
        discovered = traverse_trust_network(
            local_registry=root,
            max_depth=2,
            fetcher=mock_fetcher,
            root_repo_name="org/root",
        )

        peers = [p for _, p, _ in discovered]
        self.assertEqual(peers, ["org/live"])


if __name__ == "__main__":
    unittest.main()
