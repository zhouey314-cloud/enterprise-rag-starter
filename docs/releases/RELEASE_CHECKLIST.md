# Release checklist

**BLOCKED:** a historical public `v1.0.0` demo Release exists, but current source has no declared version. Decide numbering and the distribution contract before any new tag. This checklist does not authorize publication.

- [ ] Choose and document the next version relative to historical tags; update changelog and source metadata together.
- [ ] Confirm `python3 -m unittest discover -s tests -v` and `python3 evals/run.py` pass in a clean local setup and CI.
- [ ] If semantic/hybrid behavior is in scope, run `evals/modes.py` with a documented model/dependency snapshot; report blocked setup honestly.
- [ ] Check the [known false answer](../../FAILURE_ANALYSIS.md) and other human-reviewed answerability cases; report retrieval and answer quality separately.
- [ ] Check ACL filtering, citation, no-answer, top-K, and absence of real/private corpus data. Do not call caller-selected scope production auth.
- [ ] Verify README commands, local/static demo distinction, links, license, and known limitations.
- [ ] Fill the [release note template](RELEASE_NOTES_TEMPLATE.md) from actual evidence, then obtain a separate explicit decision to tag/publish.
