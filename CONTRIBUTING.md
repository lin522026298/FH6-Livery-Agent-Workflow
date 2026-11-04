# Contributing

Use synthetic assets and a dedicated workspace. Install development dependencies with `bootstrap.ps1 -Dev`, or use `requirements-dev.txt` and a source-built optimizer for synthetic-only work. Run `python -m pytest` from the repository and `scripts/self_test.py --output <new-directory>` with a valid local profile.

Never use real saves, customer identities or actual Custom libraries as CI fixtures. Preserve original licenses and source provenance. Keep paths/model providers configurable. A feature that requires an image model should use the host agent's capability or an explicit user-selected adapter, not silently introduce a paid API or require a secret for unrelated work.

Describe the problem, observed output and tested result. For art workflow changes, attach only publishable references and actual before/after renders; synthetic tests alone cannot justify a claim of better likeness. Preserve interactive user review and the ability to revise any stage or part.

Before publishing: run the publication audit, inspect the exact Git tree and release archive, retain corresponding source and fixed download hashes, and verify installation from a clean extraction. Record unverified platforms/quality claims honestly.
