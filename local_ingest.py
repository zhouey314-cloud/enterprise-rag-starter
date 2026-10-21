"""Bounded local parsing; no network, OCR, rendering or fabricated DOCX pages."""
from dataclasses import dataclass
from pathlib import Path
import io
import zipfile
import xml.etree.ElementTree as ET

MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_TEXT_BYTES = 2 * 1024 * 1024


@dataclass(frozen=True)
class Passage:
    text: str
    page: int | None
    locator: str


def source_bytes(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ValueError('REGULAR_LOCAL_FILE_REQUIRED')
    with path.open('rb') as stream: raw = stream.read(MAX_FILE_BYTES+1)
    if len(raw) > MAX_FILE_BYTES:
        raise ValueError('FILE_TOO_LARGE')
    return raw


def parse_file(path: Path, raw: bytes | None = None) -> list[Passage]:
    raw = source_bytes(path) if raw is None else raw
    if len(raw) > MAX_FILE_BYTES: raise ValueError('FILE_TOO_LARGE')
    suffix = path.suffix.lower()
    passages = []
    if suffix == '.md':
        lines = raw.decode('utf-8').splitlines()
        start, paragraph = 1, []
        for number, line in enumerate(lines + [''], 1):
            if line.strip():
                if not paragraph: start = number
                paragraph.append(line)
            elif paragraph:
                passages.append(Passage('\n'.join(paragraph), None, f'lines:{start}-{number-1}'))
                paragraph = []
    elif suffix == '.pdf':
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise RuntimeError('PDF_DEPENDENCY_MISSING: install requirements-local.txt') from exc
        reader = PdfReader(io.BytesIO(raw))
        if reader.is_encrypted: raise ValueError('ENCRYPTED_PDF_UNSUPPORTED')
        if len(reader.pages) > 100: raise ValueError('PDF_PAGE_LIMIT')
        for page, value in enumerate(reader.pages, 1):
            text = value.extract_text() or ''
            if text.strip(): passages.append(Passage(text.strip(), page, f'page:{page}'))
    elif suffix == '.docx':
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            info = archive.getinfo('word/document.xml')
            if info.file_size > MAX_TEXT_BYTES: raise ValueError('DOCX_XML_TOO_LARGE')
            raw = archive.read(info)
        if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
            raise ValueError('DOCX_DTD_FORBIDDEN')
        document = ET.fromstring(raw)
        ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        for number, paragraph in enumerate(document.findall('.//w:p', ns), 1):
            text = ''.join(n.text or '' for n in paragraph.findall('.//w:t', ns)).strip()
            if text: passages.append(Passage(text, None, f'paragraph:{number}'))
    else:
        raise ValueError('UNSUPPORTED_FORMAT')
    if sum(len(p.text.encode('utf-8')) for p in passages) > MAX_TEXT_BYTES:
        raise ValueError('EXTRACTED_TEXT_TOO_LARGE')
    if not passages: raise ValueError('NO_EXTRACTABLE_TEXT')
    # Bound excerpts without losing their page/paragraph/line provenance.
    result = []
    for passage in passages:
        for start in range(0, len(passage.text), 1000):
            text = passage.text[start:start+1000]
            if text.strip(): result.append(Passage(text, passage.page, f'{passage.locator};chars:{start}-{start+len(text)}'))
    if len(result) > 2000: raise ValueError('CHUNK_LIMIT')
    return result
