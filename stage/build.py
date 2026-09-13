"""Build the integrated stage from the suite's pinned submodules."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from usdaeco_suite.stage_build import main
if __name__ == '__main__':
    raise SystemExit(main())
