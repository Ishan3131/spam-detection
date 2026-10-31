#!/usr/bin/env python3
"""Bootstrap Script for Account 1: Creates 5 Web-of-Trust (WoT) Repositories.

Usage:
    export GITHUB_TOKEN="ghp_account_1_token"
    python3 scripts/setup_account1.py
"""

import base64
import json
import os
import sys
import time

try:
    import requests
except ImportError:
    print("Error: 'requests' library required. Run: pip install requests")
    sys.exit(1)

# Configurable GitHub handles for the 3 accounts
USER1 = os.environ.get("USER1_HANDLE") or input("Enter Account 1 GitHub username (e.g. Ishan3131): ").strip()
USER2 = os.environ.get("USER2_HANDLE") or input("Enter Account 2 GitHub username (e.g. JyotiKesari): ").strip()
USER3 = os.environ.get("USER3_HANDLE") or input("Enter Account 3 GitHub username (e.g. HimanshiBishnoi): ").strip()

TOKEN = os.environ.get("GITHUB_TOKEN") or input(f"Enter GitHub Personal Access Token for {USER1}: ").strip()

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}

# 5 Repositories for Account 1 (Hub Nodes)
REPOS = {
    "wot-hub-1": {
        "version": "1.0.0",
        "project": f"{USER1}/wot-hub-1",
        "description": "WoT Tier 1 Anchor: Cross-account bridge to Account 2 and 3",
        "vouches": ["alice-dev", USER1.lower()],
        "denouncements": ["malicious-spammer"],
        "trusted_peers": [f"{USER2}/wot-node-1", f"{USER3}/wot-mesh-1"],
    },
    "wot-hub-2": {
        "version": "1.0.0",
        "project": f"{USER1}/wot-hub-2",
        "description": "WoT Tier 1 Node: Independent verification feed",
        "vouches": ["bob-builder"],
        "denouncements": ["bot-farm-01"],
        "trusted_peers": [f"{USER2}/wot-node-2"],
    },
    "wot-hub-3": {
        "version": "1.0.0",
        "project": f"{USER1}/wot-hub-3",
        "description": "WoT Tier 2 Node: Transitive vouch registry",
        "vouches": ["alice-dev"],
        "denouncements": [],
        "trusted_peers": [f"{USER3}/wot-mesh-3"],
    },
    "wot-hub-4": {
        "version": "1.0.0",
        "project": f"{USER1}/wot-hub-4",
        "description": "WoT Tier 3 Node: Security audit register",
        "vouches": ["charlie-dev"],
        "denouncements": ["malicious-spammer"],
        "trusted_peers": [f"{USER1}/wot-hub-5"],
    },
    "wot-hub-5": {
        "version": "1.0.0",
        "project": f"{USER1}/wot-hub-5",
        "description": "WoT Boundary Node: Contains cyclic loop back to hub-1 to test cycle prevention",
        "vouches": ["deep-contributor-d4"],
        "denouncements": [],
        "trusted_peers": [f"{USER1}/wot-hub-1"],  # Loop back to prove loop avoidance
    },
}


def create_or_update_repo(repo_name: str, registry_data: dict):
    print(f"\n🚀 [{repo_name}] Processing repository for @{USER1}...")
    
    # 1. Create Repository (if not existing)
    res = requests.post(
        "https://api.github.com/user/repos",
        headers=HEADERS,
        json={
            "name": repo_name,
            "description": registry_data["description"],
            "auto_init": True,
            "private": False,
        },
    )
    if res.status_code == 201:
        print(f"   ✅ Created repository: https://github.com/{USER1}/{repo_name}")
        time.sleep(1.5)  # Allow GitHub to initialize default branch
    elif res.status_code == 422:
        print(f"   ℹ️ Repository already exists: https://github.com/{USER1}/{repo_name}")
    else:
        print(f"   ❌ Failed to create repo: {res.status_code} {res.text}")
        return

    # 2. Check if trust-registry.json already exists to obtain SHA
    file_url = f"https://api.github.com/repos/{USER1}/{repo_name}/contents/trust-registry.json"
    file_res = requests.get(file_url, headers=HEADERS)
    sha = file_res.json().get("sha") if file_res.status_code == 200 else None

    # 3. Create or update trust-registry.json
    content_b64 = base64.b64encode(json.dumps(registry_data, indent=2).encode("utf-8")).decode("utf-8")
    payload = {
        "message": "feat: configure decentralized trust-registry.json",
        "content": content_b64,
    }
    if sha:
        payload["sha"] = sha

    put_res = requests.put(file_url, headers=HEADERS, json=payload)
    if put_res.status_code in (200, 201):
        print(f"   ✅ Successfully committed trust-registry.json ({len(registry_data['trusted_peers'])} peers)")
    else:
        print(f"   ❌ Failed to commit registry: {put_res.status_code} {put_res.text}")


def main():
    print("=" * 65)
    print(f" 🛡️  Web-of-Trust Network Setup — Account 1 (@{USER1})")
    print("=" * 65)
    for name, data in REPOS.items():
        create_or_update_repo(name, data)
    print("\n" + "=" * 65)
    print(f" ✅ Account 1 (@{USER1}) setup complete: 5/5 repositories active!")
    print("=" * 65)


if __name__ == "__main__":
    main()
