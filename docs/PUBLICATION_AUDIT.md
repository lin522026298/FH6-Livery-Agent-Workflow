# Publication audit — 1.3.0

The release source is checked by `scripts/audit_publication.py`. It checks the
exact source candidates for common credential formats, personal home paths,
runtime data, unreviewed binaries and game/Custom payloads. Findings report file
locations, never matched credential values. The new Git history and final source
archive are audited separately before publication.

Workbench 0.3.0 ships an explicit module/CLI manifest, checked by
`scripts/check_workbench_bundle.py` and pytest. Its headless tools convert authored
files, validate them, back up, import additively and read back journaled files.
Generic parsing/encoding remains available for these operations. No GUI is
included in this native tool package. The third-party FLS editor is obtained
separately at its pinned upstream release.

The Windows optimizer release includes corresponding C++ source, license,
compiler/flags, source and binary digests. `toolchain.lock.json` pins all download
archives. Classic Windows PowerShell computes hashes using system .NET. Runtime
settings, artwork, identities, real Custom and game saves stay outside Git.

These checks apply to this release's files and do not replace visual acceptance
or guarantee arbitrary future additions or third-party downloads.
