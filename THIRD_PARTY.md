# Tools, source and distribution

|Component|Role|License / distribution|
|---|---|---|
|This workflow, native adapters, optimizer and bridges|Natural-language planning, fitting, assembly, geometry/Custom/save integration|AGPL-3.0 for this combined repository; source included. Original component licenses remain applicable|
|[ForzaLiveryStudio](https://github.com/Arstz/ForzaLiveryStudio), 1.3.0|Editor, native resources and user Custom library|AGPL-3.0. Download the original `windows_x64.zip` by fixed URL/hash; do not repackage the user's installation. Source at the original tagged repository|
|[FH6-Background-Preview](https://github.com/lin522026298/FH6-Background-Preview), 1.0.0|Offscreen native vehicle renderer and preview wrapper|AGPL-3.0; existing public source and matching Windows release linked and hash-pinned. Game resources remain user supplied|
|[Forza Painter FH6 GPT branch](https://github.com/DDDuoDuo/forza-painter-fh6-gpt), source baseline `29a827d503bb9cba4e9aa3eaf873d97b3e6eb240`|Basic shape templates/data and ecosystem basis|Original MIT, GPT Edition and custom importer notices retained under `licenses/`. Full GUI/API service not required by this workflow|
|[Hx-zh/fh6-livery-viewer](https://github.com/Hx-zh/fh6-livery-viewer), Workbench baseline `199616a936d4fae9517ebeeb1707a8f2ecd36be8`|Save/header discovery and native format reference|AGPL-3.0; attribution retained in bundled Workbench `THIRD_PARTY.md`|
|[FH6 Livery Workbench](https://github.com/lin522026298/FH6-Livery-Workbench), 0.3.0|Headless authored-file conversion, validation, backup, import/readback|AGPL-3.0 source and exact module manifest under `vendor/workbench-src`|
|[uv](https://github.com/astral-sh/uv)|Portable Python/environment/dependency setup|MIT OR Apache-2.0; downloaded from a fixed official release with hash. Licenses/source available at that release|
|Python, NumPy, Pillow, OpenCV, Frida, pytest|Runtime and development dependencies|Installed at versions in requirements files; their original licenses apply. They are not relabeled as project-owned code|
|GCC/MinGW toolchain|Build the C++17 optimizer in CI|Compiler and runtime licenses/exceptions apply. Release includes corresponding optimizer source, compiler/flags and source digest. A local compiler is optional for Windows users|

Original copyright/license texts are preserved. This repository does not bundle game models/textures, personal save containers, account identity headers, real Custom libraries, API credentials, subscription access or private artwork. Character/game assets obtained by a user remain under their own applicable terms and are not relicensed by this code license.

FLS and the previewer are unmodified runtime dependencies, so fixed official release references are sufficient here. Only actually needed code is vendored with provenance. No redundant fork is presented as newly authored software. Native codecs inherit the relevant AGPL obligations; this combined distribution is not advertised as wholly MIT.

`toolchain.lock.json` pins download archives. The preview protocol also verifies its executable hash before observing an owned renderer. Unsupported versions are not silently substituted. Model/image generation services are selected by the user/agent capability and are outside the software distribution.
