import hashlib
import http.client
import json
import os
from pathlib import Path
import selectors
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from localrag import KnowledgeStore, Metadata
from test_local_store import pdf_fixture
import zipfile

ROOT=Path(__file__).resolve().parents[1]


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name);self.database=self.root/'index.sqlite3'
        self.store=KnowledgeStore(self.database)
        self.viewer=self.store.issue_identity('a-viewer','alpha','viewer')
        self.team=self.store.issue_identity('a-team','alpha','team')
        self.beta=self.store.issue_identity('b-admin','beta','admin')
        self.file=self.root/'policy.md';self.file.write_text('Employee onboarding requires access review.')
        self.meta=Metadata('alpha','internal','Employee onboarding','employee.onboarding',1,'2020-01-01',min_role='team')
        self.store.ingest(self.file,self.meta,rights_attested=True)
        self.process=subprocess.Popen([sys.executable,str(ROOT/'local_service.py'),'--db',str(self.database),'serve','--port','0'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        selector=selectors.DefaultSelector();selector.register(self.process.stdout,selectors.EVENT_READ)
        ready=selector.select(timeout=10);selector.close()
        if not ready: self.process.kill();raise RuntimeError('SERVER_START_TIMEOUT')
        line=self.process.stdout.readline()
        if not line: raise RuntimeError('SERVER_DID_NOT_START')
        self.port=json.loads(line)['port']

    def tearDown(self):
        self.process.terminate()
        stdout,stderr=self.process.communicate(timeout=10)
        for token in (self.viewer,self.team,self.beta): self.assertNotIn(token,stdout+stderr)
        self.temp.cleanup()

    def request(self,method,path,body=None,token=None,extra_headers=None):
        connection=http.client.HTTPConnection('127.0.0.1',self.port,timeout=5)
        headers={'Content-Type':'application/json'}
        if token:headers['Authorization']='Bearer '+token
        headers.update(extra_headers or {})
        try:
            connection.request(method,path,json.dumps(body) if body is not None else None,headers)
            response=connection.getresponse();return response.status,json.loads(response.read())
        finally:connection.close()

    def cli(self,*arguments):
        return subprocess.run([sys.executable,str(ROOT/'local_service.py'),'--db',str(self.database),*map(str,arguments)],text=True,capture_output=True)

    def test_http_identity_cannot_be_selected_with_scope_role_tenant_or_date(self):
        for field,value in [('scope','team'),('role','admin'),('tenant','alpha'),('as_of','2020-01-01'),('identity','a-team')]:
            status,result=self.request('POST','/query',{'question':'employee onboarding',field:value},self.viewer)
            self.assertEqual(status,400)
            self.assertNotIn('citations',result)
        self.assertEqual(self.request('POST','/query',{'question':'employee onboarding'})[0],401)
        self.assertEqual(self.request('POST','/query',{'question':'employee onboarding'},'fake-bearer-1234567890')[0],401)
        self.assertEqual(self.request('POST','/query',{'question':'employee onboarding'},self.viewer)[1]['retrieved'],[])
        self.assertEqual(self.request('POST','/query',{'question':'employee onboarding'},self.team)[1]['status'],'EXTRACTIVE')
        self.assertEqual(self.request('POST','/query',{'question':'employee onboarding'},self.beta)[1]['retrieved'],[])

    def test_source_endpoint_enforces_identity_and_current_revision(self):
        self.assertEqual(self.request('GET','/sources/internal/1',token=self.viewer)[0],404)
        self.assertEqual(self.request('GET','/sources/internal/1',token=self.beta)[0],404)
        self.assertEqual(self.request('GET','/sources/internal/1',token=self.team)[0],200)
        self.file.write_text('Employee onboarding requires manager access approval.')
        self.store.ingest(self.file,replace(self.meta,version=2),rights_attested=True)
        self.assertEqual(self.request('GET','/sources/internal/1',token=self.team)[0],404)
        status,result=self.request('POST','/query',{'question':'employee onboarding'},self.team)
        self.assertEqual(status,200);self.assertEqual(result['citations'][0]['version'],2)
        self.assertEqual(result['citations'][0]['sha256'],hashlib.sha256(self.file.read_bytes()).hexdigest())
        self.store.delete('alpha','internal')
        self.assertEqual(self.request('GET','/sources/internal/2',token=self.team)[0],404)
        self.assertEqual(self.request('POST','/query',{'question':'employee onboarding'},self.team)[1]['status'],'NO_ANSWER')

    def test_expiry_conflict_and_revocation_are_live_server_boundaries(self):
        self.store.ingest(self.file,replace(self.meta,version=2,expires_on='2021-01-01'),rights_attested=True)
        self.assertEqual(self.request('POST','/query',{'question':'employee onboarding'},self.team)[1]['retrieved'],[])
        self.store.ingest(self.file,replace(self.meta,version=3),rights_attested=True)
        self.file.write_text('Employee onboarding requires no access review.')
        self.store.ingest(self.file,replace(self.meta,doc_id='disputed'),rights_attested=True)
        result=self.request('POST','/query',{'question':'employee onboarding','top_k':1},self.team)[1]
        self.assertEqual(result['refusal_reason'],'CONFLICTING_CURRENT_SOURCES')
        self.store.revoke_identity('a-team')
        self.assertEqual(self.request('POST','/query',{'question':'employee onboarding'},self.team)[0],401)

    def test_cli_licensed_pdf_docx_and_private_token_output(self):
        tokenfile=self.root/'reader.token'
        result=self.cli('issue-identity','--subject','pdf-reader','--tenant','alpha','--role','viewer','--token-file',tokenfile)
        self.assertEqual(result.returncode,0,result.stderr)
        secret=tokenfile.read_text().strip();self.assertNotIn(secret,result.stdout+result.stderr)
        before=tokenfile.read_bytes()
        self.assertNotEqual(self.cli('issue-identity','--subject','overwrite','--tenant','beta','--role','admin','--token-file',tokenfile).returncode,0)
        self.assertEqual(before,tokenfile.read_bytes());self.assertEqual(tokenfile.stat().st_mode&0o777,0o600)
        pdf=self.root/'licensed.pdf';pdf_fixture(pdf)
        metadata=self.root/'metadata.json';metadata.write_text(json.dumps({'tenant':'alpha','doc_id':'pdf','title':'Refund window','topic':'refund.window','version':1,'effective_on':'2020-01-01'}))
        self.assertNotEqual(self.cli('ingest',pdf,'--metadata',metadata).returncode,0)
        self.assertEqual(self.cli('ingest',pdf,'--metadata',metadata,'--rights-attested').returncode,0)
        result=self.cli('query','refund window','--token-file',tokenfile)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['citations'][0]['page'],2)
        self.assertNotIn(secret,result.stdout+result.stderr)
        status,response=self.request('POST','/query',{'question':'refund window'},secret)
        self.assertEqual(status,200);self.assertEqual(response['citations'][0]['page'],2)
        docx=self.root/'licensed.docx'
        with zipfile.ZipFile(docx,'w') as archive:
            archive.writestr('[Content_Types].xml','<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
            archive.writestr('_rels/.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
            archive.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Travel allowance is twenty credits.</w:t></w:r></w:p></w:body></w:document>')
        metadata.write_text(json.dumps({'tenant':'alpha','doc_id':'docx','title':'Travel allowance','topic':'travel.allowance','version':1,'effective_on':'2020-01-01'}))
        self.assertEqual(self.cli('ingest',docx,'--metadata',metadata,'--rights-attested').returncode,0)
        status,response=self.request('POST','/query',{'question':'travel allowance'},secret)
        self.assertEqual(status,200);self.assertIsNone(response['citations'][0]['page'])
        self.assertIn('paragraph:1',response['citations'][0]['locator'])

    def test_request_validation_and_nonloopback_bind_fail_closed(self):
        for value in [[],{'question':''},{'question':'x','top_k':True},{'question':'x'*2001}]:
            self.assertEqual(self.request('POST','/query',value,self.team)[0],400)
        self.assertEqual(self.request('GET','/health',extra_headers={'Host':'evil.example'})[0],400)
        self.assertEqual(self.request('GET','/sources/internal/1?tenant=beta',token=self.team)[0],400)
        self.assertNotEqual(self.cli('serve','--host','0.0.0.0','--port','0').returncode,0)


if __name__=='__main__':unittest.main()
