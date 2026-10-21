# ADR: authenticated local FTS reference

Status: selected for implementation, 2026-10-21. The existing browser/lexical demo stays illustrative; it does not become an authentication system.

Use Python standard-library SQLite/FTS5, a small loopback JSON HTTP adapter, and a local administrator CLI. Persist document revisions/chunks transactionally. Hash both input bytes and security/version metadata so an ACL/date change cannot be mistaken for an unchanged file. Only the latest non-deleted revision is eligible, within its effective/expiry interval. Fail closed for conflicting eligible sources in the same explicitly assigned topic.

Identity is a random opaque bearer token issued to a mode-0600 file by the trusted local administrator. Store its digest, tenant and role on the server. Query clients cannot submit tenant, role, scope or historical dates. Filter eligible chunks before ranking; use an authorized in-memory FTS5 snapshot so another tenant's corpus cannot affect BM25 statistics. Fuse BM25 and deterministic token-overlap ranks using RRF. This is deliberately a bounded laptop reference, not a scalable multi-tenant hosted service.

MD uses line locators; PDF uses real parser page numbers; DOCX uses paragraph locators and page=null because physical pagination is not reliably stored in DOCX. Never invent page numbers. Only operator-attested licensed local files are imported; no remote URL ingestion, OCR, external relationship fetching, model/API calls or embedding downloads.

Answers are exact evidence excerpts with version/date/hash/location citations and a provisional lexical coverage gate. Conflict/insufficient evidence means refusal. This is not semantic entailment. Candidate synthetic cases and a human-review queue will report retrieval, answer, citation and refusal metrics separately; human/semantic acceptance remains BLOCKED until actual review.

Three review units: storage/parsing/version/access library; authenticated CLI/HTTP plus process regressions; candidate evaluation/metrics/quickstart/CI. Preserve all existing tests and cases. Rollback by normally reverting the focused PR; the original worktree and round-one checkout are not integration targets.
