"""Configuration constants and threshold parameters for the Web-of-Trust bot."""

from typing import Dict

# Depth decay multipliers:
# Farther peers in the trust graph have decaying influence on the net trust score:
# - Depth 0 (Local Repository): 1.0
# - Depth 1 (Direct Peer): 1.0
# - Depth 2 (Peer of a Peer): 0.5
# - Depth 3 (3rd-degree Peer): 0.25
DEPTH_WEIGHTS: Dict[int, float] = {
    0: 1.0,  # Local repository vouches / denouncements
    1: 1.0,  # Direct peer repositories
    2: 0.5,  # 2nd-degree transitive peers
    3: 0.25,  # 3rd-degree transitive peers
}

# Maximum depth limit for BFS graph traversal to prevent infinite cycles and rate limits
MAX_TRAVERSAL_DEPTH: int = 3

# Reputation decision thresholds
# - Score > 1.0: Contributor is marked as trusted
# - Score < -1.0: Contributor is flagged as suspicious with an alert comment
# - Between -1.0 and 1.0: Neutral (e.g., brand-new contributors), left for human maintainer review
TRUSTED_THRESHOLD: float = 1.0
SUSPICIOUS_THRESHOLD: float = -1.0

# GitHub PR labels
LABEL_TRUSTED: str = "trusted-contributor"
LABEL_SUSPICIOUS: str = "suspicious"

# Default branch used when fetching remote trust-registry.json
DEFAULT_BRANCH: str = "main"

# GitHub Raw content URL pattern
RAW_URL_TEMPLATE: str = "https://raw.githubusercontent.com/{owner}/{repo}/{branch}/trust-registry.json"

# HTTP timeout in seconds for peer registry network requests
HTTP_TIMEOUT_SECONDS: float = 5.0
