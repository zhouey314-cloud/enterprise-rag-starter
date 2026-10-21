# Failure analysis

Observed on 2026-09-29 from current `main` with the fictional corpus:

```bash
python3 rag.py 'What is the support phone number?'
```

The lexical path returned `status=EXTRACTIVE`, cited `support:0`, and answered with the fictional support **hours** sentence. That chunk contains no phone number. The citation is structurally valid, but the answer does not address the question. No LLM ran. The repaired lexical path checks coverage of question terms in the top hit title and text; insufficient coverage returns `NO_ANSWER` without a citation and exposes `QUESTION_NOT_ANSWERABLE_BY_TOP_HIT` in the trace. The same rule runs in the static browser demo. The expected outcome is encoded in `tests/test_rag.py::test_support_phone_number_is_unanswerable`.

| Field | Finding |
|---|---|
| Expected behavior | `NO_ANSWER` or an explicit absence-of-phone-number response after answerability checking. |
| Observed behavior | Related support chunk selected; first sentence returned as answer. |
| Likely cause | Retrieval matches “support”, then `answer()` always extracted the first sentence of the top chunk without checking whether the retrieved text covered the requested information. |
| Category | Retrieval relevance / answerability / citation interpretation. |
| Severity | High for real policy questions; the demo has fictional data only. |
| Current gate | Unit regressions assert refusal, no citation, a related retrieval trace and an answerability reason; a positive phone fixture prevents a keyword blacklist. `evals/answerability.py` reports retrieval and extractive-answer checks separately. |
| Follow-up | Human-review a broader answerability set and evaluate semantic/hybrid entailment independently; this lexical heuristic does not establish semantic or model answer quality. |

Other known limits: lexical mode misses paraphrases; semantic similarity can retrieve related but non-answering chunks; the 0.30 threshold and hybrid weights are provisional; caller-selected scope is not authentication. See [eval specification](evals/PROJECT_EVAL_SPEC.md) and [architecture](docs/architecture.md). `MODEL_QUALITY=NOT_RUN` remains the provider-backed answer-quality state.

## 2026-10-21 offline regression comparison

On remote baseline `89b9d3184bf2e6f6728dba3d8e79db101c9e99a9`, 19 unit tests and the original four lexical fixtures pass despite the phone failure. On the nine new `synthetic_unverified` fixtures, retrieval targets pass 9/9 (Recall@1 = 7/7 for non-empty targets), while extractive answers pass 6/9: phone, short phone and email queries incorrectly return hours. The preserved local patch improves answers to 8/9 but still answers `support phone` with hours at exactly 0.5 coverage.

The candidate uses a provisional 0.6 lexical coverage threshold, passes 9/9 answer checks with unchanged retrieval targets and no ACL failures, and preserves supported hours, refunds and team-scope cases. It does not claim general answer correctness: titles may be misleading, unrelated words can overlap, and the first extracted sentence can omit required facts. Exact-token coverage is deliberately limited to lexical mode; applying it to semantic paraphrases would confuse missing words with missing evidence.

Current optional semantic/hybrid execution is **BLOCKED** by `SEMANTIC_DEPENDENCY_MISSING`; no dependencies or models were downloaded for this repair. Mocked routing tests do not count as model evaluation. Generative-model answer quality and independent human semantic review remain `NOT_RUN`.
