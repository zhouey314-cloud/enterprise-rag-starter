# Project-specific eval contract

Goal: answer synthetic enterprise-policy questions with an exact source sentence and citation, or refuse when no accessible source sentence meets the lexical evidence gate. Users can inspect top-K scores and access scope. All fixtures are `synthetic_unverified`; there is no real enterprise policy, no generation model, and no claim of production security.

## Baseline before V3 change

10 Python tests passed; 4/4 synthetic lexical retrieval cases passed; answer-model eval `NOT_RUN`. The original project had only lexical retrieval and placeholder embedding/vector interfaces.

## Required gates

- Retrieval Recall@1: expected document at rank 1 on the synthetic set, reported separately for lexical/semantic/hybrid.
- Citation correctness: cited document and chunk must be the selected accessible top hit; no citation on no-answer.
- No-answer: nonexistent lunar-engine warranty must return NO_ANSWER.
- ACL leakage: `team` document must not appear for public scope at any top-K.
- Top-K: returned accessible chunks never exceed requested count.
- Critical failures: inaccessible chunk in results or citation; invented answer; silent semantic fallback to lexical.

Semantic mode is optional locally and requires a real SentenceTransformer model. If model download or dependency fails, report `BLOCKED`, not PASS. The public static web demo is lexical only; do not label its output semantic. The corpus and labels are self-authored and not expert-verified.

Known failure modes: lexical exact-token matching misses paraphrases; embedding similarity may retrieve merely related but non-answering text; substring/sentence extraction can omit nuance; no production authentication. Human review needed before real enterprise use.

## Lexical answerability regression contract

`python3 evals/answerability.py` evaluates `answerability.jsonl` with separate retrieval and extractive-answer results. A related support document is the expected retrieval for an unsupported phone/email query; retrieving it is a retrieval success, while answering with its hours is an answer failure. A refusal must have no citation and retain the retrieval trace. Supported hours, refunds, public-scope denial and team-scope access must stay correct. `node --test tests/web.test.mjs` uses the same dataset for the static demo. Labels are `synthetic_unverified`, derived from the fictional corpus and the reported user regression, and are not a human-approved enterprise Golden Set.

The existing gate is zero failures on these nine lexical cases and no regressions in the original four fixtures. The 0.6 token-coverage threshold is provisional and only applies to lexical mode. These checks measure exact status/citation/source-substring constraints, not semantic correctness or real-user quality. Semantic/hybrid retain their prior behavior and require a separate real-model eval; unavailable dependencies must remain BLOCKED.

## 2026-10-23 excerpt selection repair

The affected journey is the Python/static-web lexical path returning an exact relevant sentence from an accessible top hit. The high-risk failures are a wrong sentence with a valid-looking citation, title-only evidence, inaccessible evidence, or weakening an existing refusal. Optional model extraction and `localrag` are separate paths; no model behavior is claimed verified here.

`excerpts.jsonl` adds ten shared `synthetic_unverified` regressions with exact source-substring expectations and provenance. `python3 evals/excerpts.py` records raw results, exact answer/citation/version agreement, access failures and case failures. Python unit tests and Node tests both consume the same cases. Expected answers were derived from the reported synthetic defect and fixture text; they are not independent semantic ground truth. The original nine cases, four lexical fixtures, and 62 local candidates are unchanged.

Baseline `45e2daa8` passes 48 Python tests, 10 Node tests, the original four/nine fixture sets, and 60/60 required local cases. On the new excerpt cases it passes 2/10; the other eight fail under the unchanged source, classified as Workflow (whole-chunk/title gate followed by first-sentence extraction). The [preserved raw baseline](baselines/20261023-excerpts-45e2daa8.json) binds the added dataset hash to that source SHA. The repair passes 10/10, all 49 Python and 20 Node checks, with zero regressions in the previous gates. Two local semantic probes remain failures, with their original expectations retained.

Patch release gate: zero excerpt/status/citation/access failures and no regressions in old lexical, refusal or local-library contracts. The provisional 0.6 gate now applies to actual sentence evidence; explicit clock ranges add the “hours” lexical cue in that sentence to preserve existing source wording. This is not semantic entailment, a generic multi-sentence reasoning method, or proof of completeness. Optional semantic/hybrid model execution is NOT_RUN for this repair; generative quality is NOT_RUN. The local user's reported 62-case review and synthetic provenance remain as documented in LOCAL_EVAL_SPEC.md. Latency and cost are not used as patch acceptance claims; no paid API runs.

## Independent-review typed-value hardening — 2026-10-24

The intermediate `372a137a` repair still answered an archived “support phone” directory (2/3 coverage), and a sentence saying “The support phone number changes quarterly” could tie with the following actual number. These are in-scope Workflow/answer-support failures, not a successful completed fix. Seven additional synthetic cases preserve both failures plus missing-email, positive email/different-phone and date-not-phone boundaries. The expanded 17-case set passed 11/17 before hardening; [raw intermediate baseline](baselines/20261024-excerpts-372a137a.json) records every result and the new dataset hash.

The final sentence gate retains the 0.6 floor, requires every question content term in that sentence, and requires typed syntactic evidence for phone/email/number requests. The grammatical “many” in “how many” is exempt only from content completeness; original coverage still includes it. Phone patterns require 7–15 digits and exclude ISO dates, email patterns require an address, and number questions require a digit. These conservative checks reject unsupported references without hardcoding fixture values. They do not prove semantic entailment or implement a complete contact-format/intent parser; unsupported formats may refuse.

Final mechanical gate: 17/17 excerpts, 49 Python tests, 27 Node tests, original 4/4 retrieval and 9/9 answerability, and local 60/60 required contracts. Compared with the intermediate baseline: six improved, eleven unchanged, zero regressed/new failures; the two unrelated local semantic probes still fail. No expected answer or provenance was changed, and neither optional semantic/hybrid nor generative models ran.
