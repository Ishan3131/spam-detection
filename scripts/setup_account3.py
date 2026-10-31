#!/usr/bin/env python3
"""Bootstrap Script for Account 3: Creates 5 Web-of-Trust (WoT) Repositories.

Usage:
    export GITHUB_TOKEN="ghp_account_3_token"
    python3 scripts/setup_account3.py
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

TOKEN = os.environ.get("GITHUB_TOKEN") or input(f"Enter GitHub Personal Access Token for {USER3}: ").strip()

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}

# 5 Repositories for Account 3 (Mesh Cluster)
REPOS = {
    "wot-mesh-1": {
        "version": "1.0.0",
        "project": f"{USER3}/wot-mesh-1",
        "description": "WoT Cross-Link Mesh: Connects Account 3 into Account 2 and Account 1",
        "vouches": ["frank-dev", USER3.lower()],
        "denouncements": ["malicious-spammer"],
        "trusted_peers": [f"{USER2}/wot-node-3", f"{USER1}/wot-hub-4"],
    },
    "wot-mesh-2": {
        "version": "1.0.0",
        "project": f"{USER3}/wot-mesh-2",
        "description": "WoT Tier 3 Vouch Node: Confirms trusted contributors",
        "vouches": ["alice-dev"],
        "denouncements": [],
        "trusted_peers": [],
    },
    "wot-mesh-3": {
        "version": "1.0.0",
        "project": f"{USER3}/wot-mesh-3",
        "description": "WoT Distributed Security Feed: Denounces malicious actors",
        "vouches": ["grace-coder"],
        "denouncements": ["malicious-spammer"],
        "trusted_peers": [],
    },
    "wot-mesh-4": {
        "version": "1.0.0",
        "project": f"{USER3}/wot-mesh-4",
        "description": "WoT Intra-Account Loop Node: Tests cyclic resilience",
        "vouches": ["heidi-reviewer"],
        "denouncements": ["bot-farm-01"],
        "trusted_peers": [f"{USER3}/wot-mesh-1"],  # Intra-account loop
    },
    "wot-mesh-5": {
        "version": "1.0.0",
        "project": f"{USER3}/wot-mesh-5",
        "description": "WoT Independent Peer: Cross-links to Account 2",
        "vouches": ["ivan-maintainer"],
        "denouncements": [],
        "trusted_peers": [f"{USER2}/wot-node-2"],
    },
}


def create_or_update_repo(repo_name: str, registry_data: dict):
    print(f"\n🚀 [{repo_name}] Processing repository for @{USER3}...")
    
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
        print(f"   ✅ Created repository: https://github.com/{USER3}/{repo_name}")
        time.sleep(1.5)  # Allow GitHub to initialize default branch
    elif res.status_code == 422:
        print(f"   ℹ️ Repository already exists: https://github.com/{USER3}/{repo_name}")
    else:
        print(f"   ❌ Failed to create repo: {res.status_code} {res.text}")
        return

    # 2. Check if trust-registry.json already exists to obtain SHA
    file_url = f"https://api.github.com/repos/{USER3}/{repo_name}/contents/trust-registry.json"
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
    print(f" 🛡️  Web-of-Trust Network Setup — Account 3 (@{USER3})")
    print("=" * 65)
    for name, data in REPOS.items():
        create_or_update_repo(name, data)
    print("\n" + "=" * 65)
    print(f" ✅ Account 3 (@{USER3}) setup complete: 5/5 repositories active!")
    print("=" * 65)


if __name__ == "__main__":
    main()
