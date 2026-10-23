# Release checklist

The historical public `v1.0.0` demo Release remains immutable. Current source is run from a clone and has no installable-package version. The 2026-10-23 repair is a source/Pages update, not a new Release or package.

For the next authorized source-only fix Release, choose the next unused patch above `v1.0.0` (currently `v1.0.1`), bind it to the tested commit and label it a source snapshot. Recheck existing tags before choosing. Do not imply package installation or production readiness. A future installable package must declare its version and validate its separate installation contract before release. This checklist itself does not authorize publication.

- [ ] Choose and document the next version relative to historical tags; update changelog and source metadata together.
- [ ] Confirm `python3 -m unittest discover -s tests -v`, `python3 evals/run.py`, `python3 evals/answerability.py`, `python3 evals/excerpts.py`, `python3 evals/local.py` and `node --test tests/web.test.mjs` pass in a clean local setup and CI.
- [ ] If semantic/hybrid behavior is in scope, run `evals/modes.py` with a documented model/dependency snapshot; report blocked setup honestly.
- [ ] Check the [known false answer](../../FAILURE_ANALYSIS.md) and other applicable answerability cases (record their actual review/provenance status); report retrieval and answer quality separately.
- [ ] Check ACL filtering, citation, no-answer, top-K, and absence of real/private corpus data. Do not call caller-selected scope production auth.
- [ ] Verify README commands, local/static demo distinction, links, license, and known limitations.
- [ ] Fill the [release note template](RELEASE_NOTES_TEMPLATE.md) from actual evidence, then confirm publication is within the current explicit authorization and verify the resulting tag/assets.
