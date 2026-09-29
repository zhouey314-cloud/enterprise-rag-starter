# Roadmap

This is an inspectable RAG engineering reference with fictional documents. Status refers to current source behavior.

| Area | Status | Boundary |
|---|---|---|
| Overlap chunking and document metadata | IMPLEMENTED | JSON synthetic corpus; no PDF ingestion or incremental index. |
| Lexical retrieval, top-K, trace | IMPLEMENTED | Token overlap; may select related but non-answering text. |
| Local semantic and hybrid retrieval | IMPLEMENTED locally | Optional cached SentenceTransformer; not on the public lexical web demo. |
| Access filtering | PARTIAL | Scope filter before scoring; demo scope is caller-selected, not authenticated ACL. |
| Citations and no-answer | PARTIAL | Cite selected chunk; no-answer only when retrieval has no hit. Citation is not answer correctness. |
| Eval and failure analysis | PARTIAL | Synthetic retrieval fixtures; no expert-reviewed answerability/model-quality evaluation. |
| LLM and external vector providers | NOT_CONFIGURED | Interfaces fail closed; no generative answer runs. |

## Current

Preserve reproducible lexical, local semantic/hybrid, citation, ACL-filter, and no-answer mechanics. Record observed failures such as the [support-phone false answer](FAILURE_ANALYSIS.md) without claiming model quality. Resolve the historical `v1.0.0` tag versus unversioned source before another release.

## Next

- Create a small human-reviewed answerability regression set, including unanswerable questions that still retrieve related documents.
- Require the same evaluated query/answer/citation behavior for lexical and optional semantic/hybrid modes; separate retrieval metrics from answer correctness.
- Define a version/install contract and reproducible dependency/model snapshot before a new tag.

## Later

Planned only: provider-backed answer eval, authenticated ACL, document ingestion/versioning, and replaceable vector storage. None is present in the public demo.
