"""GitHub API client and PR event handler for Web-of-Trust actions."""

import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from wot_bot.config import LABEL_SUSPICIOUS, LABEL_TRUSTED
from wot_bot.models import EvaluationResult

logger = logging.getLogger(__name__)


def parse_pr_event(event_data: Dict[str, Any]) -> Tuple[Optional[str], Optional[str], Optional[int], str]:
    """Extract PR author, repository full name, PR number, and action from GitHub event JSON.

    Returns:
        Tuple of (contributor_login, repo_full_name, pr_number, action_name).
    """
    action = event_data.get("action", "")
    pr = event_data.get("pull_request")
    repo = event_data.get("repository", {})

    if not pr:
        logger.warning("Event payload does not contain a 'pull_request' object.")
        return None, None, None, action

    contributor = pr.get("user", {}).get("login")
    pr_number = pr.get("number")
    repo_full_name = repo.get("full_name")

    return contributor, repo_full_name, pr_number, action


def load_event_file(event_path: str) -> Dict[str, Any]:
    """Read and parse GitHub event JSON file from disk."""
    if not os.path.exists(event_path):
        raise FileNotFoundError(f"Event file not found at '{event_path}'")

    with open(event_path, "r", encoding="utf-8") as f:
        return json.load(f)


def execute_pr_action(
    result: EvaluationResult,
    repo_full_name: str,
    pr_number: int,
    token: Optional[str] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Execute required GitHub PR label and comment actions based on WoT evaluation.

    Args:
        result: EvaluationResult from scorer.
        repo_full_name: "owner/repo"
        pr_number: Pull request issue number.
        token: GitHub API token (defaults to GITHUB_TOKEN env var).
        dry_run: If True, skip network mutating calls and log planned actions.

    Returns:
        Dict summarizing executed actions.
    """
    summary: Dict[str, Any] = {
        "contributor": result.contributor,
        "score": result.score,
        "status": result.status,
        "labels_added": [],
        "comment_posted": False,
        "dry_run": dry_run,
    }

    if result.status == "neutral":
        logger.info(
            "Contributor @%s is neutral (score %.2f). Leaving PR #%d untouched for maintainer review.",
            result.contributor,
            result.score,
            pr_number,
        )
        return summary

    labels_to_add: List[str] = []
    comment_body: Optional[str] = None

    if result.status == "trusted":
        labels_to_add.append(LABEL_TRUSTED)
        logger.info(
            "Contributor @%s is trusted (score +%.2f). Applying label: %s",
            result.contributor,
            result.score,
            LABEL_TRUSTED,
        )

    elif result.status == "suspicious":
        labels_to_add.append(LABEL_SUSPICIOUS)
        comment_body = result.explanation
        logger.warning(
            "Contributor @%s is suspicious (score %.2f). Flagging PR #%d with label '%s' and warning comment.",
            result.contributor,
            result.score,
            pr_number,
            LABEL_SUSPICIOUS,
        )

    if dry_run:
        logger.info(
            "[DRY-RUN] Would apply labels %s and comment=%s to %s#%d",
            labels_to_add,
            bool(comment_body),
            repo_full_name,
            pr_number,
        )
        summary["labels_added"] = labels_to_add
        summary["comment_posted"] = bool(comment_body)
        return summary

    # Live execution via PyGithub or REST API
    token = token or os.environ.get("GITHUB_TOKEN")
    if not token:
        logger.warning(
            "No GITHUB_TOKEN found in environment; cannot execute PR actions against GitHub API."
        )
        return summary

    _apply_github_mutations(
        repo_full_name=repo_full_name,
        pr_number=pr_number,
        labels=labels_to_add,
        comment=comment_body,
        token=token,
    )

    summary["labels_added"] = labels_to_add
    summary["comment_posted"] = bool(comment_body)
    return summary


def _apply_github_mutations(
    repo_full_name: str,
    pr_number: int,
    labels: List[str],
    comment: Optional[str],
    token: str,
) -> None:
    """Apply labels and comments to GitHub PR using PyGithub or fallback REST requests."""
    # Attempt PyGithub first
    try:
        from github import Github

        gh = Github(token)
        repo = gh.get_repo(repo_full_name)
        pull = repo.get_pull(pr_number)

        if labels:
            pull.add_to_labels(*labels)
            logger.info("Successfully added labels %s to PR #%d via PyGithub.", labels, pr_number)

        if comment:
            pull.create_issue_comment(comment)
            logger.info("Successfully posted warning comment to PR #%d via PyGithub.", pr_number)
        return
    except ImportError:
        logger.debug("PyGithub not installed, falling back to GitHub REST API.")
    except Exception as exc:
        logger.warning("PyGithub mutation failed: %s; falling back to REST API.", exc)

    # Fallback to direct REST API
    _rest_api_mutate(repo_full_name, pr_number, labels, comment, token)


def _rest_api_mutate(
    repo_full_name: str,
    pr_number: int,
    labels: List[str],
    comment: Optional[str],
    token: str,
) -> None:
    """Perform GitHub PR modifications using standard library urllib."""
    import urllib.request

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "WoT-Reputation-Bot/1.0",
        "Content-Type": "application/json",
    }

    base_url = f"https://api.github.com/repos/{repo_full_name}/issues/{pr_number}"

    # Add labels
    if labels:
        try:
            req = urllib.request.Request(
                f"{base_url}/labels",
                data=json.dumps({"labels": labels}).encode("utf-8"),
                headers=headers,
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                logger.info("REST API added labels %s (status %d)", labels, resp.status)
        except Exception as exc:
            logger.error("Failed to add labels via REST API: %s", exc)

    # Add comment
    if comment:
        try:
            req = urllib.request.Request(
                f"{base_url}/comments",
                data=json.dumps({"body": comment}).encode("utf-8"),
                headers=headers,
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                logger.info("REST API created comment (status %d)", resp.status)
        except Exception as exc:
            logger.error("Failed to post comment via REST API: %s", exc)
