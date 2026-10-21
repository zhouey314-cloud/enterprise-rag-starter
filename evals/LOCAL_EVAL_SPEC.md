# Local file/identity candidate eval contract

The target is the separate `localrag` SQLite library and authenticated loopback service. The existing four lexical retrieval fixtures, nine answerability fixtures, 23 original Python tests and 10 Node tests remain unchanged. Optional old semantic/hybrid adapters are not called by this suite. No model, embedding, paid API or customer/company data is used.

## Dataset and provenance

`local-corpus.json` contains 42 self-authored fictional source revisions (Markdown, four-page PDF and four-paragraph DOCX generated reproducibly by `local_fixtures.py`). `local-candidates.jsonl` contains 62 cases and 56 distinct question strings. Six access/tenant comparisons intentionally ask the same question under a different trusted identity. There are 60 required lexical cases: 38 supported facts and 22 refusals across missing attributes, role/tenant denial, expiry, future versions, deletion, stale revisions, tightened access metadata, conflicting topics and unrelated questions. There are also two semantic-paraphrase probes with supported-source expectations, predeclared as outside the lexical release contract. They remain in every full report and are never converted to expected refusals to fit the implementation.

Every source and case is `synthetic_unverified`; every row in `local-human-review.jsonl` is `needs_human_review`, with no reviewer, decision or approval timestamp. Source text, expected answers and checks were prepared in the same engineering workflow. Literal agreement is therefore a regression aid, not independent correctness evidence. The queue asks a human to check support/refusal, ACL/version/date/location and useful intent. This runner cannot promote a case to human-verified status. Business-critical real policies require independently reviewed inputs and expectations in a separate authorized workflow.

## Baseline and observed failures

The c83bb573 baseline passes 23 original Python tests, 10 Node tests, four lexical fixtures and nine answerability fixtures. File ingestion, trusted server identities and this new candidate dataset were `NOT_IMPLEMENTED`; an absent module is not treated as a historical product regression. Storage was reviewed separately, and real CLI/HTTP process tests then exposed a shared-PDF-title wrong-page defect; body evidence coverage fixed it with a preserved failing test.

The first executable candidate run, before lexical normalization, agreed on 58/62 full cases and 58/60 required cases. `contains` vs `contain` and the terminal Chinese question word `什么` produced false refusals despite retrieval of the expected source. Small lexical normalization fixes those cases without changing questions, expected labels, the 0.8 coverage threshold or the two semantic probes. The all-candidate metrics continue to include the two unsupported paraphrases. Their failure class is Retrieval/Answerability, not a fabricated successful refusal.

## Metrics and gates

`python evals/local.py --output .rag-data/eval/local-latest.json` writes all raw synthetic results, errors, counts, exact source hashes, Git revision/dirty status, Python/SQLite/pypdf versions and timestamps. It imports a fresh temporary corpus and issues ephemeral tokens; tokens are not written into reports. Each run is deterministic except timing, temporary locations, token bytes and DB internals. Fixture output bytes are reproducible.

- Retrieval Recall@1 and Recall@3 use supported-source cases as the denominator (40 full, 38 lexical required). They count expected document+version in the returned trace, independently of whether the answer is refused. The four-page PDF's page correctness is evaluated separately in citation agreement.
- Answer literal fixture agreement counts exact excerpt agreement on the same supported cases. It is not semantic correctness, factual reliability or completeness. Those remain `NOT_TESTED`.
- Citation source integrity counts responses with citations; it verifies actual current source membership, source-byte SHA-256, answer excerpt equality and independently derived fixture eligibility. Expected citation agreement separately checks document, version, PDF page or DOCX paragraph/Markdown line locator on every supported case. Refusals must have no citation/answer.
- Refusal precision is correct candidate refusals / all refusals; recall is correct candidate refusals / the 22 expected refusals. Unsupported paraphrases are false refusals in the full metrics.
- p50/p95 use the nearest-rank observed wall latency across every query, including authentication and SQLite retrieval. They exclude import, HTTP/network and model latency. They are local observations with no production SLO or capacity claim.

The required mechanical gate is zero required case-contract failures, zero access/version/date/deletion leaks and zero citation-integrity failures. Empty datasets, fewer than 50 distinct questions, duplicate IDs, missing review rows, invented provenance or undeclared optional capabilities fail closed. Unit fault injection deliberately corrupts citation hashes and verifies this gate fails. CI publishes the full candidate report even when a gate fails.

The runner's exit code reports this lexical mechanical gate only. Human semantic review and commercial/production acceptance are always `BLOCKED`; provider semantic quality is `NOT_TESTED`. The overall report remains `BLOCKED` even if the mechanical exit is zero. Required and all-candidate counts are both visible. Do not summarize a green CI job as 62/62 verified answers or a human-approved Golden Set.

## Regression and human review

Keep all old and new difficult cases. A changed expected answer, scope or optional/required flag requires source evidence and explicit review; do not modify it to obtain green results. A reviewer should inspect at least the body-only PDF-page failure, unsupported attribute refusals, every access/version/date/conflict case, both language normalizations and both semantic probes. Actual human decisions and natural-user acceptance remain outstanding; this source archive does not contain a claim they occurred.
