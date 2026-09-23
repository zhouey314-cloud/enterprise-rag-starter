# Project-specific eval contract

Goal: answer synthetic enterprise-policy questions with an exact source sentence and citation, or refuse when no accessible evidence is retrieved. Users can inspect top-K scores and access scope. All fixtures are `synthetic_unverified`; there is no real enterprise policy, no generation model, and no claim of production security.

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
