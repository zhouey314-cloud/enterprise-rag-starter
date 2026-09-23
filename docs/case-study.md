# Enterprise RAG Starter — case study

## Problem
An enterprise knowledge assistant must retrieve the right accessible document, show where an answer came from, and refuse when evidence is missing.

## Context
The corpus is four fictional policy documents. The online demo is lexical; local Python offers actual embedding-based semantic and hybrid retrieval.

## Constraints
The public static host cannot run a private embedding service or secure ACL. All online records are synthetic, and scope switching is illustrative.

## My Role
I built chunking, ACL-first retrieval, citation/no-answer behavior, local semantic adapter, hybrid ranking, browser explorer, tests and eval runner.

## Architecture
Documents become metadata-bearing chunks. Access filtering precedes lexical overlap or normalized sentence-embedding cosine ranking. Hybrid uses weighted reciprocal-rank fusion. The highest-ranked accessible chunk supplies an exact sentence and citation.

## Key Decisions
Keep lexical as a transparent baseline, make semantic an optional replaceable local adapter, and never silently fall back from semantic to lexical. Display scores, access scope and no-answer reason.

## Hardest Problem
The first hybrid weighting let a generic lexical overlap outrank the correct semantic paraphrase. The synthetic failure was kept in eval; semantic weight was increased and the same cases rerun.

## Failure/Tradeoff
Lexical matching can miss synonyms or match generic words. Embedding similarity can return merely related text. The 0.30 semantic threshold is provisional for this tiny corpus.

## Testing
19 Python unit tests; 4 legacy lexical fixtures; local mode eval: lexical 5/5, semantic 8/8 and hybrid 8/8 synthetic cases. Browser checked public employee-policy no-answer versus team-scope retrieval.

## Eval
Retrieval Recall@1, citation correctness, no-answer, ACL leakage and top-K are separate gates. All labels are `synthetic_unverified`; generative answer quality is `NOT_RUN`.

## Current Evidence
[Online lexical explorer](https://zhouey314-cloud.github.io/enterprise-rag-starter/) · [eval spec](../evals/PROJECT_EVAL_SPEC.md) · [runner](../evals/modes.py) · [source](../rag.py).

## Limitations
No real documents, authenticated scope, PDF ingestion, expert-verified labels or production vector index. The answer is extractive, not generated.

## What I Would Do in Production
Add verified ingestion/versioning, authenticated ACLs at every retrieval stage, a calibrated no-answer threshold, human-reviewed eval sets and trace monitoring.

## What I Learned
Retrieval success, citation presence and answer validity are different claims; hybrid ranking requires its own regression cases.
