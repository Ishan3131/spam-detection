# 🛡️ Decentralized Web-of-Trust (WoT) PR Reputation Bot

An automated GitHub bot and Action that calculates contributor trust scores for Pull Requests using a **Decentralized Web-of-Trust (WoT)** graph. Solves **Hacktoberfest 2026 Problem Statement 7** by thwarting spam and malicious PRs through peer reputation networks without penalizing innocent newcomers.

---

## 📂 Codebase Layout

```text
.
├── .github/
│   ├── workflows/
│   │   └── ci.yaml                  # Multi-version Python CI (3.9–3.12) & linting pipeline
│   └── pull_request_template.md     # Clean, standardized PR layout template
├── wot_bot/                         # Core Python package
│   ├── __init__.py                  # Public exports and package entrypoints
│   ├── config.py                    # Decay weights, thresholds (-1.0/+1.0), and labels
│   ├── github_client.py             # PR event payload parser & PyGithub/REST executor
│   ├── models.py                    # Data classes (TrustRegistry, ScoringRecord, EvaluationResult)
│   ├── scorer.py                    # Weighted reputation engine with depth decay math
│   ├── traversal.py                 # BFS graph traversal with cycle prevention & depth limits
│   └── main.py                      # CLI entrypoint for both GitHub Actions and local runs
├── tests/                           # Unit & integration test suite (18 test cases)
│   ├── __init__.py
│   ├── test_scorer.py               # Depth-decay weights & threshold decision tests
│   ├── test_traversal.py            # BFS traversal, loop detection & cutoff tests
│   ├── test_event_parser.py         # PR payload extraction & action simulation
│   └── test_integration.py          # End-to-end multi-tier pipeline & CLI tests
├── trust-registry.json              # Sample local repository trust registry
├── verify_scoring.py                # Standalone verification script for quick checks
├── requirements.txt                 # Dependencies (requests, PyGithub, ruff)
├── README.md                        # Complete architecture guide and documentation
└── HACKATHON.md                     # Hackathon problem statement & local model info
```

---

## 🏗️ Core Architecture

### 1. Trigger & Event Parsing
- **Supported Events**: Listens for GitHub PR events: `opened`, `synchronize`, and `reopened`.
- **Payload Extraction**: Parses the contributor's GitHub username (`user.login`), target repository (`repository.full_name`), and pull request number (`number`).
- **Safety Handling**: Ignores unsupported actions (`closed`, `assigned`) cleanly without error.

### 2. Trust Registry Discovery & Recursive Traversal
- **Local File**: Reads the repository's `trust-registry.json`:
  ```json
  {
    "version": "1.0.0",
    "project": "vyrox/spam-detection",
    "vouches": ["alice-dev", "himanshi-core", "jyoti-lead"],
    "denouncements": ["malicious-spammer", "phishing-actor-x"],
    "trusted_peers": ["vyrox/reputation-seed", "acme/trust-network"]
  }
  ```
- **Graph Traversal (BFS)**:
  - Fetches remote `trust-registry.json` files via raw GitHub URLs:
    `https://raw.githubusercontent.com/{owner}/{repo}/{branch}/trust-registry.json`
  - Explores level-by-level to ensure the **shortest-path property** (peers are evaluated at their closest distance).
  - Maintains a `visited_peers` set to prevent cyclic dependencies and infinite loops (e.g. `A -> B -> A`).
  - Strict cutoff at **Max Depth 3** to avoid API rate limits and unbounded latency.
  - Fault tolerance: Unreachable or 404 peers are skipped cleanly without crashing.

### 3. Weighted Scoring & Depth Decay
Farther projects have a decaying influence on contributor reputation:

$$\text{Weight}(d) = \begin{cases} 
1.0 & d = 1 \text{ (Direct Peer)} \\
0.5 & d = 2 \text{ (Transitive Peer)} \\
0.25 & d = 3 \text{ (3rd-Degree Peer)}
\end{cases}$$

For each peer in the traversal graph at depth $d$:
- **Vouch**: Adds $+(1.0 \times \text{Weight}_d)$ to net score.
- **Denouncement**: Subtracts $-(1.0 \times \text{Weight}_d)$ from net score.

### 4. Action Execution & Decisions
| Net Score | Status | Automated Action |
|:---:|:---:|:---|
| $> +1.0$ | **Trusted** | Applies `trusted-contributor` label. |
| $< -1.0$ | **Suspicious** | Applies `suspicious` label and posts an automated warning comment with the audit trail. |
| $[-1.0, +1.0]$ | **Neutral** | **PR left untouched** for maintainer review. Newcomers with zero network path are protected. |

---

## 🚀 Quickstart & Local Verification

### 1. Run the Quick Scoring Verification Script
Verify scoring calculations and depth decay across mock scenarios:
```bash
python3 verify_scoring.py
```

### 2. Run the Full Unit Test Suite
```bash
python3 -m unittest discover -s tests -v
```

### 3. Run CLI in Dry-Run Mode
Simulate PR evaluation with a sample event without calling GitHub APIs:
```bash
python3 -m wot_bot.main \
  --username alice-dev \
  --repo vyrox/spam-detection \
  --registry trust-registry.json \
  --dry-run \
  --output-json
```
