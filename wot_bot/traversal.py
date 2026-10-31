"""Graph traversal and remote trust registry discovery engine.

Implements Breadth-First Search (BFS) to traverse the decentralized
Web-of-Trust graph up to a maximum depth limit while preventing infinite
loops and cyclic peer relationships.
"""

from collections import deque
import json
import logging
from typing import Callable, Deque, List, Optional, Set, Tuple

from wot_bot.config import (
    DEFAULT_BRANCH,
    HTTP_TIMEOUT_SECONDS,
    MAX_TRAVERSAL_DEPTH,
    RAW_URL_TEMPLATE,
)
from wot_bot.models import TrustRegistry

logger = logging.getLogger(__name__)


def build_raw_registry_url(repo_identifier: str, branch: str = DEFAULT_BRANCH) -> str:
    """Format the GitHub raw content URL for a repository's trust-registry.json.

    Supports 'owner/repo' or 'owner/repo@branch' syntax.
    """
    if "@" in repo_identifier:
        repo_part, custom_branch = repo_identifier.split("@", 1)
        branch = custom_branch.strip() or branch
    else:
        repo_part = repo_identifier

    parts = repo_part.strip().split("/")
    if len(parts) != 2:
        raise ValueError(
            f"Invalid repository identifier '{repo_identifier}'. Expected 'owner/repo'."
        )

    owner, repo = parts[0].strip(), parts[1].strip()
    return RAW_URL_TEMPLATE.format(owner=owner, repo=repo, branch=branch)


def fetch_remote_registry(
    peer_repo: str,
    branch: str = DEFAULT_BRANCH,
    timeout: float = HTTP_TIMEOUT_SECONDS,
) -> Optional[TrustRegistry]:
    """Fetch and parse remote trust-registry.json via GitHub raw content URL.

    Uses `requests` when available; falls back to `urllib.request` for
    dependency-free execution. Unreachable or missing files fail gracefully.
    """
    try:
        url = build_raw_registry_url(peer_repo, branch)
    except ValueError as err:
        logger.warning("Skipping invalid peer format: %s (%s)", peer_repo, err)
        return None

    logger.debug("Fetching trust registry from %s", url)

    # Attempt requests library first
    try:
        import requests

        response = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": "WoT-Reputation-Bot/1.0"},
        )
        if response.status_code == 200:
            data = response.json()
            return TrustRegistry.from_dict(data)
        logger.warning(
            "Peer %s returned HTTP status %s; skipping.", peer_repo, response.status_code
        )
        return None
    except ImportError:
        pass  # Fallback to urllib
    except Exception as exc:
        logger.warning("Failed to fetch %s via requests: %s", peer_repo, exc)
        return None

    # Fallback to standard library urllib
    try:
        import urllib.request

        req = urllib.request.Request(
            url, headers={"User-Agent": "WoT-Reputation-Bot/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                raw_bytes = resp.read()
                data = json.loads(raw_bytes.decode("utf-8"))
                return TrustRegistry.from_dict(data)
            return None
    except Exception as exc:
        logger.warning("Failed to fetch %s via urllib fallback: %s", peer_repo, exc)
        return None


def traverse_trust_network(
    local_registry: TrustRegistry,
    max_depth: int = MAX_TRAVERSAL_DEPTH,
    fetcher: Optional[Callable[[str], Optional[TrustRegistry]]] = None,
    root_repo_name: str = "local",
) -> List[Tuple[int, str, TrustRegistry]]:
    """Traverse the trust graph using Breadth-First Search (BFS) up to max_depth.

    Breadth-First Search (BFS) guarantees:
    1. Shortest Path Property: Each peer repository is visited at its minimum
       distance from the local repository. This ensures direct peers are evaluated
       at Depth 1 before they could ever be reached transitively at lower weights.
    2. Cycle & Infinite Loop Prevention: An in-memory set (`visited_peers`) tracks
       all seen repositories. Any self-referential or circular trust links are
       discarded immediately.
    3. Depth Decay Compliance: Traversal terminates cleanly once `max_depth` is reached.

    Args:
        local_registry: The repository's root TrustRegistry.
        max_depth: Maximum hops from the root (defaults to 3).
        fetcher: Optional callable(peer_repo) -> Optional[TrustRegistry], useful for mocks/testing.
        root_repo_name: Name of the local root repository to prevent self-inclusion.

    Returns:
        List of tuples: `(depth, peer_repo_name, peer_registry)`.
    """
    if fetcher is None:
        fetcher = fetch_remote_registry

    discovered_peers: List[Tuple[int, str, TrustRegistry]] = []
    visited_peers: Set[str] = {root_repo_name.lower().strip()}

    # Normalize and seed local project if specified
    if local_registry.project:
        visited_peers.add(local_registry.project.lower().strip())

    # Queue contains: (depth, peer_repo_identifier)
    queue: Deque[Tuple[int, str]] = deque()

    # Enqueue Depth 1: Direct trusted peers from the local repository
    for direct_peer in local_registry.trusted_peers:
        norm_peer = direct_peer.lower().strip()
        if norm_peer not in visited_peers:
            visited_peers.add(norm_peer)
            queue.append((1, direct_peer))

    # Execute BFS traversal level by level
    while queue:
        current_depth, current_peer = queue.popleft()

        if current_depth > max_depth:
            # Traversal cutoff reached; do not expand further
            continue

        # Fetch remote trust registry for current peer
        peer_registry = fetcher(current_peer)
        if peer_registry is None:
            logger.info(
                "Peer %s at depth %d could not be reached; continuing traversal.",
                current_peer,
                current_depth,
            )
            continue

        discovered_peers.append((current_depth, current_peer, peer_registry))

        # Enqueue downstream transitive peers if not yet at max depth
        if current_depth < max_depth:
            next_depth = current_depth + 1
            for next_peer in peer_registry.trusted_peers:
                norm_next = next_peer.lower().strip()
                if norm_next not in visited_peers:
                    visited_peers.add(norm_next)
                    queue.append((next_depth, next_peer))

    return discovered_peers
