"""CLI entrypoint for Web-of-Trust reputation bot."""

import argparse
import json
import logging
import os
import sys
from typing import Optional

from wot_bot.config import MAX_TRAVERSAL_DEPTH
from wot_bot.github_client import execute_pr_action, load_event_file, parse_pr_event
from wot_bot.models import TrustRegistry
from wot_bot.scorer import compute_reputation_score
from wot_bot.traversal import traverse_trust_network

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("wot_bot")


def build_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Decentralized Web-of-Trust (WoT) Pull Request reputation bot"
    )
    parser.add_argument(
        "--event-path",
        type=str,
        default=os.environ.get("GITHUB_EVENT_PATH"),
        help="Path to GitHub PR event payload JSON file (defaults to GITHUB_EVENT_PATH)",
    )
    parser.add_argument(
        "--registry",
        type=str,
        default="trust-registry.json",
        help="Path to local trust-registry.json file (default: trust-registry.json)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run mode: perform traversal and scoring without mutating GitHub PR labels or comments",
    )
    parser.add_argument(
        "--token",
        type=str,
        default=os.environ.get("GITHUB_TOKEN"),
        help="GitHub API access token (defaults to GITHUB_TOKEN environment variable)",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=MAX_TRAVERSAL_DEPTH,
        help=f"Maximum graph traversal depth (default: {MAX_TRAVERSAL_DEPTH})",
    )
    parser.add_argument(
        "--username",
        type=str,
        default=None,
        help="Direct contributor username override for testing/standalone runs",
    )
    parser.add_argument(
        "--repo",
        type=str,
        default=None,
        help="Direct repository full name (e.g. 'owner/repo') override",
    )
    parser.add_argument(
        "--output-json",
        action="store_true",
        help="Output structured JSON result to stdout",
    )
    return parser


def run(argv: Optional[list] = None) -> int:
    """Main execution function."""
    parser = build_parser()
    args = parser.parse_args(argv)

    # 1. Load local trust registry
    registry_path = args.registry
    if not os.path.exists(registry_path):
        logger.error("Local trust registry file '%s' not found.", registry_path)
        return 1

    with open(registry_path, "r", encoding="utf-8") as f:
        registry_data = json.load(f)
    local_registry = TrustRegistry.from_dict(registry_data)
    logger.info(
        "Loaded local registry '%s' with %d vouches, %d denouncements, and %d trusted peers.",
        local_registry.project or registry_path,
        len(local_registry.vouches),
        len(local_registry.denouncements),
        len(local_registry.trusted_peers),
    )

    # 2. Extract PR context (from event file or CLI overrides)
    contributor = args.username
    repo_full_name = args.repo
    pr_number = 1
    action_name = "opened"

    if args.event_path and os.path.exists(args.event_path):
        event_data = load_event_file(args.event_path)
        ev_user, ev_repo, ev_pr, action_name = parse_pr_event(event_data)
        if not contributor:
            contributor = ev_user
        if not repo_full_name:
            repo_full_name = ev_repo
        if ev_pr:
            pr_number = ev_pr
        logger.info(
            "Parsed PR event: action='%s', repo='%s', pr_number=%s, author='%s'",
            action_name,
            repo_full_name,
            pr_number,
            contributor,
        )

        # Only evaluate on 'opened' and 'synchronize' (or 'reopened')
        supported_actions = {"opened", "synchronize", "reopened"}
        if action_name not in supported_actions:
            logger.info(
                "Skipping PR event with action '%s' (only %s are evaluated).",
                action_name,
                supported_actions,
            )
            return 0

    if not contributor:
        logger.error(
            "No contributor username could be identified. Provide --username or a valid --event-path."
        )
        return 1

    repo_full_name = repo_full_name or local_registry.project or "local/repo"

    # 3. Recursive / BFS Traversal of Web-of-Trust network
    logger.info(
        "Starting BFS traversal of trust network up to depth %d for contributor '@%s'...",
        args.max_depth,
        contributor,
    )
    discovered_peers = traverse_trust_network(
        local_registry=local_registry,
        max_depth=args.max_depth,
        root_repo_name=repo_full_name,
    )
    logger.info("Discovered %d reachable peer repositories.", len(discovered_peers))

    # 4. Weighted scoring with depth decay
    result = compute_reputation_score(
        contributor=contributor,
        local_registry=local_registry,
        discovered_peers=discovered_peers,
    )

    logger.info(
        "Evaluation complete for @%s: Net Score = %.2f, Status = %s (%s)",
        contributor,
        result.score,
        result.status,
        result.action_taken,
    )

    # 5. Execute GitHub PR Action (dry-run or live API)
    action_summary = execute_pr_action(
        result=result,
        repo_full_name=repo_full_name,
        pr_number=pr_number,
        token=args.token,
        dry_run=args.dry_run,
    )

    if args.output_json:
        output_payload = {
            "contributor": result.contributor,
            "score": result.score,
            "status": result.status,
            "action_taken": result.action_taken,
            "action_summary": action_summary,
            "explanation": result.explanation,
        }
        print(json.dumps(output_payload, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(run())
