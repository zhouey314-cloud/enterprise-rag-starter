"""Fail-closed candidate harness checks, including deliberate citation corruption."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from local_fixtures import load_corpus, materialize
from local_ingest import parse_file
from localrag import KnowledgeStore

spec=importlib.util.spec_from_file_location('local_candidate_eval',Path(__file__).resolve().parents[1]/'evals/local.py')
local_eval=importlib.util.module_from_spec(spec);spec.loader.exec_module(local_eval)


class CandidateHarnessTests(unittest.TestCase):
    def test_empty_or_duplicate_case_ids_cannot_turn_green(self):
        cases,review=local_eval.load_cases()
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'cases.jsonl';queue=Path(directory)/'review.jsonl'
            path.write_text('');queue.write_text('')
            with self.assertRaises(ValueError):local_eval.load_cases(path,queue)
            cases[1]['id']=cases[0]['id']
            path.write_text(''.join(json.dumps(c)+'\n' for c in cases));queue.write_text(''.join(json.dumps(c)+'\n' for c in review))
            with self.assertRaises(ValueError):local_eval.load_cases(path,queue)

    def test_fixture_formats_have_real_page_or_paragraph_provenance(self):
        docs=[d for d in load_corpus()['documents'] if d['format'] in {'pdf','docx'}]
        with tempfile.TemporaryDirectory() as directory:
            manifest=materialize(directory,docs)
            for doc,item in zip(docs,manifest):
                passages=parse_file(Path(directory)/item['file'])
                self.assertEqual([p.text for p in passages],doc['passages'])
                if doc['format']=='pdf':self.assertEqual([p.page for p in passages],[1,2,3,4])
                else:
                    self.assertTrue(all(p.page is None for p in passages))
                    self.assertTrue(passages[3].locator.startswith('paragraph:4;'))
            with self.assertRaises(ValueError):materialize(directory,docs)

    def test_corrupted_citation_fails_gate_and_cannot_attest_human_review(self):
        original=KnowledgeStore.query
        def corrupted(store,*args,**kwargs):
            result=original(store,*args,**kwargs)
            if result['citations']:result['citations'][0]['sha256']='0'*64
            return result
        with patch.object(KnowledgeStore,'query',corrupted):report=local_eval.evaluate()
        self.assertEqual(report['gates']['mechanical_candidate_contract'],'FAIL')
        self.assertTrue(report['gates']['citation_integrity_failures'])
        self.assertEqual(report['gates']['human_semantic_review'],'BLOCKED')
        self.assertEqual(report['overall'],'BLOCKED')
