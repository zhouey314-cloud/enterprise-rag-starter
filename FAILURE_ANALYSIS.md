# Failure analysis

Observed on 2026-09-29 from current `main` with the fictional corpus:

```bash
python3 rag.py 'What is the support phone number?'
```

The lexical path returned `status=EXTRACTIVE`, cited `support:0`, and answered with the fictional support **hours** sentence. That chunk contains no phone number. The citation is structurally valid, but the answer does not address the question. No LLM ran.

| Field | Finding |
|---|---|
| Expected behavior | `NO_ANSWER` or an explicit absence-of-phone-number response after answerability checking. |
| Observed behavior | Related support chunk selected; first sentence returned as answer. |
| Likely cause | Retrieval matches “support”, then `answer()` always extracts the first sentence of the top chunk. This is a code-path inference, not a validated root-cause fix. |
| Category | Retrieval relevance / answerability / citation interpretation. |
| Severity | High for real policy questions; the demo has fictional data only. |
| Current gate | Existing four lexical fixtures and 5/8/8 mode cases do not include this question; passing them does not cover this failure. |
| Follow-up | Add a human-reviewed expected outcome and regression case, then change answerability logic with before/after eval. Keep retrieval Recall@K and answer correctness as separate metrics. |

Other known limits: lexical mode misses paraphrases; semantic similarity can retrieve related but non-answering chunks; the 0.30 threshold and hybrid weights are provisional; caller-selected scope is not authentication. See [eval specification](evals/PROJECT_EVAL_SPEC.md) and [architecture](docs/architecture.md). `MODEL_QUALITY=NOT_RUN` remains the provider-backed answer-quality state.
