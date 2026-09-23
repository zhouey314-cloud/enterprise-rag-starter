import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from rag import load,retrieve,answer
chunks=load();cases=[json.loads(x) for x in Path('evals/golden.jsonl').read_text().splitlines() if x.strip()]
fail=[]
for c in cases:
    top=retrieve(c['question'],chunks,c.get('scope','public'),1)
    got=top[0]['chunk'].doc_id if top else None
    result=answer(c['question'],chunks,c.get('scope','public'))
    if got!=c['expected_doc'] or (result['status']=='NO_ANSWER')!=(got is None):fail.append(c['id'])
print(json.dumps({'retrieval_cases':len(cases),'failures':fail,'answer_model_eval':'NOT_RUN','provenance':'synthetic_unverified'}))
if fail:raise SystemExit(1)
