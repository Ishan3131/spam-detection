## Description
<!-- Provide a brief summary of the changes introduced by this pull request. -->

## Problem Statement Reference
<!-- Mention related issue or hackathon problem statement (e.g., Hacktoberfest 2026 Problem Statement 7). -->

## Type of Change
- [ ] New feature (non-breaking change adding functionality)
- [ ] Bug fix (non-breaking change fixing an issue)
- [ ] Refactor / Code layout enhancement
- [ ] Documentation update
- [ ] CI / CD configuration

## Decentralized Web-of-Trust (WoT) Impact
<!-- Does this PR affect trust-registry.json, peer traversal, or reputation scoring logic? -->
- [ ] Modifies `trust-registry.json` (vouches, denouncements, or trusted peers)
- [ ] Modifies WoT graph traversal or scoring algorithms
- [ ] None (standard code contribution)

## Testing Performed
<!-- Describe the tests run to verify the changes (e.g., python -m unittest discover -s tests -v, dry-run CLI test). -->
- [ ] Unit tests pass: `python -m unittest discover -s tests -v`
- [ ] Smoke test dry run passes: `python -m wot_bot.main --dry-run`
- [ ] JSON schema validation passed for `trust-registry.json`

## Checklist
- [ ] My code adheres to the style guidelines of this project
- [ ] I have commented my code, particularly explaining complex graph traversal or depth decay logic
- [ ] I have added appropriate tests covering new functionality
- [ ] Changes are isolated to a dedicated feature branch
