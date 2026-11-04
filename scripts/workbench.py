"""Expose the bundled native codec/backup CLI without launching a GUI."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'vendor/workbench-src'))
from fh6_livery_workbench.cli import main
if __name__ == '__main__': raise SystemExit(main())
