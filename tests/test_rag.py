import unittest
from unittest.mock import patch
from rag import *
class TestRAG(unittest.TestCase):
    def test_chunk_metadata(self):self.assertEqual(chunk_document({'id':'a','title':'A','text':'one two','version':2})[0].version,2)
    def test_chunk_overlap(self):self.assertEqual(len(chunk_document({'id':'a','title':'A','text':'one two three four five'},3,1)),2)
    def test_bad_chunk(self):self.assertRaises(ValueError,chunk_document,{'id':'a','title':'A','text':'x'},2,2)
    def test_retrieval(self):self.assertEqual(retrieve('support hours',load())[0]['chunk'].doc_id,'support')
    def test_access_filter(self):self.assertFalse(any(x['chunk'].doc_id=='team' for x in retrieve('internal onboarding',load(),'public')))
    def test_team_access(self):self.assertEqual(retrieve('internal onboarding',load(),'team')[0]['chunk'].doc_id,'team')
    def test_no_answer(self):self.assertEqual(answer('lunar engine warranty',load())['status'],'NO_ANSWER')
    def test_citation(self):self.assertEqual(answer('support hours',load())['citations'][0]['doc_id'],'support')
    def test_llm_not_configured(self):self.assertRaises(RuntimeError,LLMProvider().answer,'q',[])
    def test_embedding_not_configured(self):self.assertRaises(RuntimeError,EmbeddingProvider().embed,'q')
    def test_top_k(self):self.assertEqual(len(retrieve_mode('support hours',load(),k=1)),1)
    def test_invalid_top_k(self):self.assertRaises(ValueError,retrieve_mode,'support',load(),'public',0)
    def test_invalid_mode(self):self.assertRaises(ValueError,retrieve_mode,'support',load(),'public',3,'unknown')
    def test_trace_access(self):self.assertTrue(all(h['access']=='public' for h in explain('employee onboarding policy',load())['retrieved_chunks']))
    def test_no_answer_reason(self):self.assertEqual(explain('lunar engine warranty',load())['no_answer_reason'],'NO_ACCESSIBLE_MATCH_ABOVE_THRESHOLD')
    def test_refund_citation(self):self.assertEqual(answer('refund policy',load())['citations'][0]['doc_id'],'returns')
    def test_security_citation(self):self.assertEqual(answer('security policy',load())['citations'][0]['doc_id'],'security')
    def test_team_policy(self):self.assertEqual(answer('employee onboarding policy',load(),'team')['citations'][0]['doc_id'],'team')
    def test_public_employee_no_answer(self):self.assertEqual(answer('employee policy',load(),'public')['status'],'NO_ANSWER')
    def test_support_phone_number_is_unanswerable(self):
        result=answer('What is the support phone number?',load())
        self.assertEqual(result['status'],'NO_ANSWER')
        self.assertEqual(result['citations'],[])
        explained=explain('What is the support phone number?',load())
        self.assertEqual(explained['no_answer_reason'],'QUESTION_NOT_ANSWERABLE_BY_TOP_HIT')
        self.assertTrue(explained['retrieved_chunks'])
    def test_support_phone_short_is_unanswerable(self):
        self.assertEqual(answer('support phone',load())['status'],'NO_ANSWER')
    def test_phone_is_answerable_when_the_source_contains_it(self):
        chunks=chunk_document({'id':'contact','title':'Support contact','text':'The support phone number is 555-0100.'})
        result=answer('What is the support phone number?',chunks)
        self.assertEqual(result['status'],'EXTRACTIVE')
        self.assertIn('555-0100',result['answer'])
        self.assertEqual(result['citations'][0]['doc_id'],'contact')
    def test_lexical_gate_does_not_reject_embedding_paraphrases(self):
        # Routing invariant only; a mocked hit is not a real embedding-model eval.
        support=load()[0]
        for mode in ('semantic','hybrid'):
            with self.subTest(mode=mode),patch('rag.retrieve_mode',return_value=[{'chunk':support,'score':0.9}]):
                self.assertEqual(answer('When can I reach customer service?',[support],mode=mode)['status'],'EXTRACTIVE')
if __name__=='__main__':unittest.main()
