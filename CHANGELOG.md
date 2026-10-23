# Changelog

## Unreleased source snapshot — 2026-10-24

- Independent post-merge review found remaining missing-value excerpts: an archived support phone directory or a statement that the number changes could still pass token coverage. Require complete question content terms and syntactic phone/email/number values within the returned sentence. Keep the existing coverage floor and original fixture expectations.
- Expand the shared excerpt suite to 17 cases, preserving the intermediate `372a137a` baseline (11/17) and improving to 17/17. Python remains 49 tests; Node now has 27. The separate local eval remains 60/60 required and 60/62 overall, with the same two semantic failures.

## 2026-10-23 first sentence-selection repair (intermediate)

- Fix Python and browser lexical extraction to rank/validate the returned sentence, instead of letting title/whole-chunk evidence justify an unrelated first sentence. Preserve the 0.6 threshold and existing refusal/ACL checks; recognize explicit clock ranges as a sentence-local hours cue.
- Add ten shared synthetic excerpt cases with a preserved failing baseline; 2/10 improves to 10/10. Existing lexical fixtures and the local 60-required/2-semantic-probe contract remain unchanged.
- Synchronize roadmap, architecture, case study, interview and resume material around three distinct paths, including already-implemented local file ingestion and token identities.
- Delivery for this change is source commits plus the existing static Pages deployment, with no new package or Release. CI/deployment success must be checked on the resulting commit; it is not model-quality or production acceptance.

## Earlier source changes (historical)

- Added a conservative lexical answerability gate to Python and the static browser demo. Phone/email queries without supporting facts now refuse while retaining retrieved evidence in the trace.
- Added separate retrieval/answer fixtures and CI regressions, including short phone queries and a positive phone-source case. Exact-token coverage is not applied to semantic/hybrid paraphrases.

- Added maintenance, contribution, issue/PR, release-checklist, and reproducible failure documentation.
- Provider-backed answer quality remained `NOT_RUN`; this earlier maintenance entry did not create a Release or deployment. It is not a statement about later Pages runs.

## Historical public demo release

GitHub lists `v1.0.0` (2026-09-23) for the public demo. The current source has no declared package version. The tag remains historical and will not be moved. The next source-only fix Release uses the next unused patch above it (currently `v1.0.1`), explicitly as a commit-bound source snapshot. An installable package needs a declared package/install contract first. It does not establish production ACL, answer quality, or customer use.
