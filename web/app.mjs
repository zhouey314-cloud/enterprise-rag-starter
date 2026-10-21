import {explain} from './rag.mjs';
const response=await fetch(new URL('../data/documents.json',import.meta.url));if(!response.ok)throw new Error('Failed to load synthetic documents');const docs=await response.json();
const $=id=>document.getElementById(id);
const el=(tag,text,className)=>{const n=document.createElement(tag);n.textContent=text;if(className)n.className=className;return n;};
function run(){const query=$('query').value.trim(),scope=$('scope').value,k=Number($('topk').value),result=explain(query,docs,scope,k),hits=result.hits,answer=$('answer'),chunks=$('chunks');answer.replaceChildren();chunks.replaceChildren();
  if(result.status==='NO_ANSWER'){answer.append(el('p',result.answer,'no'),el('p',`Status: NO_ANSWER · Reason: ${result.no_answer_reason}`),el('p',`Scope: ${scope} · Top-K: ${k} · Mode: lexical`,'muted'));}
  else{const source=result.citations[0];answer.append(el('p',result.answer),el('p',`Status: EXTRACTIVE · Scope: ${scope} · Top-K: ${k}`,'muted'),el('p',`Source: ${source.title} · ${source.chunk_id} · v${source.version}`,'source'));}
  if(!hits.length){chunks.append(el('p','No accessible chunks matched the query.'));return;}
  for(const {doc,score} of hits){const row=el('div','','chunk');row.append(el('div',`${doc.title} · score ${score}`,'score'),el('div',`Chunk ${doc.id}:0 · Access: ${doc.access} · v${doc.version}`,'labels'),el('p',doc.text));chunks.append(row);}
}
$('ask').addEventListener('click',run);$('query').addEventListener('keydown',e=>{if(e.key==='Enter')run();});$('scope').addEventListener('change',run);$('topk').addEventListener('change',run);for(const button of document.querySelectorAll('.example'))button.addEventListener('click',()=>{$('query').value=button.dataset.q;run();});run();
