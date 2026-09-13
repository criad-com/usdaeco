# Verification scope

The source gate checks this superproject's files and its recorded submodule
commits. It does not rebuild or recursively re-lint released repositories.
The submodules retain their release evidence, licences and documentation.

S01–S05 are adapted to the suite's root files, vocabulary, `suite` kind and
tier, `suite.json` pin list and generated flake inputs. S25 uses the pinned
toolchain's term patterns plus suite vocabulary and portable-path checks.
Only the exact required geometry-kit URLs and technical CSS/font syntax have
narrow syntax exceptions. All other files and lines remain subject to the
sweep, including tracked files even if they match an ignore rule.

S06–S24 and S27–S29 use the toolchain's applicability rules: this superproject
defines no schema or built example. S26 runs the toolchain's check-entry-point
contract. The gate also resolves each release tag in its initialized submodule,
compares HEAD and the indexed gitlink, rejects dirty submodules, checks generated
file freshness and verifies documentation targets and image inventory.

The older `aeco-toolchain` tag has no root `library.json`. Its kind, schema-domain
slot and requirements come from the scenarios release-index card; its tag and
commit are still independently resolved and checked. The other 22 entries read
their submodule metadata.

The imported guide has two prose terminology substitutions. Three assets are
byte-identical to their supplied originals; the schema guide otherwise retains
all bytes. Source and imported hashes are recorded in [site.json](site.json).

The Nix pin comparison is a pure evaluation assertion, also exposed as
`lib.pins`. Standard flake checks require a derivation, so `checks.<system>.pins`
wraps that assertion in a trivial stamp derivation. Use `--no-build` to evaluate
it without building the stamp or any package. The Python gate independently
verifies all 23 declared URL/tag pairs offline.

The single Nix attempt passed on `aarch64-darwin` in **12.68 seconds**, exit 0,
with `--offline --no-write-lock-file --no-build`. It used 23 explicit local
source overrides, the external registry described by the toolchain, and cached
upstream inputs. Both the pin-check derivation and default dev-shell derivation
evaluated. **Zero packages were built and no lockfile was written.** Nix omitted
`x86_64-linux`; that system and a realized dev shell are not proven. Public input
fetches were not exercised. Local Nix configuration emitted two unsupported-setting
warnings; neither prevented evaluation. No second attempt was made.

The source gate reports **56 checks, 0 failed, 0 not run**. Of its 29 skeleton
rows, 22 report not applicable to this suite; the other 7 execute suite or shared
checks. It verifies 23 clean release gitlinks, 3 fresh generated files, matching
versions, 6 documentation files with 119 resolved local links/fragments and
34 external references that were not fetched. The 4 site assets total
155,793 bytes; the original 1280×800 PNG is non-uniform and meets the image caps.
Pytest reports **37 passed** across pin drift, tag resolution, checkout preflight,
documentation failures and sanitization regressions.

Integrated-stage proofs remain not run; see the
[stage contract](../stage/README.md).
