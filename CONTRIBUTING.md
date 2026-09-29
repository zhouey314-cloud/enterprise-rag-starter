# Contributing

Small, reproducible fixes are welcome. Open an Issue for behavior changes so the expected answer and evaluation boundary can be agreed first.

1. Use Python 3.10+ and run `python3 -m unittest discover -s tests -v` and `python3 evals/run.py` from the repository root. These are deterministic mechanics/synthetic fixture checks, not model-quality evidence.
2. For optional semantic/hybrid work, install `requirements-semantic.txt`, cache `sentence-transformers/all-MiniLM-L6-v2`, then run `HF_HOME="$PWD/.model-cache" HF_HUB_OFFLINE=1 .venv/bin/python evals/modes.py`. If the model is unavailable, report `BLOCKED`, not a pass. Dependencies are ranges, not a frozen lockfile.
3. A PR that changes retrieval or answer behavior needs baseline results, new and regression cases with independently reviewed expected outcomes, failure analysis, and separate retrieval/answer-quality reporting. Start with [the known false answer](FAILURE_ANALYSIS.md).
4. Keep examples fictional and mark self-authored fixtures `synthetic_unverified`. Do not add real enterprise documents, private data, credentials, or claims of production ACL or LLM quality.
5. Update `CHANGELOG.md` for user-visible behavior and `ROADMAP.md` only when a status really changes.

The [release checklist](docs/releases/RELEASE_CHECKLIST.md) records gates; the historical version conflict and publication need separate maintainer decisions.
