"""Run the integrated stage proofs; summary contract: N checks, M failed."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from usdaeco_suite.stage_check import main
if __name__ == '__main__':
    raise SystemExit(main())
