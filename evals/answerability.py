"""Separate offline retrieval and extractive-answer checks on synthetic cases."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rag import explain, load


def evaluate():
    cases = [json.loads(line) for line in Path('evals/answerability.jsonl').read_text().splitlines() if line.strip()]
    chunks = load()
    rows = []
    for case in cases:
        result = explain(case['question'], chunks, case.get('scope', 'public'), k=1)
        retrieved = result['retrieved_chunks']
        got = retrieved[0]['doc_id'] if retrieved else None
        citations = result['citations']
        citation_ok = (not citations if case['expected_status'] == 'NO_ANSWER' else
                       len(citations) == 1 and citations[0]['doc_id'] == case['expected_doc'])
        access_ok = all(hit['access'] in {'public', case.get('scope', 'public')} for hit in retrieved)
        rows.append({
            'id': case['id'], 'retrieval_pass': got == case['expected_doc'],
            'answer_pass': result['status'] == case['expected_status'] and citation_ok and
                           case.get('answer_contains', '') in result['answer'],
            'access_pass': access_ok, 'expected_doc': case['expected_doc'],
            'result': result,
        })
    positives = [row for row in rows if row['expected_doc'] is not None]
    return {
        'provenance': 'synthetic_unverified', 'mode': 'lexical', 'cases': len(rows),
        'retrieval': {'recall_at_1': sum(row['retrieval_pass'] for row in positives) / len(positives),
                      'answerable_and_related_denominator': len(positives),
                      'all_case_passed': sum(row['retrieval_pass'] for row in rows)},
        'extractive_answer': {'passed': sum(row['answer_pass'] for row in rows), 'total': len(rows)},
        'access_failures': sum(not row['access_pass'] for row in rows),
        'answer_model_eval': 'NOT_RUN', 'human_semantic_review': 'NOT_RUN', 'rows': rows,
    }


if __name__ == '__main__':
    report = evaluate()
    print(json.dumps(report, indent=2))
    if any(not row['retrieval_pass'] or not row['answer_pass'] or not row['access_pass'] for row in report['rows']):
        raise SystemExit(1)
