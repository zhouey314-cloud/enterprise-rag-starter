# Enterprise RAG Starter

An offline, inspectable RAG baseline using entirely fictional enterprise documents. It extracts a supported sentence with a document citation or says it has insufficient evidence.

![Architecture](docs/images/architecture.svg)

## Demo

Python 3.10+: `python3 rag.py "What are the support hours?"`; `python3 rag.py "lunar engine warranty"`; `python3 -m unittest discover -s tests`; `python3 evals/run.py`.

## Problem and architecture

Documents → parse → overlap chunk → metadata/access → lexical retrieval → rerank → context selection → extractive answer + citation. `EmbeddingProvider`, `VectorStore` and `LLMProvider` are explicit interfaces that return `NOT_CONFIGURED`; no model call is claimed. Access filtering happens before scoring. See [architecture](docs/architecture.md).

## Eval and verification

Ten tests cover chunking, access, citation, no-answer and provider states. Four `synthetic_unverified` fixture cases check retrieval and no-answer. Answer quality from a generative model is `NOT_RUN`; extractive answers may still omit nuance. Failure cases and next evaluation steps are documented. See [resume bullets](docs/resume-bullets.md) and [interview notes](docs/interview-notes.md).

## Status, privacy and roadmap

`IMPLEMENTED_AND_TESTED`: offline lexical retrieval, citation, access filter, deterministic fixtures. `NOT_CONFIGURED`: embeddings/vector store/LLM. `NOT_IMPLEMENTED`: PDF parser, semantic retrieval, production auth and provider-backed groundedness eval. All text is synthetic. Before production, add document versioning, authenticated ACLs, hybrid retrieval, expert reviewed Golden Set and trace evaluation. MIT.
