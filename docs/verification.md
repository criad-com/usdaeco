# Verification scope

The source gate checks the usdAECO suite's own files, recorded release gitlinks,
portable paths and vocabulary. It does not rebuild or recursively lint released
submodules. Their licences and release evidence remain with their sources.

The 22 public pins follow the scenarios release index and the explicit released
advances in `suite-overrides.json`, including the native architecture delivery,
its IFC reader and the study layout releases. Tag commits, clean checkouts,
the indexed gitlinks, generated `suite.json`,
flake inputs and [suite map](suite.md) are checked independently.

The skeleton gate applies the toolchain's applicability rules to the superproject.
Its suite adaptations check metadata, source layout, documentation targets,
image inventory and sanitization. The integrated artifact has its own
[stage gate and operating reference](../stage/README.md). The
[integrated-stage user guide](stage/index.html) explains the recorded evidence.
The stage gate requires exactly three roots and one project catalog, checks each
analysis namespace and its stored paths, and measures all three forms,
stock composition and rendering, all registered validators, delivery and analysis
muting, source provenance, package ownership, views, size caps and reconstruction.
The manifest preserves raw validator severities and all stated deviations.

The older `aeco-toolchain` tag has no root `library.json`; its metadata card comes
from the release index. All other entries read their own committed metadata.
The imported schema guide's source hashes and narrow terminology substitutions
remain recorded in [site.json](site.json), alongside current asset hashes including
the new integrated-stage page.

Nix packaging is **not proven**. The recorded stage release's single attempt used the
external registry documented by the toolchain and `--no-write-lock-file --no-build`.
It stopped when the public `usdSolid v0.1.6` input lookup returned HTTP 404.
No package was built and no lockfile was written. Native stage proofs use
existing development outputs, whose required ABI relationships are documented
in the stage guide.

Run the two gates and tests from the suite root:

```sh
env -u PYTHONPATH "$PYTHON" check.py
env -u PYTHONPATH "$PYTHON" -m pytest -q
env -u PYTHONPATH "$PYTHON" stage/check.py --record --rebuild
```

The last command needs the native environment described in the stage guide.
The delivered manifest records actual counts, per-rule warnings, per-folder
sizes and the reconstruction comparison rather than inferring success from
source checks alone.

For documentation work, `stage/check.py --use-evidence` can reuse successful
isolated probes only when their stage, code and runtime receipts match. Missing
receipts cause fresh probes; this is not an offline manifest-only gate. The checker
has no `--no-rebuild` option, and reconstruction runs only when requested explicitly.
If the native runtimes and reusable receipts are unavailable, report that the stage
gate was skipped and distinguish the committed proof from checks run for the change.
