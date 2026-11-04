# Privacy and safe local operation

The public source and release archives must contain only generic code, license/provenance records and synthetic examples. Do not attach private `header`, `C_livery`, whole-save ZIPs, actual Custom registry dumps, personal paths, account identifiers, model/API keys or full user workspaces to public issues.

For a suspected leak, use this repository's private vulnerability reporting if enabled, or privately notify the maintainer through GitHub. Describe the type and location without reposting the sensitive value. Revoke exposed credentials through the relevant provider; deleting the latest file alone does not remove Git history.

Local profiles are `.local/installation.json` and ignored. Task outputs and model images belong outside the source checkout. Bootstrap does not ask for model keys, modify file associations, close editors or launch the game. Release downloads are pinned and checked; partial/mismatched installs fail rather than silently selecting another version.

Save operations require the user's explicit task request, a closed game, a verified complete backup, exact target checks and full readback. Normal operation retains one complete backup across the workspace after success; damage/failure creates a cleanup hold. Manifests and journals are retained. Custom import merges in the actual user's FLS context and preserves unrelated entries.

Geometry observation attaches only to the new offscreen process created by the task. Custom's scoped bridge attaches to the intended user editor only for its configuration value. Neither is a game-memory import path. No global input/focus actions are required by the production workflow.

Run `python scripts/audit_publication.py` before committing/releasing. It checks tracked/candidate paths and common credentials/private data. CI adds tests and secret scanning where configured. A clean scan supports a bounded audit; it is not a promise that arbitrary future user files are safe to publish.
