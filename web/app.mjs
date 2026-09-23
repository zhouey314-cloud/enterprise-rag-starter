const response=await fetch(new URL('../data/documents.json',import.meta.url));if(!response.ok)throw new Error('Failed to load synthetic documents');const docs=await response.json();
const $=id=>document.getElementById(id);
const el=(tag,text,className)=>{const n=document.createElement(tag);n.textContent=text;if(className)n.className=className;return n;};
const words=text=>(text.toLowerCase().match(/[a-z0-9]+/g)||[]);
const stop=new Set(['what','is','the','a','an','for','to','how','does','in','of','our','are','policy']);
function search(query,scope,k){const terms=new Set(words(query).filter(t=>!stop.has(t)));const hits=[];for(const doc of docs){if(doc.access!=='public'&&doc.access!==scope)continue;const title=new Set(words(doc.title)),body=new Set(words(doc.text));let score=0;for(const term of terms)score+=(body.has(term)?1:0)+(title.has(term)?2:0);if(score>0)hits.push({doc,score});}return hits.sort((a,b)=>b.score-a.score||a.doc.id.localeCompare(b.doc.id)).slice(0,k);}
function run(){const query=$('query').value.trim(),scope=$('scope').value,k=Number($('topk').value),hits=search(query,scope,k),answer=$('answer'),chunks=$('chunks');answer.replaceChildren();chunks.replaceChildren();
  if(!hits.length){answer.append(el('p','I do not have enough evidence in the available documents.','no'),el('p','Status: NO_ANSWER · Reason: NO_ACCESSIBLE_LEXICAL_MATCH'),el('p',`Scope: ${scope} · Top-K: ${k} · Mode: lexical`,'muted'));chunks.append(el('p','No accessible chunks matched the query.'));return;}
  const top=hits[0].doc,sentence=top.text.split(/(?<=[.!?])\s+/)[0];answer.append(el('p',sentence),el('p',`Status: EXTRACTIVE · Scope: ${scope} · Top-K: ${k}`,'muted'),el('p',`Source: ${top.title} · ${top.id}:0 · v${top.version}`,'source'));
  for(const {doc,score} of hits){const row=el('div','','chunk');row.append(el('div',`${doc.title} · score ${score}`,'score'),el('div',`Chunk ${doc.id}:0 · Access: ${doc.access} · v${doc.version}`,'labels'),el('p',doc.text));chunks.append(row);}
}
$('ask').addEventListener('click',run);$('query').addEventListener('keydown',e=>{if(e.key==='Enter')run();});$('scope').addEventListener('change',run);$('topk').addEventListener('change',run);for(const button of document.querySelectorAll('.example'))button.addEventListener('click',()=>{$('query').value=button.dataset.q;run();});run();
