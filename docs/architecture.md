# Architecture and known failures

The repository has three paths with different runtime and security boundaries.

| Path | Flow and boundary |
|---|---|
| Public static lexical demo | Synthetic JSON → illustrative scope filter → token overlap/title retrieval → top-K → best sentence by body evidence coverage → exact excerpt/citation or refusal. `web/app.mjs` imports `web/rag.mjs`; no authentication or model runs. Python `rag.py` adds overlapping chunks and implements the same excerpt rule. |
| Optional local semantic/hybrid baseline | `rag.py` uses normalized SentenceTransformer embeddings and cosine similarity; hybrid combines lexical/semantic ranks with weighted reciprocal-rank fusion. Access filtering precedes both branches. Dependencies/model must be available or the path errors; no silent lexical fallback. |
| Local file/identity library | `local_ingest.py` parses MD/PDF/DOCX; `localrag.py` manages SQLite, revisions/source hashes, dates, deletion, topic conflicts and server-stored tenant/role identities. `local_service.py` exposes operator CLI and authenticated loopback query/source HTTP endpoints. No browser upload or public HTTP ingestion. See [ADR](adr-local-rag.md) and [quickstart](local-quickstart.md). |

The lexical excerpt gate uses only the exact candidate sentence, never the title or another sentence. Highest question-term coverage wins; ties preserve source order. The provisional threshold remains 0.6. An explicit clock range supplies the “hours” cue within that same sentence, preserving the existing support-hours case without title leakage. No qualifying sentence means `NO_ANSWER`, no citation, and a retained retrieval trace. This fixes the [second-sentence defect](../FAILURE_ANALYSIS.md), but token overlap is still not semantic entailment and sentence splitting can omit context.

Semantic/hybrid extraction is unchanged by this repair: it still uses the first sentence of the selected chunk, and the 0.30 similarity threshold is provisional. A separately calibrated answerability evaluation is needed; this repair did not run a model. No generative LLM is configured.

The local library requires a trusted operator to attest input rights. Tokens cannot select their tenant/role; source lookup repeats ACL/current-version/date checks. New future revisions suppress older revisions, and conflicting eligible same-topic sources refuse. PDF page and DOCX paragraph locators are parser evidence, not rendered-layout claims. This is a local reference, not independently reviewed production IAM.

All supplied sources/labels remain `synthetic_unverified`. The user-reported review of 62 local cases is recorded in the [receipt](reviews/user-review-receipt-20261021.json); 60 required lexical cases pass and two semantic probes remain failures. Production extensions require authorized verified data, deployment/IAM review, independently governed Golden Sets, provider groundedness evaluation and monitoring.
