"""Unit tests for GitHub event parsing and PR action execution."""

import json
import tempfile
import unittest

from wot_bot.github_client import execute_pr_action, load_event_file, parse_pr_event
from wot_bot.models import EvaluationResult


class TestEventParser(unittest.TestCase):
    def test_parse_valid_pr_event(self):
        """Verify extraction of PR number, user login, repo name, and action."""
        payload = {
            "action": "opened",
            "pull_request": {
                "number": 42,
                "user": {"login": "octocat"},
            },
            "repository": {
                "full_name": "octocat/Hello-World",
            },
        }

        user, repo, pr_num, action = parse_pr_event(payload)
        self.assertEqual(user, "octocat")
        self.assertEqual(repo, "octocat/Hello-World")
        self.assertEqual(pr_num, 42)
        self.assertEqual(action, "opened")

    def test_parse_non_pr_event(self):
        """Events without pull_request object should return None cleanly."""
        payload = {"action": "push", "repository": {"full_name": "octocat/Hello-World"}}
        user, repo, pr_num, action = parse_pr_event(payload)
        self.assertIsNone(user)
        self.assertIsNone(repo)
        self.assertIsNone(pr_num)
        self.assertEqual(action, "push")

    def test_load_event_file(self):
        """Verify reading JSON file from disk."""
        data = {"action": "synchronize", "pull_request": {"number": 10}}
        with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".json") as tmp:
            json.dump(data, tmp)
            tmp_path = tmp.name

        loaded = load_event_file(tmp_path)
        self.assertEqual(loaded["action"], "synchronize")
        self.assertEqual(loaded["pull_request"]["number"], 10)

    def test_dry_run_trusted_action(self):
        """Dry-run on trusted status should plan 'trusted-contributor' label without API calls."""
        res = EvaluationResult(
            contributor="alice-dev",
            score=2.0,
            status="trusted",
            action_taken="Apply label 'trusted-contributor'",
        )
        summary = execute_pr_action(
            result=res,
            repo_full_name="acme/app",
            pr_number=5,
            dry_run=True,
        )
        self.assertTrue(summary["dry_run"])
        self.assertIn("trusted-contributor", summary["labels_added"])
        self.assertFalse(summary["comment_posted"])

    def test_dry_run_suspicious_action(self):
        """Dry-run on suspicious status should plan 'suspicious' label and warning comment."""
        res = EvaluationResult(
            contributor="bad-actor",
            score=-2.0,
            status="suspicious",
            action_taken="Apply label 'suspicious' and post warning comment",
            explanation="Warning: Contributor denounced by peers",
        )
        summary = execute_pr_action(
            result=res,
            repo_full_name="acme/app",
            pr_number=5,
            dry_run=True,
        )
        self.assertTrue(summary["dry_run"])
        self.assertIn("suspicious", summary["labels_added"])
        self.assertTrue(summary["comment_posted"])

    def test_neutral_action_untouched(self):
        """Neutral contributors should leave PR untouched (no labels, no comments)."""
        res = EvaluationResult(
            contributor="newbie",
            score=0.0,
            status="neutral",
            action_taken="No automated action taken",
        )
        summary = execute_pr_action(
            result=res,
            repo_full_name="acme/app",
            pr_number=5,
            dry_run=True,
        )
        self.assertEqual(summary["labels_added"], [])
        self.assertFalse(summary["comment_posted"])


if __name__ == "__main__":
    unittest.main()
