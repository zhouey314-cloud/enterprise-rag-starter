"""Candidate-fixture agreement, not semantic quality or a human-approved Golden Set."""
import argparse
from datetime import date, datetime, timezone
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import platform
import sqlite3
import subprocess
import sys
import tempfile
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from local_fixtures import ROOT, load_corpus, materialize
from localrag import KnowledgeStore, Metadata, ROLES

IDENTITIES={'alpha-viewer':('alpha','viewer'),'alpha-team':('alpha','team'),'alpha-admin':('alpha','admin'),'beta-admin':('beta','admin')}


def load_cases(path=ROOT/'evals/local-candidates.jsonl', queue=ROOT/'evals/local-human-review.jsonl'):
    cases=[json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]
    review=[json.loads(line) for line in Path(queue).read_text().splitlines() if line.strip()]
    if len(cases)<50 or len({c['id'] for c in cases})!=len(cases) or len({c['question'] for c in cases})<50:
        raise ValueError('AT_LEAST_50_DISTINCT_QUESTIONS_REQUIRED')
    if len({c['question'] for c in cases if c['required_for_lexical_release']})<50:
        raise ValueError('AT_LEAST_50_DISTINCT_REQUIRED_QUESTIONS_REQUIRED')
    if {c['id'] for c in cases}!={r['case_id'] for r in review} or len(review)!=len(cases):raise ValueError('REVIEW_QUEUE_MISMATCH')
    for row in review:
        if row['state']!='needs_human_review' or row['reviewer'] is not None or row['decision'] is not None:raise ValueError('HUMAN_REVIEW_NOT_ATTESTED_BY_THIS_RUNNER')
    for case in cases:
        if case['identity'] not in IDENTITIES or case['provenance']['status']!='synthetic_unverified' or case['provenance']['human_review']!='needs_human_review':raise ValueError('INVALID_PROVENANCE_OR_IDENTITY')
        if type(case['required_for_lexical_release']) is not bool or case['expected']['status'] not in {'EXTRACTIVE','NO_ANSWER'}:raise ValueError('INVALID_CASE_CONTRACT')
        if not case['required_for_lexical_release'] and case.get('capability')!='semantic_paraphrase':raise ValueError('UNDECLARED_OPTIONAL_CAPABILITY')
    return cases,review


def fraction(n,d):return {'numerator':n,'denominator':d,'value':round(n/d,6) if d else None}
def percentile(values,p):return sorted(values)[max(0,math.ceil(len(values)*p)-1)] if values else None

def score(rows):
    positive=[r for r in rows if r['expected']['status']=='EXTRACTIVE']
    negative=[r for r in rows if r['expected']['status']=='NO_ANSWER']
    refusals=[r for r in rows if r['result']['status']=='NO_ANSWER']
    true_refusal=sum(r['expected']['status']=='NO_ANSWER' for r in refusals)
    citations=[r for r in rows if r['result']['citations']]
    return {'cases':len(rows),
      'retrieval':{'recall_at_1':fraction(sum(r['retrieval_at_1'] for r in positive),len(positive)),'recall_at_3':fraction(sum(r['retrieval_at_3'] for r in positive),len(positive))},
      'answer':{'literal_fixture_agreement':fraction(sum(r['answer_literal_agreement'] for r in positive),len(positive)),'semantic_correctness':'NOT_TESTED','completeness':'NOT_TESTED'},
      'citation':{'source_integrity':fraction(sum(r['citation_integrity'] for r in citations),len(citations)),'expected_doc_version_locator_agreement':fraction(sum(r['citation_expected'] for r in positive),len(positive))},
      'refusal':{'precision':fraction(true_refusal,len(refusals)),'recall':fraction(true_refusal,len(negative))},
      'latency_ms':{'samples':len(rows),'p50':percentile([r['wall_latency_ms'] for r in rows],.5),'p95':percentile([r['wall_latency_ms'] for r in rows],.95),'method':'nearest-rank; local core call includes auth/SQLite/parsing-free retrieval, excludes import/HTTP/network/model'},
      'fixture_contract':fraction(sum(r['case_contract'] for r in rows),len(rows))}


def evaluate():
    cases,review=load_cases();corpus=load_corpus();rows=[]
    with tempfile.TemporaryDirectory(prefix='rag-candidate-') as directory:
        root=Path(directory);manifest=materialize(root/'fixtures',corpus['documents']);store=KnowledgeStore(root/'index.sqlite3')
        tokens={name:store.issue_identity(name,*identity) for name,identity in IDENTITIES.items()}
        current={}
        for source,entry in zip(corpus['documents'],manifest):
            meta=Metadata(**source['metadata']);store.ingest(root/'fixtures'/entry['file'],meta,rights_attested=True)
            if source.get('delete_after_import'):store.delete(meta.tenant,meta.doc_id)
            current[(meta.tenant,meta.doc_id)]={**meta.__dict__,'deleted':source.get('delete_after_import',False),'sha256':entry['sha256']}
        today=date.today().isoformat()
        for case in cases:
            expected=case['expected'];token=tokens[case['identity']];tenant,role=IDENTITIES[case['identity']]
            allowed={(m['doc_id'],m['version']):m for m in current.values() if m['tenant']==tenant and ROLES[role]>=ROLES[m['min_role']] and not m['deleted'] and m['effective_on']<=today and (not m['expires_on'] or m['expires_on']>today)}
            start=time.perf_counter();result=store.query(token,case['question'],case['top_k']);elapsed=round((time.perf_counter()-start)*1000,3)
            expected_key=(expected['doc_id'],expected['version'])
            trace_keys=[(c['doc_id'],c['version']) for c in result['retrieved']]
            returned=result['retrieved']+result['citations']
            access_ok=all((c['doc_id'],c['version']) in allowed for c in returned)
            access_ok &= all(c['doc_id'] not in case.get('forbidden_docs',[]) and [c['doc_id'],c['version']] not in case.get('forbidden_versions',[]) for c in returned)
            integrity=True
            for citation in result['citations']:
                meta=allowed.get((citation['doc_id'],citation['version']))
                try:source=store.source(token,citation['doc_id'],citation['version'])['source']
                except LookupError:source=[]
                integrity &= bool(meta and citation['sha256']==meta['sha256'] and citation in source and citation['text']==result['answer'])
            if result['status']=='NO_ANSWER':integrity &= not result['citations'] and result['answer'] is None
            expected_citation=bool(result['citations']) and all(c['doc_id']==expected['doc_id'] and c['version']==expected['version'] and c['page']==expected['page'] and (not expected.get('locator_prefix') or c['locator'].startswith(expected['locator_prefix'])) for c in result['citations'])
            literal=expected['literal']==result['answer'] if expected['status']=='EXTRACTIVE' else result['answer'] is None
            contract=result['status']==expected['status'] and literal and access_ok and integrity and len(result['retrieved'])<=case['top_k']
            contract &= expected_citation if expected['status']=='EXTRACTIVE' else result['refusal_reason']==expected['refusal_reason']
            recall1=expected_key in trace_keys[:1];recall3=expected_key in trace_keys[:3]
            errors=[]
            if not access_ok:errors.append('Business Rule: access/version/date/deletion leak')
            if not integrity or (result['citations'] and not expected_citation):errors.append('Citation: source or expected locator disagreement')
            if expected['status']=='EXTRACTIVE' and not recall3:errors.append('Retrieval: expected source absent from top-3')
            if result['status']!=expected['status'] or not literal:errors.append('Answerability: status or literal candidate disagreement')
            rows.append({'id':case['id'],'question':case['question'],'identity':case['identity'],'provenance':'synthetic_unverified','required_for_lexical_release':case['required_for_lexical_release'],'expected':expected,'result':result,'wall_latency_ms':elapsed,'access_pass':access_ok,'citation_integrity':integrity,'citation_expected':expected_citation,'retrieval_at_1':recall1,'retrieval_at_3':recall3,'answer_literal_agreement':literal,'case_contract':bool(contract),'errors':errors})
    required=[r for r in rows if r['required_for_lexical_release']]
    required_failures=[r['id'] for r in required if not r['case_contract']]
    access_failures=[r['id'] for r in rows if not r['access_pass']]
    integrity_failures=[r['id'] for r in rows if not r['citation_integrity']]
    try:
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True,stderr=subprocess.DEVNULL).strip()
        dirty=bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True,stderr=subprocess.DEVNULL).strip())
    except (OSError,subprocess.CalledProcessError):revision=None;dirty=None
    paths=['localrag.py','local_ingest.py','local_fixtures.py','evals/local.py','evals/local-corpus.json','evals/local-candidates.jsonl','evals/local-human-review.jsonl']
    source_hashes={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}
    mechanical=not(required_failures or access_failures or integrity_failures)
    return {'schema_version':1,'created_at':datetime.now(timezone.utc).isoformat(),'provenance':'synthetic_unverified','provider':'deterministic_extract','model_calls':0,'embedding_calls':0,'selected_size':len(rows),'distinct_questions':len({c['question'] for c in cases}),'pending_human_review':len(review),'source_revision':revision,'worktree_dirty':dirty,'source_hashes':source_hashes,'environment':{'python':platform.python_version(),'sqlite':sqlite3.sqlite_version,'pypdf':importlib.metadata.version('pypdf')},'all_candidates':score(rows),'required_lexical_candidates':score(required),'semantic_probe_failures':[r['id'] for r in rows if not r['required_for_lexical_release'] and not r['case_contract']],'gates':{'mechanical_candidate_contract':'PASS' if mechanical else 'FAIL','required_failures':required_failures,'access_failures':access_failures,'citation_integrity_failures':integrity_failures,'human_semantic_review':'BLOCKED','provider_semantic_eval':'NOT_TESTED','commercial_or_production_acceptance':'BLOCKED'},'overall':'BLOCKED','rows':rows}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',default='.rag-data/eval/local-latest.json');args=parser.parse_args()
    report=evaluate();path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True,mode=0o700);path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('selected_size','pending_human_review','all_candidates','required_lexical_candidates','semantic_probe_failures','gates','overall')},ensure_ascii=False,indent=2))
    return 0 if report['gates']['mechanical_candidate_contract']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
