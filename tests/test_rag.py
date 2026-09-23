import unittest
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
if __name__=='__main__':unittest.main()
