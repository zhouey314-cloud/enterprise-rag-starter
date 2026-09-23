"""Synthetic retrieval/evidence gates for lexical, local semantic and hybrid."""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from rag import answer, load, retrieve_mode, semantic_adapter

cases=[
    ('support hours','public','support'),
    ('refund policy','public','returns'),
    ('security policy','public','security'),
    ('employee onboarding policy','team','team'),
    ('lunar engine warranty','public',None),
]
paraphrases=[
    ('When can I reach customer service?','public','support'),
    ('How long do I have to ask for my money back?','public','returns'),
    ('What protects client data?','public','security'),
]
chunks=load()
adapter=semantic_adapter()
report={}
critical=[]
for mode in ('lexical','semantic','hybrid'):
    selected=cases+(paraphrases if mode!='lexical' else [])
    outcomes=[]
    for question,scope,expected in selected:
        hits=retrieve_mode(question,chunks,scope,1,mode,adapter)
        got=hits[0]['chunk'].doc_id if hits else None
        result=answer(question,chunks,scope,mode,1,adapter)
        citation=result['citations'][0]['doc_id'] if result['citations'] else None
        accessible=all(h['chunk'].access in ('public',scope) for h in hits)
        passed=(got==expected and citation==got and accessible and (result['status']=='NO_ANSWER')==(got is None))
        outcomes.append({'question':question,'scope':scope,'expected_doc':expected,'retrieved_doc':got,'citation_doc':citation,'pass':passed})
        if not passed:critical.append(f'{mode}:{question}')
    report[mode]={'recall_at_1':sum(x['retrieved_doc']==x['expected_doc'] for x in outcomes)/len(outcomes),'cases':len(outcomes),'passed':sum(x['pass'] for x in outcomes),'outcomes':outcomes}
    public=retrieve_mode('employee onboarding policy',chunks,'public',4,mode,adapter)
    if any(h['chunk'].doc_id=='team' for h in public):critical.append(f'{mode}:ACL_LEAKAGE')
    if len(public)>4:critical.append(f'{mode}:TOP_K')
print(json.dumps({'provenance':'synthetic_unverified','answer_model_eval':'NOT_RUN','modes':report,'critical_failures':critical},indent=2))
if critical:raise SystemExit(1)
