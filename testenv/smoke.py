"""Run the source gate without an installed package."""
from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).resolve().parents[1] / "check.py"), run_name="__main__")
