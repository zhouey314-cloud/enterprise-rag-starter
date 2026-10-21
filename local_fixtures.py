"""Generate only repository-owned fictional MD/PDF/DOCX examples; no external data."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import zipfile
from xml.sax.saxutils import escape
from localrag import Metadata

ROOT = Path(__file__).resolve().parent


def write_pdf(path, pages):
    """Small valid ASCII PDF with an actual page tree; no renderer or download."""
    count = len(pages)
    font = count + 3
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>',
               f'<< /Type /Pages /Kids [{" ".join(f"{i+3} 0 R" for i in range(count))}] /Count {count} >>'.encode()]
    for index in range(count):
        objects.append(f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 600 400] /Resources << /Font << /F1 {font} 0 R >> >> /Contents {font+index+1} 0 R >>'.encode())
    objects.append(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>')
    for text in pages:
        literal = text.replace('\\','\\\\').replace('(','\\(').replace(')','\\)')
        stream = f'BT /F1 12 Tf 20 300 Td ({literal}) Tj ET'.encode('ascii')
        objects.append(b'<< /Length '+str(len(stream)).encode()+b' >>\nstream\n'+stream+b'\nendstream')
    data = bytearray(b'%PDF-1.4\n'); offsets = [0]
    for index, value in enumerate(objects, 1):
        offsets.append(len(data));data.extend(f'{index} 0 obj\n'.encode()+value+b'\nendobj\n')
    xref=len(data);data.extend(f'xref\n0 {len(objects)+1}\n0000000000 65535 f \n'.encode())
    for offset in offsets[1:]:data.extend(f'{offset:010} 00000 n \n'.encode())
    data.extend(f'trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode())
    path.write_bytes(data)


def write_docx(path, paragraphs):
    parts = {
      '[Content_Types].xml':'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>',
      '_rels/.rels':'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>',
      'word/document.xml':'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'+''.join('<w:p><w:r><w:t>'+escape(text)+'</w:t></w:r></w:p>' for text in paragraphs)+'</w:body></w:document>'}
    with zipfile.ZipFile(path,'x',compression=zipfile.ZIP_DEFLATED) as archive:
        for name, text in sorted(parts.items()):
            info=zipfile.ZipInfo(name,(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            archive.writestr(info,text.encode('utf-8'))


def materialize(root, documents):
    root=Path(root);root.mkdir(parents=True,exist_ok=True,mode=0o700);manifest=[]
    for document in documents:
        meta=Metadata(**document['metadata']);meta.validate()
        filename=f'{meta.tenant}-{meta.doc_id}-v{meta.version}'
        path=root/(filename+'.'+document['format'])
        if path.exists():raise ValueError('FIXTURE_OUTPUT_ALREADY_EXISTS')
        if document['format']=='md':path.write_text('\n\n'.join(document['passages'])+'\n')
        elif document['format']=='pdf':write_pdf(path,document['passages'])
        elif document['format']=='docx':write_docx(path,document['passages'])
        else:raise ValueError('UNSUPPORTED_FIXTURE_FORMAT')
        metadata=root/(filename+'.json');metadata.write_text(json.dumps(asdict(meta),ensure_ascii=False,indent=2)+'\n')
        manifest.append({'file':path.name,'metadata':metadata.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'provenance':'synthetic_unverified','license':'MIT','delete_after_import':document.get('delete_after_import',False)})
    (root/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


def load_corpus():return json.loads((ROOT/'evals/local-corpus.json').read_text())
