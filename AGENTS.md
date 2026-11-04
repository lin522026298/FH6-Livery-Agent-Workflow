# Start here: natural-language Forza livery production

This repository is an executable workflow for an image-capable agent, not an image generation service. For a user livery request, read this file, `SKILL.md`, and relevant references. Follow the user's current requirements over defaults. Users provide themes, exact vehicles, references and visual feedback, not code or UV coordinates.

## First use on another computer

1. Keep user art, games, saves and generated projects outside this public checkout. Do not copy another user's installed profile, identity header, Custom library or old art. `.local/installation.json` is generated for this computer and ignored by Git.
2. On Windows x64, run `powershell -NoProfile -ExecutionPolicy Bypass -File bootstrap.ps1 -Workspace <dedicated project root>`. It installs pinned portable uv/Python, an independent environment, the source-built optimizer, FLS 1.3.0 and the existing public FH6Preview release; release archives are SHA-256 checked. It does not launch FLS or the game. Preserve incomplete installations and select a fresh ToolsRoot for retries.
3. Read `.local/bootstrap-result.json` and `.local/installation.json`. Use the generated `runtimePython` for scripts. Bootstrap performs synthetic fits, Custom tests and two isolated save imports; these never write actual Custom or saves. If the game directory was not uniquely discovered, ask for its location while continuing design/reference work. User-owned `Content/media/Cars` resources are required and not bundled.
4. Run `scripts/preflight.py` before actual vehicle work. The agent needs local file/CLI access, image viewing and a reference-capable image generator. Use the agent's available subscribed image tool; these scripts need no proprietary API key. If generation is not connected, the user can generate from your prompt/references and return the file. Do not silently replace the selected tool with code-drawn characters, SVG or a differently billed API.
5. Search `scripts/workspace.py cars <query>` for the exact year/variant, including FE/non-FE. Create a versioned private task with `workspace.py init`. All car tasks share the workspace's rolling-backup policy root.

## Production and interaction

- Confirm theme, exact vehicle, artwork choices and intended budgets. Offer actual generated concept images when choice is needed; don't require fitting knowledge from users. If fully delegated, choose a reasonable direction and show it at a meaningful review point.
- **Default character appearance follows the official original and specified form. Preserve distinguishing features. Explicit user adaptations take precedence.** Use original illustrations, reliable turnarounds and skill close-ups as identity evidence. A chosen concept can still have wrong hair, ears, costume or jewelry; correct these before fitting. Generated predecessors are not identity authority.
- Read native masks/XML, mesh/UV coordinates and visibility, then design characters and backgrounds together within the real layer budget. Prioritize faces and identity motifs over microtexture. Keep backgrounds recognizable, hair restrained and body paint intentional.
- Use `geometry.py masks`, `capture` and `fields` for raw domains and world-coordinate fields. Body-to-window continuation samples one clean master through shared world registration, then fits/groups each face separately. See `references/geometry-and-seams.md`. Never guess offsets from screenshots or reuse another car's silhouette.
- Use image generation for artwork and code for deterministic cropping/mapping/native fitting. Inspect the **actual fitter input** for beaded microstructure, fused hair/buildings and identity drift. If repeated repairs deteriorate it, regenerate from reliable references.
- Review actual PNGs at concept, master, native 2D and multi-view vehicle stages. Script PASS does not establish visual quality. Inspect composition, seams, holes, wheel arches, narrow strips and windows. Character identity, layout and technical correctness are separate gates.
- **Multiple rounds of human visual review and interactive changes may be needed.** Show version-labeled previews and accept natural language, screenshots, marks and files. Any step/part may be revised: scheme, character, background, seam, colour, decal, budget or import. A delivery is not immune to feedback. Within delegated autonomy, keep fixing visible defects without asking for every routine action.
- Text/logos/chibi decals default to separate reusable groups and reserves. User final placement is recommended; agent placement is optional. Reuse correct assets and economical native shapes rather than rebuilding letters pixel by pixel.
- Save numbered versions and compare the same position/size. After acceptance and after related processes end, clean only owned regenerable caches; retain masters, masks, parameters, scripts, native/DAT results, screenshots and reports. `cleanup_fit.py` handles the exact owned plan using PowerShell literal paths on Windows.

## Native preview, Custom and game import

Use `scripts/preview.py --exe <profile.previewExe> --input <whole-car project> --game <profile.gameContent> --output <new QA directory>`. Input and output must be independent directories; inspect resulting PNGs. This is an editor reference renderer, not in-game confirmation. No global input, focus theft or closing unsaved editor windows.

Read `references/windows-operations.md` for Custom and save import. Custom uses the actual user FLS process/context, ID-preserving merge/CAS and same-context readback. A script's registry view is not panel visibility. Preserve other entries; replace only intended IDs. Let the user save/reopen the editor when needed.

Only import when requested. Export private native data using the user's own legitimate identity header, verify counts/car/paint/hashes and require the game closed. Never import synthetic test identity into actual saves. If no private seed exists, guide the user through creating one in-game once. Default add-only; explicit replacement targets only the prior receipt's exact item.

**One full-save backup across the entire workspace, all cars/jobs.** Create and fully verify the new backup first; retain old ones until import and complete readback succeed. Then remove old complete ZIPs, preserving manifests/journals/verification. No damage report means the prior import is normal; don't reconfirm repeatedly. Damage reports/import failures create a hold and preserve related backups; resolve first. Use the bundled retention module, not old one-off importers.

The user applies the livery in-game, saves it in the livery menu, publishes and checks the shared result. Local write is not publication. Don't claim another platform, model, GPU or game version was validated if it wasn't.

## Maintaining the repository

Use synthetic fixtures. Don't commit personal paths, keys, saves, identity bytes, customer artwork or profiles. Read `SECURITY.md`, `THIRD_PARTY.md` and `docs/VALIDATION.md` before release. Preserve corresponding source, fixed tool hashes and original licenses. CI cannot certify likeness or aesthetics.

Use the bundled headless Workbench only for authored-file conversion, validation, verified backup, additive import and journaled readback. Its module/CLI contract is checked by `scripts/check_workbench_bundle.py`. Keep project-local Git history when useful; do not commit user identity, saves or image-model credentials.
