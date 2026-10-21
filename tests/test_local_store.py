import hashlib
from pathlib import Path
import tempfile
import unittest
import zipfile
from dataclasses import replace
from localrag import KnowledgeStore, Metadata
from local_ingest import parse_file


def pdf_fixture(path):
    """Two-page, self-authored ASCII PDF; no downloaded or personal fixture."""
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>',
               b'<< /Type /Pages /Kids [3 0 R 4 0 R] /Count 2 >>',
               b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] /Resources << /Font << /F1 5 0 R >> >> /Contents 6 0 R >>',
               b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] /Resources << /Font << /F1 5 0 R >> >> /Contents 7 0 R >>',
               b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    for text in ['Support hours are 09:00 to 17:00.', 'Refund window is fourteen days.']:
        stream = f'BT /F1 12 Tf 20 200 Td ({text}) Tj ET'.encode()
        objects.append(b'<< /Length '+str(len(stream)).encode()+b' >>\nstream\n'+stream+b'\nendstream')
    data = bytearray(b'%PDF-1.4\n'); offsets = [0]
    for index, value in enumerate(objects, 1):
        offsets.append(len(data)); data.extend(f'{index} 0 obj\n'.encode()+value+b'\nendobj\n')
    xref = len(data); data.extend(f'xref\n0 {len(objects)+1}\n0000000000 65535 f \n'.encode())
    for offset in offsets[1:]: data.extend(f'{offset:010} 00000 n \n'.encode())
    data.extend(f'trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode())
    path.write_bytes(data)


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = KnowledgeStore(self.root/'index.sqlite3')
        self.viewer = self.store.issue_identity('viewer-a', 'alpha', 'viewer')
        self.team = self.store.issue_identity('team-a', 'alpha', 'team')
        self.other = self.store.issue_identity('viewer-b', 'beta', 'admin')
        self.path = self.root/'policy.md'
        self.path.write_text('Support hours are 09:00 to 17:00.')
        self.meta = Metadata('alpha','support','Support hours','support.hours',1,'2020-01-01')

    def tearDown(self): self.temp.cleanup()

    def ingest(self, **changes):
        return self.store.ingest(self.path,replace(self.meta,**changes),rights_attested=True)

    def test_english_present_tense_inflection_keeps_supported_answer(self):
        self.path.write_text('Onboarding checklist contains account review and safety briefing.')
        self.ingest(title='Onboarding checklist')
        result=self.store.query(self.viewer,'What does the onboarding checklist contain?')
        self.assertEqual(result['status'],'EXTRACTIVE')
        self.assertIn('contains account review',result['answer'])
        self.assertEqual(self.store.query(self.viewer,'What is the onboarding phone?')['status'],'NO_ANSWER')

    def test_chinese_terminal_question_word_is_not_missing_evidence(self):
        self.path.write_text('访客登记需要出示合成访客码。')
        self.ingest(title='访客登记')
        self.assertEqual(self.store.query(self.viewer,'访客登记需要什么？')['status'],'EXTRACTIVE')
        self.assertEqual(self.store.query(self.viewer,'访客登记客服电话？')['status'],'NO_ANSWER')

    def test_identity_is_server_side_and_revocable(self):
        self.assertEqual(self.store.authenticate(self.viewer)['role'],'viewer')
        with self.assertRaises(PermissionError): self.store.authenticate('synthetic-invalid-token-123456')
        with self.assertRaises(ValueError): self.store.issue_identity('bad','alpha','owner')
        self.store.revoke_identity('viewer-a')
        with self.assertRaises(PermissionError): self.store.query(self.viewer,'support hours')
        with self.store.connect() as db:
            self.assertNotIn(self.team, repr(list(db.execute('SELECT * FROM identities'))))

    def test_rights_attestation_and_private_database_mode(self):
        with self.assertRaises(ValueError): self.store.ingest(self.path,self.meta)
        self.assertEqual(self.store.path.stat().st_mode & 0o777,0o600)

    def test_acl_filters_trace_and_source_before_ranking(self):
        self.ingest(min_role='team')
        for token in [self.viewer,self.other]:
            result = self.store.query(token,'support hours')
            self.assertEqual(result['retrieved'],[])
            with self.assertRaises(LookupError): self.store.source(token,'support',1)
        self.assertEqual(self.store.query(self.team,'support hours')['status'],'EXTRACTIVE')

    def test_incremental_hash_and_version_update_remove_stale_citations(self):
        first = self.ingest()
        self.assertEqual(self.ingest()['status'],'UNCHANGED')
        self.path.write_text('Support hours are 10:00 to 18:00.')
        with self.assertRaises(ValueError): self.ingest()
        second = self.ingest(version=2)
        result = self.store.query(self.viewer,'support hours')
        self.assertIn('10:00',result['answer'])
        self.assertEqual(result['citations'][0]['version'],2)
        self.assertNotEqual(first['sha256'],second['sha256'])
        self.assertEqual(second['sha256'],hashlib.sha256(self.path.read_bytes()).hexdigest())
        with self.assertRaises(LookupError): self.store.source(self.viewer,'support',1)

    def test_metadata_change_is_not_skipped_as_unchanged_content(self):
        self.ingest()
        with self.assertRaises(ValueError): self.ingest(min_role='admin')
        self.ingest(version=2,min_role='admin')
        self.assertEqual(self.store.query(self.viewer,'support hours')['status'],'NO_ANSWER')

    def test_expired_and_future_documents_cannot_be_quoted(self):
        self.ingest(expires_on='2021-01-01')
        self.assertEqual(self.store.query(self.viewer,'support hours')['retrieved'],[])
        self.ingest(version=2,effective_on='2999-01-01')
        self.assertEqual(self.store.query(self.viewer,'support hours')['retrieved'],[])

    def test_compact_date_cannot_bypass_string_ordered_expiry(self):
        # fromisoformat accepts YYYYMMDD, whose lexical ordering differs from YYYY-MM-DD.
        with self.assertRaises(ValueError): self.ingest(expires_on='20261001')

    def test_delete_removes_query_and_source_access(self):
        self.ingest(); self.store.delete('alpha','support')
        self.assertEqual(self.store.query(self.viewer,'support hours')['retrieved'],[])
        with self.assertRaises(LookupError): self.store.source(self.viewer,'support',1)

    def test_conflict_refuses_even_if_client_top_k_is_one(self):
        self.ingest()
        self.path.write_text('Support hours are 11:00 to 19:00.')
        self.ingest(doc_id='support-copy')
        result = self.store.query(self.viewer,'support hours',top_k=1)
        self.assertEqual(result['refusal_reason'],'CONFLICTING_CURRENT_SOURCES')
        self.assertEqual(result['citations'],[])

    def test_same_filename_different_tenants_and_doc_ids(self):
        self.ingest()
        self.path.write_text('Support hours are private beta hours.')
        self.ingest(tenant='beta')
        self.assertNotIn('beta',self.store.query(self.viewer,'support hours')['answer'])
        self.assertIn('beta',self.store.query(self.other,'support hours')['answer'])

    def test_related_support_evidence_does_not_provide_a_phone(self):
        self.ingest()
        result = self.store.query(self.viewer,'support phone')
        self.assertTrue(result['retrieved'])
        self.assertEqual(result['status'],'NO_ANSWER')
        self.assertEqual(result['citations'],[])

    def test_pdf_pages_and_docx_paragraphs_are_not_fabricated(self):
        pdf = self.root/'licensed.pdf'; pdf_fixture(pdf)
        pdf_passages = parse_file(pdf)
        self.assertEqual([p.page for p in pdf_passages],[1,2])
        docx = self.root/'licensed.docx'
        with zipfile.ZipFile(docx,'w') as archive:
            archive.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Self authored docx evidence.</w:t></w:r></w:p></w:body></w:document>')
        paragraph = parse_file(docx)[0]
        self.assertIsNone(paragraph.page)
        self.assertIn('paragraph:1',paragraph.locator)

    def test_shared_document_title_cannot_make_wrong_pdf_page_answerable(self):
        pdf=self.root/'licensed.pdf';pdf_fixture(pdf)
        self.store.ingest(pdf,replace(self.meta,doc_id='refund',title='Refund window',topic='refund.window'),rights_attested=True)
        result=self.store.query(self.viewer,'refund window')
        self.assertEqual(result['citations'][0]['page'],2)
        self.assertIn('fourteen days',result['answer'])

    def test_failed_parse_does_not_destroy_current_revision(self):
        self.ingest()
        bad = self.root/'invalid.docx';bad.write_bytes(b'not a docx')
        with self.assertRaises(zipfile.BadZipFile): self.store.ingest(bad,replace(self.meta,version=2),rights_attested=True)
        self.assertEqual(self.store.query(self.viewer,'support hours')['citations'][0]['version'],1)

    def test_question_and_metadata_limits(self):
        for question in ['', 'x'*2001]:
            with self.assertRaises(ValueError): self.store.query(self.viewer,question)
        with self.assertRaises(ValueError): self.store.query(self.viewer,'support',top_k=True)
        with self.assertRaises(ValueError): self.ingest(version=True)
        with self.assertRaises(ValueError): self.ingest(effective_on='invalid')


if __name__=='__main__': unittest.main()
