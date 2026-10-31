# 🧪 Web-of-Trust (WoT) Examples

This folder provides sample inputs and generated outputs from the Decentralized Web-of-Trust (WoT) PR Reputation Bot, satisfying Hackathon Rule 9.

## Files

1. `sample_pr_event.json`: Standard GitHub Pull Request webhook event (`action: "opened"`).
2. `output_trusted.json`: Output payload when a contributor receives positive vouches across peer repositories (Score > 1.0 $\rightarrow$ `trusted-contributor` label).
3. `output_suspicious.json`: Output payload when a contributor receives negative denouncements across peer repositories (Score < -1.0 $\rightarrow$ `suspicious` label & automated warning comment).

## Reproducing Locally

Run the CLI in dry-run mode using the sample input event:
```bash
python3 -m wot_bot.main \
  --event-path examples/sample_pr_event.json \
  --registry trust-registry.json \
  --dry-run \
  --output-json
```
