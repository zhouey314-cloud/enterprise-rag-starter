# Failure analysis

Observed on 2026-09-29 from current `main` with the fictional corpus:

```bash
python3 rag.py 'What is the support phone number?'
```

The lexical path returned `status=EXTRACTIVE`, cited `support:0`, and answered with the fictional support **hours** sentence. That chunk contains no phone number. The citation is structurally valid, but the answer does not address the question. No LLM ran. The initial repair checked coverage of question terms in the top hit title and text; insufficient coverage returned `NO_ANSWER` without a citation and exposes `QUESTION_NOT_ANSWERABLE_BY_TOP_HIT` in the trace. That initial rule also ran in the static browser demo. The sentence-local repair below supersedes its title/whole-chunk evidence gate. The expected outcome is encoded in `tests/test_rag.py::test_support_phone_number_is_unanswerable`.

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

## 2026-10-23 second/later-sentence repair

Baseline source: `45e2daa8fa7cbd4092c08219a68b16ca02148d50`. Reproduction: public `contact` document titled “Support contact” with `Our office has a garden. The support phone number is 555-0100.` and question `What is the support phone number?`. Both Python and JavaScript returned the garden sentence with `contact:0`. Retrieval found the correct document; the Workflow failure was answer selection/validation, not a missing document.

Before editing behavior, the existing suite passed 48 Python tests, 10 Node tests, four original lexical and nine answerability fixtures. The new ten-case shared excerpt set passed only 2/10 on unchanged source. [Raw baseline](evals/baselines/20261023-excerpts-45e2daa8.json) preserves all outputs and the dataset hash. The eight failing IDs were `second_sentence`, `later_sentence`, `prefer_more_complete_sentence`, `title_is_not_answer_evidence`, `no_supporting_sentence`, `team_allowed_later_sentence`, `clock_range_supports_hours`, and `unrelated_clock_does_not_lend_evidence`.

The repair scores each candidate sentence using its own body evidence, chooses the greatest coverage (source order breaks ties), and returns only a qualifying exact source sentence. Neither title nor another sentence can supply missing terms. The 0.6 threshold is unchanged. A clock-range lexical cue preserves the old support-hours source, whose body says `09:00 to 17:00` without the word “hours”; an unrelated train timetable in another sentence cannot support the support-hours query. No phone value is hardcoded in implementation. No qualifying sentence means refusal/no citation with retrieval trace retained.

After repair: 49 Python tests and 20 Node tests pass; all ten excerpt cases pass (eight improved, two unchanged; zero new failures). The original four/nine fixture gates remain unchanged and passing. Local file/identity evaluation remains 60/60 required and 60/62 all-candidate contracts; `semantic-paraphrase-support` and `semantic-paraphrase-refund` remain visible failures. Access/citation integrity failures remain zero. Patch mechanical gate: PASS. Production acceptance: BLOCKED; generative quality NOT_RUN, semantics NOT_TESTED. User-reported review of all 62 local cases is preserved by the existing receipt; provenance remains synthetic_unverified, and no per-case verdicts are invented.

Reproduce from a clean Python environment with `requirements-local.txt` installed:

```bash
python -m unittest discover -s tests -v
python evals/run.py
python evals/answerability.py
python evals/excerpts.py
python evals/local.py --output .rag-data/eval/local-latest.json
node --test tests/web.test.mjs
```

No semantic model was downloaded or executed during this repair. The optional semantic/hybrid first-sentence path remains unchanged and needs its own calibrated answerability work. Sentence token coverage and simple punctuation splitting do not establish entailment, multi-sentence completeness or enterprise quality.
