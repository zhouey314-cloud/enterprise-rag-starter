"""Authenticated local extractive retrieval reference, independent of the static demo."""
from dataclasses import dataclass, asdict
from datetime import date
from pathlib import Path
from contextlib import contextmanager, closing
import hashlib
import json
import os
import re
import secrets
import sqlite3
import time
from local_ingest import parse_file, source_bytes

ROLES = {'viewer': 0, 'team': 1, 'admin': 2}
STOP = set('what is are the a an for to how does in of our policy can i do when many which please tell me about'.split())


def terms(text):
    english = re.findall(r'[a-z0-9]+', text.lower())
    chinese = re.findall(r'[\u4e00-\u9fff]+', text)
    return set(english) - STOP | {word[i:i+2] for word in chinese for i in range(max(1, len(word)-1))}


@dataclass(frozen=True)
class Metadata:
    tenant: str
    doc_id: str
    title: str
    topic: str
    version: int
    effective_on: str
    expires_on: str | None = None
    min_role: str = 'viewer'

    def validate(self):
        for value in (self.tenant, self.doc_id, self.topic):
            if not re.fullmatch(r'[A-Za-z0-9_.-]{1,80}', value): raise ValueError('INVALID_IDENTIFIER')
        if not self.title.strip() or len(self.title) > 200: raise ValueError('INVALID_TITLE')
        if type(self.version) is not int or self.version < 1: raise ValueError('INVALID_VERSION')
        if self.min_role not in ROLES: raise ValueError('INVALID_ROLE')
        start = date.fromisoformat(self.effective_on)
        if start.isoformat() != self.effective_on: raise ValueError('CANONICAL_ISO_DATE_REQUIRED')
        if self.expires_on:
            end = date.fromisoformat(self.expires_on)
            if end.isoformat() != self.expires_on: raise ValueError('CANONICAL_ISO_DATE_REQUIRED')
            if end <= start: raise ValueError('INVALID_DATE_INTERVAL')


class KnowledgeStore:
    def __init__(self, database):
        self.path = Path(database)
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.path.is_symlink(): raise ValueError('DATABASE_SYMLINK_FORBIDDEN')
        if not self.path.exists():
            descriptor = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(descriptor)
        with self.connect() as db:
            db.executescript('''
              CREATE TABLE IF NOT EXISTS identities (
                subject TEXT PRIMARY KEY, digest TEXT UNIQUE NOT NULL, tenant TEXT NOT NULL,
                role TEXT NOT NULL, revoked INTEGER NOT NULL DEFAULT 0);
              CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY, tenant TEXT NOT NULL, doc_id TEXT NOT NULL,
                version INTEGER NOT NULL, title TEXT NOT NULL, topic TEXT NOT NULL,
                effective_on TEXT NOT NULL, expires_on TEXT, min_role INTEGER NOT NULL,
                sha256 TEXT NOT NULL, fingerprint TEXT NOT NULL, filename TEXT NOT NULL,
                current INTEGER NOT NULL, deleted INTEGER NOT NULL DEFAULT 0,
                UNIQUE(tenant,doc_id,version));
              CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY, document INTEGER NOT NULL REFERENCES documents(id),
                text TEXT NOT NULL, page INTEGER, locator TEXT NOT NULL);
              CREATE INDEX IF NOT EXISTS document_eligibility ON documents(tenant,current,deleted,min_role,effective_on);
            ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            with db: yield db
        finally:
            db.close()

    def issue_identity(self, subject, tenant, role):
        if role not in ROLES or not re.fullmatch(r'[A-Za-z0-9_.-]{1,80}', tenant): raise ValueError('INVALID_IDENTITY')
        if not subject or len(subject) > 100: raise ValueError('INVALID_IDENTITY')
        token = secrets.token_urlsafe(32)
        with self.connect() as db:
            db.execute('INSERT INTO identities(subject,digest,tenant,role) VALUES(?,?,?,?)',
                       (subject, hashlib.sha256(token.encode()).hexdigest(), tenant, role))
        return token  # Trusted provisioning CLI writes this once to a mode-0600 file.

    def revoke_identity(self, subject):
        with self.connect() as db: db.execute('UPDATE identities SET revoked=1 WHERE subject=?', (subject,))

    def authenticate(self, token):
        if not isinstance(token, str) or not 20 <= len(token) <= 200: raise PermissionError('UNAUTHORIZED')
        with self.connect() as db:
            row = db.execute('SELECT subject,tenant,role FROM identities WHERE digest=? AND revoked=0',
                             (hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
        if not row: raise PermissionError('UNAUTHORIZED')
        return dict(row)

    def ingest(self, path, metadata, *, rights_attested=False):
        if rights_attested is not True: raise ValueError('LICENSE_ATTESTATION_REQUIRED')
        metadata.validate()
        path = Path(path)
        raw = source_bytes(path)
        passages = parse_file(path, raw)
        digest = hashlib.sha256(raw).hexdigest()
        fingerprint = hashlib.sha256(json.dumps([asdict(metadata), digest], sort_keys=True).encode()).hexdigest()
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            previous = db.execute('SELECT * FROM documents WHERE tenant=? AND doc_id=? ORDER BY version DESC LIMIT 1',
                                  (metadata.tenant, metadata.doc_id)).fetchone()
            if previous and metadata.version == previous['version'] and fingerprint == previous['fingerprint'] and previous['current'] and not previous['deleted']:
                return {'status': 'UNCHANGED', 'sha256': digest, 'chunks': len(passages)}
            if previous and metadata.version <= previous['version']: raise ValueError('VERSION_MUST_INCREASE')
            db.execute('UPDATE documents SET current=0 WHERE tenant=? AND doc_id=?', (metadata.tenant, metadata.doc_id))
            cursor = db.execute('''INSERT INTO documents(tenant,doc_id,version,title,topic,effective_on,expires_on,min_role,sha256,fingerprint,filename,current)
              VALUES(?,?,?,?,?,?,?,?,?,?,?,1)''',
              (metadata.tenant, metadata.doc_id, metadata.version, metadata.title, metadata.topic, metadata.effective_on,
               metadata.expires_on, ROLES[metadata.min_role], digest, fingerprint, path.name))
            db.executemany('INSERT INTO chunks(document,text,page,locator) VALUES(?,?,?,?)',
                           [(cursor.lastrowid, p.text, p.page, p.locator) for p in passages])
        return {'status': 'INDEXED', 'sha256': digest, 'chunks': len(passages)}

    def delete(self, tenant, doc_id):
        with self.connect() as db:
            cursor = db.execute('UPDATE documents SET current=0,deleted=1 WHERE tenant=? AND doc_id=?', (tenant, doc_id))
        return {'status': 'DELETED', 'revisions': cursor.rowcount}

    def eligible(self, identity, at=None):
        today = date.fromisoformat(at).isoformat() if at else date.today().isoformat()  # Internal clock injection only; never HTTP.
        with self.connect() as db:
            rows = db.execute('''SELECT c.id chunk_id,c.text,c.page,c.locator,d.* FROM documents d JOIN chunks c ON c.document=d.id
              WHERE d.tenant=? AND d.min_role<=? AND d.current=1 AND d.deleted=0
              AND d.effective_on<=? AND (d.expires_on IS NULL OR d.expires_on>?) ORDER BY c.id LIMIT 10001''',
              (identity['tenant'], ROLES[identity['role']], today, today)).fetchall()
        if len(rows) > 10000: raise ValueError('AUTHORIZED_CORPUS_LIMIT')
        return [dict(row) for row in rows]

    def query(self, token, question, top_k=3, *, at=None):
        start = time.perf_counter()
        identity = self.authenticate(token)
        if not isinstance(question, str) or not question.strip() or len(question) > 2000: raise ValueError('INVALID_QUESTION')
        if type(top_k) is not int or not 1 <= top_k <= 10: raise ValueError('INVALID_TOP_K')
        candidates = self.eligible(identity, at)
        query_terms = terms(question)
        lookup = {str(row['chunk_id']): row for row in candidates}
        overlap = sorted([(key, len(query_terms & terms(row['title']+' '+row['text']))) for key,row in lookup.items()], key=lambda x:(-x[1],x[0]))
        overlap = [key for key, score in overlap if score > 0]
        # Rank only the authorized snapshot: global/private corpus statistics cannot affect scores.
        with closing(sqlite3.connect(':memory:')) as search:
            search.execute('CREATE VIRTUAL TABLE permitted USING fts5(body,title)')
            search.executemany('INSERT INTO permitted(rowid,body,title) VALUES(?,?,?)',
                               [(int(key),' '.join(terms(row['text'])),' '.join(terms(row['title']))) for key,row in lookup.items()])
            expression = ' OR '.join('"'+word.replace('"','""')+'"' for word in sorted(query_terms))
            fts = [str(r[0]) for r in search.execute('SELECT rowid FROM permitted WHERE permitted MATCH ? ORDER BY bm25(permitted),rowid', (expression,))] if expression else []
        scores = {}
        for ranking in (fts, overlap):
            for rank, key in enumerate(ranking): scores[key] = scores.get(key,0)+1/(60+rank+1)
        ranked = sorted(scores, key=lambda key:(-scores[key],key))
        # A shared document title can retrieve a page, but cannot prove that page contains the answer.
        supported = [key for key in ranked if query_terms and len(query_terms & terms(lookup[key]['text']))/len(query_terms) >= 0.8]
        reason = 'INSUFFICIENT_EVIDENCE'
        if supported:
            best = lookup[supported[0]]
            comparable = [lookup[key] for key in supported if lookup[key]['topic'] == best['topic']]
            conflict = any(row['doc_id'] != best['doc_id'] and row['text'].strip() != best['text'].strip() for row in comparable)
            reason = 'CONFLICTING_CURRENT_SOURCES' if conflict else None
        result = {'status':'NO_ANSWER' if reason else 'EXTRACTIVE','answer':None,'citations':[],
                  'refusal_reason':reason,'provider':'deterministic_extract','retrieval_mode':'authorized_fts5_overlap_rrf',
                  'retrieved':[self.citation(lookup[key]) for key in ranked[:top_k]]}
        if not reason:
            result['answer'] = best['text']
            result['citations'] = [self.citation(best)]
        result['latency_ms'] = round((time.perf_counter()-start)*1000,3)
        return result

    @staticmethod
    def citation(row):
        return {key:row[key] for key in ('doc_id','version','title','filename','sha256','effective_on','expires_on','chunk_id','page','locator','text')}

    def source(self, token, doc_id, version):
        identity = self.authenticate(token)
        rows = [row for row in self.eligible(identity) if row['doc_id']==doc_id and row['version']==version]
        if not rows: raise LookupError('SOURCE_NOT_AVAILABLE')
        return {'source':[self.citation(row) for row in rows]}
