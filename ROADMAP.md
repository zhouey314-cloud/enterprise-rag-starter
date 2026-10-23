# Roadmap

This is an inspectable engineering reference with fictional documents. Capabilities belong to three distinct paths; a local capability is not automatically in the public website.

| Area | Public static lexical page / `rag.py --mode lexical` | Optional local semantic/hybrid | Local file/identity library |
|---|---|---|---|
| Input and storage | Synthetic JSON; Python overlapping chunks, web small document records | Same JSON corpus plus optional local SentenceTransformer cache | MD/PDF/DOCX ingestion, SQLite FTS5, source/metadata hashes, transactional revisions |
| Retrieval | Token overlap and top-K trace | Embedding cosine or weighted reciprocal-rank fusion | Authorized FTS5/overlap reciprocal-rank fusion |
| Identity and access | Caller-selected illustrative scope; no authentication | Same illustrative scope, filtered before both retrieval branches | Opaque token digests resolve server-stored tenant/role; CLI and loopback HTTP; not production IAM |
| Answer and refusal | Rank actual source sentences, require provisional 0.6 sentence coverage; refuse related hits without supporting excerpts | Existing first-sentence extraction; embedding relevance is not answerability and needs separate calibration | Body evidence coverage, exact excerpt/locator; refuse unavailable, inaccessible or conflicting evidence |
| Source lifecycle | Static demo metadata | Static demo metadata | Monotonic revisions, effective/expiry dates, deletion, metadata tightening, same-topic conflict refusal; source lookup rechecks eligibility |
| Evidence | Four original retrieval fixtures, nine answerability fixtures, ten excerpt regressions, Python/Node checks | Historical synthetic mode results; model execution NOT_RUN in this repair | 60/60 required lexical contracts; 60/62 all cases, with two semantic paraphrases still failing |

All data and candidate expectations remain `synthetic_unverified`. The user reported reviewing all 62 local candidates; the [receipt](docs/reviews/user-review-receipt-20261021.json) records that statement without inventing per-case decisions or upgrading ground-truth provenance. Historical queue/CI pending fields are earlier snapshots. Generative LLM/external vector providers remain `NOT_CONFIGURED`, provider quality `NOT_TESTED`, and commercial/production acceptance `BLOCKED`.

## Current

Preserve all three runnable paths, scope/identity boundaries, exact citations and the existing refusal tests. The [excerpt repair](FAILURE_ANALYSIS.md) fixes a deterministic wrong-sentence defect; it does not validate semantic entailment. Source commits and the public Pages deployment remain the distribution path. Historical `v1.0.0` stays unchanged; [release rules](docs/releases/RELEASE_CHECKLIST.md) explain the next unused patch snapshot.

## Next

- Independently review authorized real-policy sources and expected answers before business use; the reported 62-case review is not enterprise accuracy.
- Calibrate semantic/hybrid answerability with model-specific evidence; preserve the two local lexical paraphrase failures until a supported solution passes unchanged expectations.
- Add broader sentence-boundary, multi-sentence and semantic-support cases without weakening current gates. A clock-range cue and token overlap cannot prove entailment or completeness.
- Before another Release, bind the source snapshot, exact commit, install instructions and applicable evidence. No package restructuring is required for this repair.

## Later

Production identity/deployment review, external vector storage, provider-backed generation/groundedness evaluation and production trace monitoring remain future work. Local file ingestion, token identities, revisions and CLI/HTTP are already implemented and tested; production IAM is not.
