"""Shared synthetic excerpt regressions; exact source agreement, not semantic quality."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rag import chunk_document, explain

DATASET = Path(__file__).with_name('excerpts.jsonl')


def evaluate():
    cases = [json.loads(line) for line in DATASET.read_text().splitlines() if line.strip()]
    if len(cases) < 21 or len({case['id'] for case in cases}) != len(cases):
        raise ValueError('Missing excerpt regressions or duplicate case IDs')
    if any(case['provenance'] != 'synthetic_unverified' for case in cases):
        raise ValueError('Excerpt provenance must not be silently promoted')
    rows = []
    for case in cases:
        doc = case['document']
        scope = case.get('scope', 'public')
        result = explain(case['question'], chunk_document(doc), scope)
        citations = result['citations']
        access_ok = all(hit['access'] in {'public', scope} for hit in result['retrieved_chunks'])
        if case['expected_status'] == 'NO_ANSWER':
            answer_ok = result['status'] == 'NO_ANSWER' and not citations
        else:
            answer_ok = (result['status'] == 'EXTRACTIVE' and result['answer'] == case['expected_answer']
                         and len(citations) == 1 and citations[0]['doc_id'] == doc['id']
                         and citations[0]['chunk_id'] == f"{doc['id']}:0"
                         and citations[0]['version'] == doc['version'] and result['answer'] in doc['text'])
        rows.append({'id': case['id'], 'pass': answer_ok and access_ok, 'access_pass': access_ok,
                     'failure_type': None if answer_ok and access_ok else 'Workflow', 'result': result})
    return {'provenance': 'synthetic_unverified', 'cases': len(rows), 'passed': sum(row['pass'] for row in rows),
            'access_failures': sum(not row['access_pass'] for row in rows),
            'answer_model_eval': 'NOT_RUN', 'semantic_correctness': 'NOT_TESTED', 'rows': rows}


if __name__ == '__main__':
    report = evaluate()
    print(json.dumps(report, indent=2))
    if any(not row['pass'] for row in report['rows']):
        raise SystemExit(1)
