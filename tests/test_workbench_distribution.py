import importlib.util
from pathlib import Path
def test_native_distribution():
    path=Path(__file__).resolve().parents[1]/"scripts/check_workbench_bundle.py"
    spec=importlib.util.spec_from_file_location("bundle_contract",path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.main()
