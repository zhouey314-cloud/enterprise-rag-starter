"""Offline lexical RAG baseline with real citations and conservative no-answer."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json
import re

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

def retrieve(query:str,chunks:list[Chunk],scope:str='public',k:int=3)->list[dict]:
    terms=set(words(query))-{ 'what','is','the','a','an','for','to','how','does','in','of','our','are' }
    scored=[]
    for c in chunks:
        if c.access not in {'public',scope}:continue
        body=set(words(c.text));title=set(words(c.title))
        score=len(terms&body)+2*len(terms&title)
        if score>0:scored.append({'chunk':c,'score':score})
    return sorted(scored,key=lambda x:(-x['score'],x['chunk'].id))[:k]

def rerank(results:list[dict])->list[dict]:return sorted(results,key=lambda x:(-x['score'],x['chunk'].id))

def answer(question:str,chunks:list[Chunk],scope:str='public')->dict:
    hits=rerank(retrieve(question,chunks,scope))
    if not hits:return {'answer':'I do not have enough evidence in the available documents.','citations':[],'status':'NO_ANSWER','provider':'offline_lexical'}
    best=hits[0]['chunk']
    sentence=re.split(r'(?<=[.!?])\s+',best.text)[0]
    return {'answer':sentence,'citations':[{'doc_id':best.doc_id,'chunk_id':best.id,'title':best.title,'version':best.version}],'status':'EXTRACTIVE','provider':'offline_lexical'}

def load()->list[Chunk]:return [c for doc in json.loads(Path('data/documents.json').read_text()) for c in chunk_document(doc)]
def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('question');p.add_argument('--scope',default='public');args=p.parse_args()
    print(json.dumps(answer(args.question,load(),args.scope),indent=2))
if __name__=='__main__':main()
