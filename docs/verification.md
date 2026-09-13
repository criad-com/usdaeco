# Verification scope

The source gate checks the usdAECO suite's own files, recorded release gitlinks,
portable paths and vocabulary. It does not rebuild or recursively lint released
submodules. Their licences and release evidence remain with their sources.

The 23 pins follow the scenarios release index except for two explicitly released
advances in `suite-overrides.json`: the full data-centre delivery and its IFC
reader. Tag commits, clean checkouts, the indexed gitlinks, generated `suite.json`,
flake inputs and [suite map](suite.md) are checked independently.

The skeleton gate applies the toolchain's applicability rules to the superproject.
Its suite adaptations check metadata, source layout, documentation targets,
image inventory and sanitization. The integrated artifact has its own
[stage gate and operating guide](../stage/README.md). It measures both forms,
stock composition and rendering, all registered validators, delivery and analysis
muting, source provenance, package ownership, views, size caps and reconstruction.
The manifest preserves raw validator severities and all stated deviations.

The older `aeco-toolchain` tag has no root `library.json`; its metadata card comes
from the release index. All other entries read their own committed metadata.
The imported schema guide's source hashes and narrow terminology substitutions
remain recorded in [site.json](site.json).

Nix packaging for this change is **not proven**. The single attempt used the
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
