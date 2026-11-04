# Forza Livery Agent Workflow

Give this repository link to an image-capable local agent. Describe a theme and exact FH6 vehicle, supply references, choose a concept and revise the editable livery using natural language, screenshots and annotations.

[中文](README.md) · [Agent entry point](AGENTS.md) · [Quickstart](docs/QUICKSTART.md) · [Third-party tools](THIRD_PARTY.md)

The agent plans characters and backgrounds together, reads native paint domains/UV geometry, fits game-native layers within budgets, checks multi-view vehicle previews and continues characters onto windows. Small logos, text and chibi decals stay in separate groups; user final placement is recommended, with agent placement optional.

**Multiple rounds of human visual review, evaluation and interactive changes may be necessary.** A valid file does not establish likeness, aesthetics or seamless projection. Default characters preserve the official original appearance and specified form; explicit user adaptations override this default. Any step or part may be revised.

## Start with a link and request

> Read this repository's README, AGENTS.md and SKILL.md. Set up the tools on your accessible Windows machine. Design a livery for [exact make/model/year/variant] featuring [theme/character/form]. Use my references or collect appropriate ones. Show two generated concepts first, then produce the selected design. Reserve layers for separate small decals. I will review it with natural-language feedback and annotated screenshots; continue iterating as needed.

The agent follows [AGENTS.md](AGENTS.md) and can set up pinned tools automatically:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\bootstrap.ps1 -Workspace C:\LiveryProjects
```

Windows release setup needs no globally installed Python/compiler. Downloads are hash-checked, dependencies use an independent environment and game paths are discovered locally. Ask for essential paths only when discovery cannot resolve them. Setup does not launch the game or editor.

## Requirements

- An agent that can inspect images, read/write files and run commands. Provider-neutral; GPT-6.1 Sol/max or comparable/stronger multimodal capability is the recommended project baseline, not a cross-model benchmark.
- A reference-capable image generator, preferably included with the user's existing subscription. No proprietary image-model API key is required. If not connected, the user can generate from prompts/references and return files.
- Windows x64 and the user's own FH6 resources for complete preview/Custom/save integration. Other systems can plan and run some source-based 2D work; full integration needs a Windows host. A chat subscription alone does not supply local execution permissions or a game installation.
- Network, time and CPU resources. Generation/fitting need not succeed in one attempt.

Optimizer source and Windows release binary, template resources, fitting/assembly, headless [Workbench](https://github.com/lin522026298/FH6-Livery-Workbench) conversion/validation/import tools, native codecs, geometry capture, preview wrapper, actual-user-context Custom import and project-wide rolling backup installation are provided. FLS 1.3.0 and the public FH6Preview release are downloaded from their original repositories at pinned versions/hashes. See [THIRD_PARTY.md](THIRD_PARTY.md).

Production uses files, CLI and offscreen rendering without global input or closing unsaved user windows. Body/window continuation samples a shared master registered through world/UV coordinates, with separate budgets/groups. Body paint is selected intentionally; glass, brakes and wheels are separate decisions.

When requested, the agent exports private native data using the user's legitimate identity and installs with the game closed. One complete pre-import backup is retained across the workspace: verify the new backup first, prune older complete ZIPs only after import and full readback, retain manifests/logs. Damage reports or failures hold cleanup until resolved.

The user applies, saves and publishes/checks the livery in-game. Local file generation/import is not online publication.

Code is AGPL-3.0 with original component notices. No game resources, personal saves, identities, keys, real Custom libraries or private artwork are bundled. [Validation](docs/VALIDATION.md) distinguishes technical tests from human art acceptance, including a previous independent trial whose character likeness was not accepted.

The complete workflow has been tested on itasha. Other themes can use applicable design, fitting and inspection steps.
