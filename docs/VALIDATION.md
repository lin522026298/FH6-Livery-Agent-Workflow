# Validation

Version 1.3.0 validates the bundled headless Workbench module hashes and CLI
contract, synthetic native conversion, owned-output staging, isolated additive
installation/readback/rollback, preservation of existing files, rolling backup
rotation and incident holds. The workflow also tests real fitting on synthetic
RGBA input, Custom append/idempotence/precise replacement and path boundaries.

Run `python -m pytest` and `python scripts/check_workbench_bundle.py` in the
configured runtime. `scripts/self_test.py` creates only synthetic artwork and an
isolated fake save. It never starts FLS/game or writes actual Custom/game data.
Fresh Windows CI follows the documented PowerShell bootstrap and builds the
optimizer from included C++ source. Release verification records exact source,
module, build and download hashes. See PUBLICATION_AUDIT.md.

Technical tests do not establish the visual quality of a newly generated design.
The user must review character fidelity, anatomy, composition, seams and the
real rendered result. The project grew from accepted iterative vehicle/decal
work. A previous independent exercise passed its technical checks but later
failed user review of character fidelity; its broad art acceptance was withdrawn.
No private case art or real saves are public test fixtures.

The workflow has been fully exercised on itasha only. Other themes should reuse
the relevant steps and be reviewed for their own requirements. New vehicles,
kits, model providers and image generators require their own validation.
