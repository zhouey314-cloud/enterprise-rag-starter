"""Offline lexical RAG baseline with real citations and conservative no-answer."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json
import re
from functools import lru_cache

def words(text:str)->list[str]:return re.findall(r'[a-z0-9]+',text.lower())
@dataclass(frozen=True)
class Chunk:
    id:str;doc_id:str;title:str;text:str;access:str;version:int

def chunk_document(doc:dict,max_words:int=70,overlap:int=10)->list[Chunk]:
    if max_words<=overlap or overlap<0:raise ValueError('invalid chunk size')
    raw=doc['text'].split();out=[];step=max_words-overlap
    for i,start in enumerate(range(0,len(raw),step)):
        part=raw[start:start+max_words]
        if not part:break
        out.append(Chunk(f"{doc['id']}:{i}",doc['id'],doc['title'],' '.join(part),doc.get('access','public'),doc.get('version',1)))
        if start+max_words>=len(raw):break
    return out

class EmbeddingProvider:
    def embed(self,text:str):raise RuntimeError('NOT_CONFIGURED')
class LLMProvider:
    def answer(self,question:str,context:list[Chunk]):raise RuntimeError('NOT_CONFIGURED')
class VectorStore:
    def search(self,vector,scope:str):raise RuntimeError('NOT_CONFIGURED')

MODEL_ID='sentence-transformers/all-MiniLM-L6-v2'
class SentenceTransformerAdapter(EmbeddingProvider):
    """Optional local semantic adapter. Install requirements-semantic.txt first."""
    def __init__(self, model_id:str=MODEL_ID):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError('SEMANTIC_DEPENDENCY_MISSING') from exc
        self.model=SentenceTransformer(model_id)
        self.model_id=model_id
        self._cache={}
    def embed(self,text:str):
        if text not in self._cache:self._cache[text]=self.model.encode(text,normalize_embeddings=True)
        return self._cache[text]

@lru_cache(maxsize=1)
def semantic_adapter()->SentenceTransformerAdapter:
    return SentenceTransformerAdapter()

def allowed(chunks:list[Chunk],scope:str)->list[Chunk]:
    return [c for c in chunks if c.access in {'public',scope}]

def retrieve(query:str,chunks:list[Chunk],scope:str='public',k:int=3)->list[dict]:
    terms=set(words(query))-{ 'what','is','the','a','an','for','to','how','does','in','of','our','are','policy' }
    scored=[]
    for c in allowed(chunks,scope):
        body=set(words(c.text));title=set(words(c.title))
        score=len(terms&body)+2*len(terms&title)
        if score>0:scored.append({'chunk':c,'score':score})
    return sorted(scored,key=lambda x:(-x['score'],x['chunk'].id))[:k]

def retrieve_semantic(query:str,chunks:list[Chunk],scope:str='public',k:int=3,adapter:EmbeddingProvider|None=None,min_score:float=0.30)->list[dict]:
    if k<1:raise ValueError('INVALID_TOP_K')
    candidates=allowed(chunks,scope)
    if not candidates:return []
    model=adapter or semantic_adapter()
    import numpy as np
    q=np.asarray(model.embed(query),dtype=float)
    hits=[]
    for c in candidates:
        vector=np.asarray(model.embed(f'{c.title}. {c.text}'),dtype=float)
        denominator=float(np.linalg.norm(q)*np.linalg.norm(vector))
        score=float(np.dot(q,vector)/denominator) if denominator else 0.0
        if score>=min_score:hits.append({'chunk':c,'score':round(score,6)})
    return sorted(hits,key=lambda x:(-x['score'],x['chunk'].id))[:k]

def retrieve_hybrid(query:str,chunks:list[Chunk],scope:str='public',k:int=3,adapter:EmbeddingProvider|None=None)->list[dict]:
    if k<1:raise ValueError('INVALID_TOP_K')
    limit=len(allowed(chunks,scope))
    lexical=retrieve(query,chunks,scope,limit)
    semantic=retrieve_semantic(query,chunks,scope,limit,adapter)
    scores={}
    for results,weight in ((lexical,1),(semantic,2)):
        for rank,item in enumerate(results):
            c=item['chunk']
            scores.setdefault(c.id,{'chunk':c,'score':0.0})['score']+=weight/(60+rank+1)
    return sorted(scores.values(),key=lambda x:(-x['score'],x['chunk'].id))[:k]

def retrieve_mode(query:str,chunks:list[Chunk],scope:str='public',k:int=3,mode:str='lexical',adapter:EmbeddingProvider|None=None)->list[dict]:
    if k<1:raise ValueError('INVALID_TOP_K')
    if mode=='lexical':return retrieve(query,chunks,scope,k)
    if mode=='semantic':return retrieve_semantic(query,chunks,scope,k,adapter)
    if mode=='hybrid':return retrieve_hybrid(query,chunks,scope,k,adapter)
    raise ValueError('INVALID_MODE')

def rerank(results:list[dict])->list[dict]:return sorted(results,key=lambda x:(-x['score'],x['chunk'].id))

def answer(question:str,chunks:list[Chunk],scope:str='public',mode:str='lexical',k:int=3,adapter:EmbeddingProvider|None=None)->dict:
    hits=retrieve_mode(question,chunks,scope,k,mode,adapter)
    if not hits:return {'answer':'I do not have enough evidence in the available documents.','citations':[],'status':'NO_ANSWER','provider':f'offline_{mode}'}
    best=hits[0]['chunk']
    sentence=re.split(r'(?<=[.!?])\s+',best.text)[0]
    return {'answer':sentence,'citations':[{'doc_id':best.doc_id,'chunk_id':best.id,'title':best.title,'version':best.version}],'status':'EXTRACTIVE','provider':f'offline_{mode}'}

def explain(question:str,chunks:list[Chunk],scope:str='public',mode:str='lexical',k:int=3,adapter:EmbeddingProvider|None=None)->dict:
    hits=retrieve_mode(question,chunks,scope,k,mode,adapter)
    result=answer(question,chunks,scope,mode,k,adapter)
    return {**result,'mode':mode,'scope':scope,'top_k':k,'no_answer_reason':'NO_ACCESSIBLE_MATCH_ABOVE_THRESHOLD' if not hits else None,
            'retrieved_chunks':[{'chunk_id':x['chunk'].id,'doc_id':x['chunk'].doc_id,'title':x['chunk'].title,'text':x['chunk'].text,'score':x['score'],'access':x['chunk'].access,'version':x['chunk'].version} for x in hits]}

def load()->list[Chunk]:return [c for doc in json.loads(Path('data/documents.json').read_text()) for c in chunk_document(doc)]
def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('question');p.add_argument('--scope',default='public');p.add_argument('--mode',choices=['lexical','semantic','hybrid'],default='lexical');p.add_argument('--top-k',type=int,default=3);args=p.parse_args()
    print(json.dumps(explain(args.question,load(),args.scope,args.mode,args.top_k),indent=2))
if __name__=='__main__':main()
