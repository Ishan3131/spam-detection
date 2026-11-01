A GitHub bot that helps open-source projects share contributor reputation without a central authority.
Each repo publishes a trust-registry.json listing the contributors it vouches for, the ones it denounces, 
and the peer projects it trusts. When a pull request is opened, the bot walks this peer network up to three hops, 
weights each vouch or denouncement by distance (closer peers count more), and adds up a score. High scores get a trusted-contributor label, 
very low scores get a suspicious label with an explanatory comment, and everyone in between, 
including brand-new contributors with no history, is left untouched for human review.
