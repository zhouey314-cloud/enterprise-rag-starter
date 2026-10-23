# Enterprise RAG Starter — case study

## Problem and context

A knowledge assistant must retrieve accessible evidence, return the relevant excerpt with a traceable source, and refuse when evidence is insufficient. This self-built reference uses fictional data and keeps three paths explicit: a public lexical browser demo, optional local embedding-based semantic/hybrid retrieval, and a local file/identity library.

## Implementation and boundaries

The public demo filters illustrative caller-selected scope before retrieval. The optional local modes use a real SentenceTransformer adapter and weighted reciprocal-rank fusion, fail when dependencies/model are missing, and do not silently fall back. The separate local library ingests MD/PDF/DOCX transactionally, tracks source hashes and revisions, enforces effective/expiry/deletion/conflict rules, and resolves opaque tokens to server-stored tenant/role identities. Operator CLI and loopback HTTP queries/source lookup are covered by child-process tests. This is not production IAM, and local capabilities are not hosted by the static website.

My work covers the public implementation, tests, eval runners and documentation. No company code, customer deployment, production accuracy or commercial outcome is claimed.

## Failure and repair

The lexical path previously judged answerability from a title and entire chunk, then always returned the first sentence. With “Our office has a garden. The support phone number is 555-0100.” it returned the garden sentence. The repair ranks the actual sentences by body evidence, retains the provisional 0.6 coverage floor, additionally requires all question content terms and requested phone/email/numeric values, and refuses if none qualifies. Titles remain retrieval-only. An explicit clock range supplies a sentence-local “hours” cue, preserving the existing support-hours case. Shared Python/JavaScript fixtures cover later sentences, misleading titles, refusal, ACL and exact citations.

This is a deterministic extraction fix. Token coverage is not entailment; semantic/hybrid extraction remains a separate known limitation. The earlier hybrid-weighting experiment and historical mode counts do not establish current model quality.

## Verification

At the 2026-10-23 repair: 49 Python tests and 36 Node tests pass; four original retrieval and nine answerability cases remain unchanged. The first ten shared excerpt cases improved from 2/10 on baseline `45e2daa8` to 10/10. Independent review then exposed missing-value cases; the expanded set improved from 11/17 on intermediate commit `372a137a` to 17/17; subsequent hours-reference cases improved the final set from 18/21 to 21/21. Five Unicode boundary cases then brought the fixed set to 26/26 in both languages (from Python 23/26, JavaScript 24/26). All failing baselines are preserved; no prior gate regressed. The separate local eval still passes 60/60 required lexical contracts and 60/62 all-candidate contracts; the same two semantic-paraphrase probes fail. Citation/access integrity gates pass. See [failure evidence](../FAILURE_ANALYSIS.md), [excerpt runner](../evals/excerpts.py) and [local eval contract](../evals/LOCAL_EVAL_SPEC.md).

All cases remain `synthetic_unverified`. The user reported reviewing all 62 local candidates, recorded by the [receipt](reviews/user-review-receipt-20261021.json); no itemized verdicts or independently verified enterprise ground truth were supplied. Optional model execution was not rerun in this repair. Generative answer quality is `NOT_RUN`, provider semantics `NOT_TESTED`, and production acceptance `BLOCKED`.

## Evidence and next work

[Online lexical explorer](https://zhouey314-cloud.github.io/enterprise-rag-starter/) · [architecture](architecture.md) · [local quickstart](local-quickstart.md) · [source](../rag.py) · [eval spec](../evals/PROJECT_EVAL_SPEC.md).

Before real enterprise use, add authorized verified policies, independently reviewed deployment/IAM, human-governed expectations, calibrated semantic answerability and trace monitoring. A citation identifies evidence; it does not itself establish correctness, completeness or production safety.
