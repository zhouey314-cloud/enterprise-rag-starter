// Offline lexical demo logic; scope is illustrative filtering, not authentication.
const words=text=>(text.toLowerCase().match(/[a-z0-9]+/g)||[]);
const stop=new Set(['what','is','the','a','an','for','to','how','does','in','of','our','are','policy']);
const termsFor=query=>new Set(words(query).filter(t=>!stop.has(t)));

export function search(query,docs,scope='public',k=3){
  const terms=termsFor(query),hits=[];
  for(const doc of docs){
    if(doc.access!=='public'&&doc.access!==scope)continue;
    const title=new Set(words(doc.title)),body=new Set(words(doc.text));let score=0;
    for(const term of terms)score+=(body.has(term)?1:0)+(title.has(term)?2:0);
    if(score>0)hits.push({doc,score});
  }
  return hits.sort((a,b)=>b.score-a.score||a.doc.id.localeCompare(b.doc.id)).slice(0,k);
}

export function explain(query,docs,scope='public',k=3){
  const hits=search(query,docs,scope,k),top=hits[0]?.doc,terms=termsFor(query);
  const evidence=new Set(words(top?`${top.title} ${top.text}`:''));
  const coverage=terms.size?[...terms].filter(t=>evidence.has(t)).length/terms.size:1;
  const reason=!top?'NO_ACCESSIBLE_LEXICAL_MATCH':coverage<0.6?'QUESTION_NOT_ANSWERABLE_BY_TOP_HIT':null;
  return {hits,status:reason?'NO_ANSWER':'EXTRACTIVE',no_answer_reason:reason,
    answer:reason?'I do not have enough evidence in the available documents.':top.text.split(/(?<=[.!?])\s+/)[0],
    citations:reason?[]:[{doc_id:top.id,chunk_id:`${top.id}:0`,title:top.title,version:top.version}]};
}
