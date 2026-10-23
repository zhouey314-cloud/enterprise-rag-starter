import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import test from 'node:test';
import {explain} from '../web/rag.mjs';

const docs=JSON.parse(await readFile(new URL('../data/documents.json',import.meta.url),'utf8'));
const cases=(await readFile(new URL('../evals/answerability.jsonl',import.meta.url),'utf8')).trim().split('\n').map(line=>JSON.parse(line));
for(const c of cases)test(`lexical browser: ${c.id}`,()=>{
  const result=explain(c.question,docs,c.scope||'public',1);
  assert.equal(result.hits[0]?.doc.id??null,c.expected_doc);
  assert.equal(result.status,c.expected_status);
  assert.ok(result.hits.every(h=>h.doc.access==='public'||h.doc.access===c.scope));
  if(c.expected_status==='NO_ANSWER')assert.deepEqual(result.citations,[]);
  else{assert.equal(result.citations[0].doc_id,c.expected_doc);assert.ok(result.answer.includes(c.answer_contains));}
});
test('phone information is allowed when it is present in the source',()=>{
  const result=explain('What is the support phone number?',[{id:'contact',title:'Support contact',text:'The support phone number is 555-0100.',access:'public',version:1}]);
  assert.equal(result.status,'EXTRACTIVE');assert.ok(result.answer.includes('555-0100'));
});

const excerptCases=(await readFile(new URL('../evals/excerpts.jsonl',import.meta.url),'utf8')).trim().split('\n').map(JSON.parse);
for(const c of excerptCases)test(`excerpt browser: ${c.id}`,()=>{
  const result=explain(c.question,[c.document],c.scope||'public');
  assert.equal(result.status,c.expected_status);
  assert.ok(result.hits.every(h=>h.doc.access==='public'||h.doc.access===c.scope));
  if(c.expected_status==='NO_ANSWER')assert.deepEqual(result.citations,[]);
  else{
    assert.equal(result.answer,c.expected_answer);
    assert.ok(c.document.text.includes(result.answer));
    assert.deepEqual(result.citations,[{doc_id:c.document.id,chunk_id:`${c.document.id}:0`,title:c.document.title,version:c.document.version}]);
  }
});
