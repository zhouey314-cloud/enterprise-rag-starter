# Changelog

## Unreleased

- Added a conservative lexical answerability gate to Python and the static browser demo. Phone/email queries without supporting facts now refuse while retaining retrieved evidence in the trace.
- Added separate retrieval/answer fixtures and CI regressions, including short phone queries and a positive phone-source case. Exact-token coverage is not applied to semantic/hybrid paraphrases.

- Added maintenance, contribution, issue/PR, release-checklist, and reproducible failure documentation.
- Provider-backed answer quality remains `NOT_RUN`; no public Release or deployment was made.

## Historical public demo release

GitHub lists `v1.0.0` (2026-09-23) for the public demo. The current source has no declared package version. The tag remains historical; the next version requires an explicit maintainer decision. It does not establish production ACL, answer quality, or customer use.
