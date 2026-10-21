# Enterprise RAG Starter

**LIVE_DEMO (lexical) + LOCAL semantic/hybrid** · [Try the browser demo](https://zhouey314-cloud.github.io/enterprise-rag-starter/) · [Case study](docs/case-study.md) · [Resume bullets](docs/resume-bullets.md) · [Interview notes](docs/interview-notes.md)

An inspectable RAG demo using entirely fictional enterprise documents. The online page is a lexical baseline; optional local Python modes use a real sentence-embedding model for semantic and hybrid retrieval. Each mode extracts a source sentence with citation or reports insufficient evidence.

![Real browser capture of the synthetic lexical query with extractive answer and citation](docs/images/demo-query.png)

The image is a capture of the public lexical demo, not a generative model answer or production quality result.

![Architecture](docs/images/architecture.svg)

## Demo

Online lexical demo: <https://zhouey314-cloud.github.io/enterprise-rag-starter/>. Try support hours, refund policy, security, employee policy (public no-answer; team-scope fictional document visible), and no-answer. The page shows answer, source, retrieved chunks, scores, access and no-answer reason. Scope selection is illustrative, not real authentication.

Python 3.10+: `python3 rag.py "What are the support hours?"`; `python3 rag.py "lunar engine warranty"`; `python3 evals/run.py`. For the full Python suite, first install `requirements-local.txt` in an isolated environment, then run `python3 -m unittest discover -s tests`; the file-format tests need the pinned PDF parser, with no model download.

Local semantic/hybrid setup:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-semantic.txt
HF_HOME="$PWD/.model-cache" .venv/bin/python rag.py "When can I reach customer service?" --mode semantic
HF_HOME="$PWD/.model-cache" .venv/bin/python rag.py "What is the refund policy?" --mode hybrid --top-k 2
HF_HOME="$PWD/.model-cache" .venv/bin/python evals/modes.py
```

The first semantic run downloads `sentence-transformers/all-MiniLM-L6-v2` from Hugging Face into the ignored local cache. No API key is needed. Without installed dependencies or model access, semantic/hybrid raise an error; they never silently become lexical.

## Problem and architecture

Documents → parse → overlap chunk → metadata/access → lexical or local embedding cosine search → optional hybrid reciprocal-rank fusion → top-K selection → extractive answer + citation. The embedding adapter is replaceable; `LLMProvider` remains `NOT_CONFIGURED`, and no generative model runs. Access filtering happens before scoring in every mode. See [architecture](docs/architecture.md).

## Eval and verification

Twenty-three Python tests cover chunking, access, citation, no-answer, top-K, mode routing, answerability and provider states. The support-phone regressions confirm a related support-hours chunk is refused without a citation in lexical mode, while a source that contains a phone number remains answerable. Ten Node tests cover the static web logic using the same fixtures. Four `synthetic_unverified` lexical fixtures remain as baseline; `evals/modes.py` checks retrieval Recall@1, citations, ACL, no-answer and top-K for lexical, semantic and hybrid, including paraphrases. Run `python3 evals/answerability.py` for separate retrieval and extractive-answer checks on nine synthetic fixtures; run `node --test tests/web.test.mjs` for browser-logic regressions. The coverage threshold is a provisional lexical heuristic, not semantic entailment. It is not applied to semantic/hybrid modes: their paraphrases need model-specific answerability evaluation. Optional semantic modes require the dependency and model; see [eval specification](evals/PROJECT_EVAL_SPEC.md). Answer quality from a generative model is `NOT_RUN`; extractive answers may still omit nuance. See [resume bullets](docs/resume-bullets.md) and [interview notes](docs/interview-notes.md).

## Local file/identity library (separate from the static demo)

`localrag.KnowledgeStore` adds transactional MD/PDF/DOCX ingestion, source-byte and metadata hashes, monotonically increasing revisions, effective/expiry dates (expiry is exclusive), deletion, server-stored tenant/role identities and authorized FTS5/overlap RRF extraction. Install `requirements-local.txt`; run the existing unittest command. PDF pages are parser page numbers; DOCX uses paragraph locators with `page=null`, because physical layout has not been rendered. A newly imported future revision suppresses the previous revision and conservatively refuses until effective; it does not silently resurrect old policy. Conflicting eligible sources in the same administrator-assigned topic refuse even for top-K=1.

The trusted local operator must attest rights for each input. Tokens are opaque and stored only as digests in the database; callers cannot choose tenant/role through the query API. This library is not production IAM. The public static page still has illustrative scope selection. See [the local architecture decision](docs/adr-local-rag.md).

`python local_service.py --help` exposes the trusted operator CLI. Use `init`, `issue-identity`, `ingest --metadata ... --rights-attested`, `delete` and `revoke-identity` locally. Identity files are created exclusively with mode `0600`; the token is never printed. `query --token-file ...` and `source DOC_ID VERSION --token-file ...` use that identity. `serve --port 8767` binds only `127.0.0.1`; clients send `Authorization: Bearer <token>` to `POST /query` with only `question` and optional `top_k`, or to `GET /sources/DOC_ID/VERSION`. Client-supplied tenant, role, scope, identity and historical dates are rejected. Source lookup repeats current-version/date/ACL checks. This service does not expose ingestion over HTTP or enable cross-origin browser access.

The Python suite includes real child-process CLI/HTTP checks for all three formats, token revocation, denied tenant/role access, updates/deletion, expiry/conflicts and malformed requests. Those tests discovered that a shared PDF title could make the wrong page appear answerable. Extraction now requires question-term coverage in the page body; titles still help retrieval. This remains a conservative lexical heuristic, not a semantic correctness check.

Follow [the complete fresh-environment quickstart](docs/local-quickstart.md) to generate fictional MIT-licensed MD/PDF/DOCX files, provision private identities, import/update/delete, start the HTTP service, query and inspect sources, and reproduce denial and revocation. No model or embedding is called. Run `python evals/local.py` for 62 `synthetic_unverified` candidate cases (56 distinct questions), with separate retrieval, citation, literal-answer agreement, refusal and observed p50/p95 metrics. The required lexical contract covers 60 cases; two semantic-paraphrase probes remain visible failures in the full metrics. The user subsequently reported completing review of all 62 cases; see the [current user-review receipt](docs/reviews/user-review-receipt-20261021.json), bound to the reviewed candidate and queue hashes. Individual case decisions were not separately supplied. The queue and CI `pending62`/human-gate fields retain the earlier snapshot; they do not mean the user is currently waiting to review. Source/ground-truth provenance remains `synthetic_unverified`; semantic quality is `NOT_TESTED` and overall/production acceptance stays `BLOCKED`. See [the candidate eval contract](evals/LOCAL_EVAL_SPEC.md) and [human-review queue](evals/local-human-review.jsonl).

## Status, privacy and maintenance

`IMPLEMENTED_AND_TESTED`: offline lexical retrieval, local optional semantic/hybrid retrieval, citation, access filter, deterministic synthetic fixtures and the separate local file/identity library. `DEPLOYED_STATIC_APP`: online lexical-only interface. `NOT_CONFIGURED`: generative LLM and external vector store. `NOT_IMPLEMENTED`: production authentication and provider-backed groundedness eval. All supplied text is synthetic. Before production, add verified policy data, independently reviewed deployment/IAM, expert-reviewed Golden Set and trace evaluation. MIT.

This source currently has no declared package version. GitHub has a historical `v1.0.0` public demo Release; it is not evidence that this engineering reference is production-ready. A new version/tag requires a separate numbering and release decision. See the [capability roadmap](ROADMAP.md), [reproduced failure analysis](FAILURE_ANALYSIS.md), [changelog](CHANGELOG.md), [contribution guide](CONTRIBUTING.md), and [release checklist](docs/releases/RELEASE_CHECKLIST.md).
