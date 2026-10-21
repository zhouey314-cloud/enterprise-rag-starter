# Reproducible local file/identity service

This is a loopback reference with deterministic extractive answers, not production IAM or a verified enterprise policy assistant. No model, embedding, API key, remote ingestion, OCR or paid service runs. Use only material you own or may process; this walkthrough generates MIT-licensed fictional examples. The existing public static demo has illustrative scope selection and is a different interface.

## Fresh environment and import

From a fresh checkout on macOS with Python 3.10+ (CI uses 3.11), run these commands. FTS5 must be included in SQLite; an unavailable extension fails explicitly. The one PDF dependency is pinned in `requirements-local.txt`. Do not reuse a production database or an original project runtime.

```bash
umask 077
mkdir -p .rag-data
python3 -m venv .rag-data/venv
RAG_PY=.rag-data/venv/bin/python
"$RAG_PY" -m pip install -r requirements-local.txt
"$RAG_PY" local_service.py init
"$RAG_PY" scripts/create_local_demo.py --out .rag-data/demo
"$RAG_PY" local_service.py issue-identity --subject demo-viewer --tenant alpha --role viewer --token-file .rag-data/viewer.token
"$RAG_PY" local_service.py issue-identity --subject demo-team --tenant alpha --role team --token-file .rag-data/team.token
"$RAG_PY" local_service.py issue-identity --subject demo-beta --tenant beta --role admin --token-file .rag-data/beta.token
"$RAG_PY" local_service.py ingest .rag-data/demo/alpha-support-hours-v1.md --metadata .rag-data/demo/alpha-support-hours-v1.json --rights-attested
"$RAG_PY" local_service.py query 'What are the support hours?' --token-file .rag-data/viewer.token
"$RAG_PY" local_service.py ingest .rag-data/demo/alpha-support-hours-v2.md --metadata .rag-data/demo/alpha-support-hours-v2.json --rights-attested
"$RAG_PY" local_service.py ingest .rag-data/demo/alpha-travel-finance-pages-v1.pdf --metadata .rag-data/demo/alpha-travel-finance-pages-v1.json --rights-attested
"$RAG_PY" local_service.py ingest .rag-data/demo/alpha-people-handbook-v1.docx --metadata .rag-data/demo/alpha-people-handbook-v1.json --rights-attested
"$RAG_PY" local_service.py query 'What are the support hours?' --token-file .rag-data/viewer.token
"$RAG_PY" local_service.py query 'What is the refund processing interval?' --token-file .rag-data/viewer.token
"$RAG_PY" local_service.py query 'What does the onboarding checklist contain?' --token-file .rag-data/team.token
```

The first support answer cites version 1 and `08:00`; the later answer cites version 2 and `10:00`. The PDF answer cites page 2, filename, hash, effective dates and character span. The DOCX answer cites paragraph 1 with `page=null`; no physical Word page is fabricated. Markdown cites line ranges. `manifest.json` records each generated file's SHA-256; verify against returned source hashes. Repeating the exact current import returns `UNCHANGED`. Changed bytes or access metadata require an increased version. The generator refuses existing outputs rather than overwrite them; choose a fresh directory for another run.

## Real HTTP requests with trusted server identities

In terminal A, start the service (foreground):

```bash
.rag-data/venv/bin/python local_service.py serve --port 8767
```

In terminal B, run this client from the same checkout. It reads private token files into request headers without printing them or putting them in command arguments. It sends requests directly to loopback, without environment proxies.

```bash
.rag-data/venv/bin/python - <<'PY'
import http.client, json
from pathlib import Path

def request(token_file, method, route, value=None):
    headers={'Authorization':'Bearer '+Path(token_file).read_text().strip()}
    if value is not None: headers['Content-Type']='application/json'
    connection=http.client.HTTPConnection('127.0.0.1',8767,timeout=5)
    connection.request(method,route,json.dumps(value) if value is not None else None,headers)
    response=connection.getresponse()
    print(response.status,json.loads(response.read()))
    connection.close()

request('.rag-data/viewer.token','POST','/query',{'question':'What are the support hours?'})
request('.rag-data/viewer.token','POST','/query',{'question':'What is the support phone?'})
request('.rag-data/viewer.token','POST','/query',{'question':'What does the onboarding checklist contain?'})
request('.rag-data/team.token','POST','/query',{'question':'What does the onboarding checklist contain?'})
request('.rag-data/beta.token','POST','/query',{'question':'What are the support hours?'})
request('.rag-data/viewer.token','POST','/query',{'question':'onboarding checklist','role':'admin','tenant':'alpha'})
request('.rag-data/viewer.token','GET','/sources/support-hours/2')
request('.rag-data/viewer.token','GET','/sources/support-hours/1')
PY
```

Expected: support hours answer with version 2; phone refuses while retaining a related trace; viewer onboarding refuses; team onboarding answers; beta admin cannot see alpha; attempted role/tenant impersonation returns 400; current source returns 200 and old source returns 404. Query accepts only `question` and optional `top_k` (1–10). User-supplied scope, identity, historical date and query parameters are rejected. A token authenticates a server-stored identity; role names in a JSON request cannot grant access.

While terminal A is running, these trusted operator commands take effect on subsequent requests:

```bash
.rag-data/venv/bin/python local_service.py delete --tenant alpha --doc-id support-hours
.rag-data/venv/bin/python local_service.py revoke-identity demo-team
```

Repeat the client: deleted support evidence is absent from queries and the source route returns 404; the revoked team token returns 401. Keep source files only as your retention policy allows. Database revisions are retained for local history; `delete` is logical removal from retrieval/source access, not secure erasure or a regulatory retention claim. Stop terminal A with Ctrl-C. The ignored `.rag-data` directory contains local database, tokens and generated fixtures: protect it and do not publish it.

## Verification and limits

```bash
.rag-data/venv/bin/python -W error::ResourceWarning -m unittest discover -s tests
node --test tests/web.test.mjs
.rag-data/venv/bin/python evals/run.py
.rag-data/venv/bin/python evals/answerability.py
.rag-data/venv/bin/python evals/local.py --output .rag-data/eval/local-latest.json
```

The local runner evaluates 62 candidate cases with 56 distinct questions: 60 required lexical-contract cases and two semantic-paraphrase capability probes declared before the first baseline. The two probes keep their supported-source expectations and remain failures in all-candidate metrics; they are not relabeled as good refusals. A green process exit means the bounded lexical contract and access/source-integrity gates passed. The user later reported completing review of all 62 cases: [current user-review receipt](reviews/user-review-receipt-20261021.json). It binds that statement to the reviewed feature commit and both candidate/queue SHA-256 hashes. Individual case adjudications were not supplied. The original queue's `needs_human_review` and the automated report's `pending_human_review=62` / human `BLOCKED` fields describe the earlier snapshot and remain unchanged for evidence; current user-reported review completion is recorded separately. Cases retain `synthetic_unverified` source/ground-truth provenance, both semantic misses remain, and overall/production acceptance stays `BLOCKED`. This is not an independently adjudicated Golden Set.

See [the eval contract](../evals/LOCAL_EVAL_SPEC.md) for denominators, risk, baseline and human-review queue. Word-suffix and terminal Chinese question-word normalization improve two observed lexical failures; they are limited heuristics, not general multilingual or semantic understanding. Source titles aid ranking but cannot make a body that lacks evidence answerable. Relevance can still be mistaken for support and an excerpt can omit nuance. Natural-input runtime acceptance, independent expert validation, generative-model quality, semantic/hybrid model evaluation and hosted production deployment acceptance are not established by that review-completion statement.

## Operator trust and bounded inputs

The OS user controlling the database/CLI is the administrator and can provision identities or edit data. This design does not defend against that user, a compromised machine, or a multi-user host with untrusted filesystem access. Token files and newly created DB files use mode 0600; use a private directory. The service binds only IPv4 loopback, validates local Host values, disables content/access logs and supplies no CORS. It has no TLS, distributed IAM, user signup, password login, multi-process ingestion worker or production rate limiter.

Inputs are local regular files, at most 5 MiB; extracted text is at most 2 MiB, 100 PDF pages and 2,000 chunks per document. Unextractable/scanned/encrypted PDFs fail; DOCX external relationships, images and rendered pagination are not fetched or interpreted. Only `word/document.xml` paragraphs are extracted; rendering and OCR are not implemented. Permissions, effective dates (expiry exclusive), latest-version selection and deletion filter before ranking and again on source lookup. A future latest revision conservatively suppresses its predecessor. Conflicts are detected among supported current chunks in the same operator-assigned topic; this cannot discover all semantic contradictions or compensate for incorrect topic metadata. At most 10,000 eligible chunks are queried; the FTS snapshot is rebuilt per request. These choices favor a small inspectable reference over enterprise scale.
