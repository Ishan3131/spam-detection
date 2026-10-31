## Description
<!-- Provide a brief summary of the changes introduced by this pull request. -->

## Problem Statement Reference
Problem 7: Decentralized Trust Network for Open Source Contributions

## AI Transparency
- **Coding agent:** <!-- e.g., Claude Code, Cursor, Gemini -->
- **Models used in project:** <!-- e.g., gemma4:e4b (via Ollama) as declared in HACKATHON.md -->

## Type of Change
- [ ] New feature (non-breaking change adding functionality)
- [ ] Bug fix (non-breaking change fixing an issue)
- [ ] Refactor / Code layout enhancement
- [ ] Documentation / Examples update
- [ ] CI / CD configuration

## Decentralized Web-of-Trust (WoT) Impact
- [ ] Modifies `trust-registry.json` (vouches, denouncements, or trusted peers)
- [ ] Modifies WoT graph traversal or depth-decay scoring algorithms
- [ ] None (standard code contribution)

## Testing Performed
- [ ] Unit tests pass: `python -m unittest discover -s tests -v`
- [ ] Smoke test dry run passes: `python -m wot_bot.main --dry-run`
- [ ] JSON validation passed: `python -m json.tool trust-registry.json > /dev/null`

## Checklist
- [ ] My code adheres to the style guidelines of this project
- [ ] Code is modular with comments explaining graph traversal and weight decay logic
- [ ] Examples and unit tests cover new functionality
- [ ] Changes are isolated to a dedicated feature branch
