"""Trusted local operator CLI and loopback-only token-authenticated JSON service."""
import argparse
import http.server
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
from urllib.parse import urlsplit
from localrag import KnowledgeStore, Metadata


def handler_for(store):
    class Handler(http.server.BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.0'  # Close each request; no request-body reuse or cookies.

        def setup(self):
            super().setup()
            self.connection.settimeout(5)

        def log_message(self, *_): pass  # Never log Authorization, question text or document content.

        def respond(self, code, value):
            raw = json.dumps(value, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.send_header('Content-Length',str(len(raw)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.end_headers(); self.wfile.write(raw)

        def token(self):
            values = self.headers.get_all('Authorization', [])
            if len(values)!=1 or not values[0].startswith('Bearer '): raise PermissionError('UNAUTHORIZED')
            return values[0][7:]

        def route(self):
            route = urlsplit(self.path)
            if route.query: raise ValueError('QUERY_PARAMETERS_NOT_SUPPORTED')
            host = self.headers.get('Host','').split(':')[0]
            if host not in {'127.0.0.1','localhost'}: raise ValueError('LOCAL_HOST_REQUIRED')
            return route.path

        def run_route(self, callback):
            try: callback()
            except (BrokenPipeError,ConnectionResetError,TimeoutError): return
            except PermissionError: self.respond(401, {'error':'UNAUTHORIZED'})
            except LookupError: self.respond(404, {'error':'SOURCE_NOT_AVAILABLE'})
            except (ValueError, UnicodeError): self.respond(400, {'error':'INVALID_REQUEST'})
            except Exception: self.respond(500, {'error':'INTERNAL_ERROR'})

        def do_GET(self):
            def perform():
                route = self.route()
                if route=='/health': self.respond(200, {'status':'ok','provider':'deterministic_extract'}); return
                match = re.fullmatch(r'/sources/([A-Za-z0-9_.-]{1,80})/([0-9]{1,9})',route)
                if not match: self.respond(404, {'error':'NOT_FOUND'}); return
                self.respond(200,store.source(self.token(),match[1],int(match[2])))
            self.run_route(perform)

        def do_POST(self):
            def perform():
                if self.route()!='/query': self.respond(404, {'error':'NOT_FOUND'}); return
                token = self.token()
                store.authenticate(token)  # Authenticate before parsing potentially large bodies.
                sizes = self.headers.get_all('Content-Length',[])
                if len(sizes)!=1 or self.headers.get('Transfer-Encoding'): raise ValueError('INVALID_FRAMING')
                if not re.fullmatch(r'[0-9]{1,6}',sizes[0]): raise ValueError('INVALID_LENGTH')
                size = int(sizes[0])
                if not 0 < size <= 16384: raise ValueError('BODY_LIMIT')
                raw = self.rfile.read(size)
                if len(raw)!=size: raise ValueError('INCOMPLETE_BODY')
                value = json.loads(raw)
                # No tenant/role/scope/as_of/identity field is accepted from a query client.
                if not isinstance(value,dict) or set(value)-{'question','top_k'} or 'question' not in value:
                    raise ValueError('INVALID_QUERY_SCHEMA')
                result = store.query(token,value['question'],value.get('top_k',3))
                self.respond(200,result)
            self.run_route(perform)
    return Handler


def read_token(path):
    path = Path(path)
    if path.is_symlink() or path.stat().st_mode & 0o077: raise ValueError('PRIVATE_TOKEN_FILE_REQUIRED')
    return path.read_text().strip()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db',default='.rag-data/index.sqlite3')
    commands = parser.add_subparsers(dest='command',required=True)
    commands.add_parser('init')
    commands.add_parser('doctor')
    backup = commands.add_parser('backup'); backup.add_argument('--out', required=True)
    restore = commands.add_parser('restore'); restore.add_argument('--from-backup', required=True)
    identity = commands.add_parser('issue-identity')
    for name in ['subject','tenant','role','token-file']: identity.add_argument('--'+name,required=True)
    revoke = commands.add_parser('revoke-identity'); revoke.add_argument('subject')
    ingest = commands.add_parser('ingest')
    ingest.add_argument('file'); ingest.add_argument('--metadata',required=True)
    ingest.add_argument('--rights-attested',action='store_true')
    delete = commands.add_parser('delete'); delete.add_argument('--tenant',required=True); delete.add_argument('--doc-id',required=True)
    query = commands.add_parser('query'); query.add_argument('question'); query.add_argument('--token-file',required=True)
    source = commands.add_parser('source'); source.add_argument('doc_id'); source.add_argument('version',type=int); source.add_argument('--token-file',required=True)
    serve = commands.add_parser('serve'); serve.add_argument('--host',default='127.0.0.1'); serve.add_argument('--port',type=int,default=8767)
    args = parser.parse_args(argv)
    try:
        from local_ops import inspect_database, copy_database
        if args.command == 'doctor':
            print(json.dumps(inspect_database(args.db))); return 0
        if args.command in {'backup', 'restore'}:
            result = (copy_database(args.db,args.out) if args.command == 'backup'
                      else copy_database(args.from_backup,args.db))
            print(json.dumps(result)); return 0
        if args.command != 'init' and not Path(args.db).is_file():
            raise ValueError('EXISTING_DATABASE_REQUIRED: run init explicitly')
        store = KnowledgeStore(args.db)
        if args.command=='init': result={'status':'INITIALIZED'}
        elif args.command=='issue-identity':
            path = Path(args.token_file)
            descriptor = os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
            created = False
            try:
                token = store.issue_identity(args.subject,args.tenant,args.role); created = True
                with os.fdopen(descriptor,'w') as file: file.write(token+'\n'); descriptor=None
            except Exception:
                if descriptor is not None: os.close(descriptor)
                path.unlink()
                if created: store.revoke_identity(args.subject)
                raise
            result={'status':'ISSUED','subject':args.subject,'token_file':str(path)}
        elif args.command=='revoke-identity': store.revoke_identity(args.subject);result={'status':'REVOKED'}
        elif args.command=='ingest': result=store.ingest(args.file,Metadata(**json.loads(Path(args.metadata).read_text())),rights_attested=args.rights_attested)
        elif args.command=='delete': result=store.delete(args.tenant,args.doc_id)
        elif args.command=='query': result=store.query(read_token(args.token_file),args.question)
        elif args.command=='source': result=store.source(read_token(args.token_file),args.doc_id,args.version)
        else:
            if args.host!='127.0.0.1' or not 0 <= args.port <= 65535: raise ValueError('LOOPBACK_ONLY')
            server=http.server.ThreadingHTTPServer((args.host,args.port),handler_for(store))
            server.daemon_threads=True
            print(json.dumps({'event':'listening','host':args.host,'port':server.server_port}),flush=True)
            try: server.serve_forever()
            except KeyboardInterrupt: pass
            finally: server.server_close()
            return 0
        print(json.dumps(result,ensure_ascii=False)); return 0
    except Exception as error:
        print(json.dumps({'error':'OPERATION_FAILED','failure_class':type(error).__name__,'detail':'Check local arguments, rights, schema, token permissions and unique output paths.'}),file=sys.stderr)
        return 2


if __name__=='__main__': raise SystemExit(main())
