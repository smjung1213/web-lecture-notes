"""Freeze an already rendered web handoff. Never render, execute package code or publish."""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import io
import json
import os
import shutil
import stat
import tempfile
import unicodedata
import zipfile

ROLES = ('notes', 'workbook')
RENDER_FILES = ('render.py', 'css_resources.py', 'typeset.cjs', 'requirements.txt',
                'package.json', 'package-lock.json')
REQUIRED = ('notes.html', 'workbook.html', 'lecture.css', 'input-contract.json',
            'source-inventory.md', 'coverage.md', 'production-note.md')
OPTIONAL = ('local.css', 'qa-summary.md', 'resume-note.md',
            'asset-manifest.json', 'calculations.json')
MAX_BYTES = 512 * 1024 * 1024


def digest(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()


def safe_name(name):
    p = PurePosixPath(name)
    if (not name or p.is_absolute() or '..' in p.parts or '\\' in name or ':' in name
            or name != p.as_posix() or unicodedata.normalize('NFC', name) != name):
        raise ValueError(f'UNSAFE_PACKAGE_PATH: {name}')
    return name


def pdf_info(data):
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(data))
    if reader.is_encrypted or not len(reader.pages):
        raise ValueError('UNSUPPORTED_PDF')
    return {'sha256': digest(data), 'bytes': len(data), 'pages': len(reader.pages)}


def read_regular(path):
    path = Path(path)
    if not stat.S_ISREG(path.lstat().st_mode):
        raise ValueError(f'REGULAR_FILE_REQUIRED: {path}')
    return path.read_bytes()


def load_archive(path):
    entries = {}
    with zipfile.ZipFile(path) as z:
        if len(z.infolist()) > 10000 or sum(i.file_size for i in z.infolist()) > MAX_BYTES:
            raise ValueError('PACKAGE_TOO_LARGE')
        seen = set()
        for i in z.infolist():
            if i.is_dir():
                continue
            name = safe_name(i.filename)
            if name.casefold() in seen or i.flag_bits & 1:
                raise ValueError('DUPLICATE_OR_ENCRYPTED_MEMBER')
            if stat.S_IFMT(i.external_attr >> 16) not in (0, stat.S_IFREG):
                raise ValueError('NON_REGULAR_MEMBER')
            seen.add(name.casefold())
            entries[name] = z.read(i)
    return entries


def validate(entries):
    """Check captured bytes, not the installed renderer/font environment."""
    m = json.loads(entries['delivery-manifest.json'])
    if m.get('handoff_version') != 1 or set(m['documents']) != set(ROLES):
        raise ValueError('HANDOFF_MANIFEST_INVALID')
    expected = m['files']
    if set(expected) != set(entries) - {'delivery-manifest.json'}:
        raise ValueError('PACKAGE_FILE_SET_CHANGED')
    for name, h in expected.items():
        safe_name(name)
        if digest(entries[name]) != h:
            raise ValueError(f'PACKAGE_BYTES_CHANGED: {name}')
    for role in ROLES:
        row = m['documents'][role]
        pdf = entries[safe_name(row['file'])]
        if any(row[k] != v for k, v in pdf_info(pdf).items()):
            raise ValueError(f'PDF_RECORD_CHANGED: {role}')
        receipt = json.loads(entries[safe_name(row['receipt'])])
        if (receipt.get('render_receipt_version') != 1 or receipt.get('source_name') != role + '.html'
                or receipt.get('pdf_sha256') != digest(pdf) or receipt.get('pages') != row['pages']
                or receipt.get('prepared_sha256') != digest(entries[role + '.html'])):
            raise ValueError(f'RENDER_PAIR_MISMATCH: {role}')
        resources = receipt.get('resources')
        if not isinstance(resources, dict) or not resources:
            raise ValueError('RENDER_RESOURCES_MISSING')
        for name, h in resources.items():
            if digest(entries[safe_name(name)]) != h:
                raise ValueError(f'RENDER_RESOURCE_CHANGED: {name}')
        identities = receipt['toolchain']['files']
        for name in RENDER_FILES:
            if digest(entries['rebuild/' + name]) != identities[name]:
                raise ValueError(f'RENDERER_BYTES_CHANGED: {name}')
    return m


def build(source, pdfs, output, revision, prefix, status='draft', include=()):
    source, output = Path(source).resolve(), Path(output).absolute()
    if not revision.strip() or status not in ('draft', 'web-reviewed'):
        raise ValueError('HANDOFF_LABEL_REQUIRED')
    safe_name(prefix)
    if '/' in prefix or not prefix.strip():
        raise ValueError('FILE_PREFIX_REQUIRED')
    if os.path.lexists(output) or output.resolve().is_relative_to(source):
        raise ValueError('NEW_OUTPUT_OUTSIDE_SOURCE_REQUIRED')
    entries = {}
    for name in REQUIRED + OPTIONAL:
        p = source / name
        if name in REQUIRED or p.exists():
            entries[name] = read_regular(p)
    for folder in ('assets', 'practice'):
        base = source / folder
        if base.is_symlink():
            raise ValueError('SYMLINK_DIRECTORY')
        if base.exists():
            for p in sorted(base.rglob('*')):
                if p.is_symlink():
                    raise ValueError('SYMLINK_RESOURCE')
                if p.is_file():
                    name = safe_name(p.relative_to(source).as_posix())
                    if any(x in p.parts for x in ('__pycache__', 'node_modules', '.git', 'private')):
                        raise ValueError('UNSUPPORTED_RESOURCE_DIRECTORY')
                    entries[name] = read_regular(p)
    for name in include:
        safe_name(name)
        p = source / name
        if not p.resolve().is_relative_to(source) or p.suffix.lower() == '.pdf' or name in entries or name.startswith('rebuild/') or name in ('delivery-manifest.json', 'REBUILD.md'):
            raise ValueError('EXTRA_FILE_CONFLICT_OR_BOUNDARY')
        entries[name] = read_regular(p)
    # Use the actual renderer shipped with the source, or the managed six files.
    for name in RENDER_FILES:
        p = source / 'rebuild' / name
        entries['rebuild/' + name] = read_regular(p if p.exists() else Path(__file__).with_name(name))
    documents = {}
    for role, label in zip(ROLES, ('학습노트', '연습문제')):
        pdf_path = Path(pdfs[role])
        name = f'pdfs/{prefix} {label}.pdf'
        entries[name] = read_regular(pdf_path)
        receipt_name = name + '.render.json'
        entries[receipt_name] = read_regular(pdf_path.with_name(pdf_path.name + '.render.json'))
        documents[role] = {'file': name, 'receipt': receipt_name, **pdf_info(entries[name])}
    entries['REBUILD.md'] = (
        'These PDFs are the frozen web handoff, not local review approval.\n'
        'Reuse verified WeasyPrint 70.0 / Python and MathJax environments; do not reinstall unnecessarily.\n'
        'A receipt with renderer_mode "draft" came from the preinstalled WeasyPrint 68.0; re-render with 70.0 for an official PDF.\n'
        'If unavailable, follow the managed references/runtime.md offline attachment path; internet installation is not assumed.\n'
        'The wheel attachment and system fonts/Node/MathJax are not bundled in this edit ZIP.\n'
        'Record the Python executable, isolated PYTHONPATH/-B -S and MATHJAX_MODULE_ROOT in production-note.md.\n'
        'For new v3.4 notes, verify with fc-list: Noto Serif CJK KR, Noto Sans CJK KR, Noto Sans Mono CJK KR.\n'
        'If any required font is missing, report rendering incomplete; do not silently substitute.\n'
        'Keep the bundled CSS and renderer/font contract for existing notes.\n'
        'From the extracted root, render a NEW candidate with:\n'
        'python rebuild/render.py notes.html /new/path/notes.pdf\n'
        'python rebuild/render.py workbook.html /new/path/workbook.pdf\n'
        'A new render may have a different hash. Keep the received PDFs unchanged.\n').encode()
    if sum(map(len, entries.values())) > MAX_BYTES:
        raise ValueError('PACKAGE_TOO_LARGE')
    for name in entries:
        safe_name(name)
    if len({n.casefold() for n in entries}) != len(entries):
        raise ValueError('DUPLICATE_PACKAGE_PATH')
    manifest = {'handoff_version': 1, 'revision': revision, 'status': status,
                'semantic_review_complete': False, 'documents': documents,
                'files': {n: digest(b) for n, b in entries.items()}}
    entries['delivery-manifest.json'] = json_bytes(manifest)
    validate(entries)
    # Validate the exact frozen HTML/resources in an isolated staging directory.
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.handoff-', dir=output.parent) as tmp:
        stage = Path(tmp) / 'package'
        stage.mkdir()
        for name, data in entries.items():
            p = stage / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
        from render import check
        for role in ROLES:
            check(stage / f'{role}.html')
        ready = Path(tmp) / 'delivery'
        ready.mkdir()
        archive = ready / f'{prefix} 편집본.zip'
        with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED) as z:
            for name, data in entries.items():
                z.writestr(name, data)
        validate(load_archive(archive))
        for row in documents.values():
            (ready / Path(row['file']).name).write_bytes(entries[row['file']])
        receipt = {'revision': revision, 'status': status, 'documents': documents,
                   'zip': {'file': archive.name, 'sha256': digest(archive.read_bytes())},
                   'downloads': {p.name: digest(p.read_bytes()) for p in ready.iterdir()}}
        (ready / 'delivery.json').write_bytes(json_bytes(receipt))
        # Output is not exposed until every byte check passes. Existing targets are refused.
        output.mkdir()
        try:
            for p in ready.iterdir():
                shutil.copyfile(p, output / p.name)
            validate(load_archive(output / archive.name))
            for row in documents.values():
                if (output / Path(row['file']).name).read_bytes() != entries[row['file']]:
                    raise ValueError('DOWNLOAD_COPY_CHANGED')
        except BaseException:
            shutil.rmtree(output)
            raise
    return receipt


def inspect_received(root, pdfs):
    """Measure received files; a byte difference alone does not prove manuscript change."""
    root = Path(root)
    try:
        m = json.loads((root / 'delivery-manifest.json').read_text())
        if not isinstance(m, dict):
            m = {}
    except (FileNotFoundError, ValueError):
        m = {}
    binding = {'status': 'UNVERIFIED', 'reason': 'Legacy or absent handoff manifest; inspect content/receipts separately.'}
    if m.get('handoff_version') == 1:
        try:
            names = m['files']
            if not isinstance(names, dict) or len(names) > 10000:
                raise ValueError('MANIFEST_FILE_SET_INVALID')
            entries = {'delivery-manifest.json': (root / 'delivery-manifest.json').read_bytes()}
            for name in names:
                p = root / safe_name(name)
                if not p.resolve().is_relative_to(root.resolve()):
                    raise ValueError('PACKAGE_PATH_BOUNDARY')
                if sum(map(len, entries.values())) + p.stat().st_size > MAX_BYTES:
                    raise ValueError('PACKAGE_TOO_LARGE')
                entries[name] = read_regular(p)
            validate(entries)
            binding = {'status': 'VERIFIED', 'revision': m.get('revision'),
                       'meaning': 'Captured HTML/resources/renderer/PDF receipt bytes match; no semantic approval.'}
        except (OSError, ValueError, KeyError, TypeError) as e:
            binding = {'status': 'INVALID', 'reason': str(e)}
    result = {}
    for role in ROLES:
        actual = pdf_info(Path(pdfs[role]).read_bytes())
        records = m.get('documents', m.get('pdfs', {}))
        row = records.get(role, {}) if isinstance(records, dict) else {}
        if not isinstance(row, dict):
            row = {}
        expected = row.get('sha256')
        if not isinstance(expected, str):
            expected = None
        candidates = []
        named = row.get('file') or row.get('name')
        if isinstance(named, str):
            try:
                safe_name(named)
                candidates = [root / named, root / 'pdfs' / named]
            except ValueError:
                pass
        candidates = [p for p in candidates if p.is_file() and p.resolve().is_relative_to(root.resolve())]
        if not candidates:
            label = '학습노트' if role == 'notes' else '연습문제'
            candidates = [p for p in root.rglob('*.pdf') if p.name in (role + '.pdf',) or p.name.endswith(label + '.pdf')]
        # Do not choose the first of conflicting same-role PDFs.
        embedded = [{'path': str(p), **pdf_info(p.read_bytes())} for p in sorted(set(candidates))]
        hashes = {p['sha256'] for p in embedded}
        if len(hashes) > 1:
            state = 'AMBIGUOUS_EMBEDDED_PDFS'
        elif hashes:
            state = 'BYTE_MATCH' if actual['sha256'] in hashes else 'BYTE_DIFFERENT'
        elif isinstance(expected, str) and len(expected) == 64:
            state = 'MANIFEST_HASH_MATCH' if actual['sha256'] == expected else 'BYTE_DIFFERENT'
        else:
            state = 'UNVERIFIED'
        result[role] = {'received': {'path': str(pdfs[role]), **actual}, 'embedded': embedded,
                        'manifest_sha256': expected, 'status': state,
                        'manifest_matches_embedded': expected in hashes if hashes and expected else None}
    return {'roles': result, 'package_binding': binding, 'meaning': 'Byte identity only; differences need content comparison. No manuscript or review approval.'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--notes-pdf', required=True, type=Path)
    p.add_argument('--workbook-pdf', required=True, type=Path)
    p.add_argument('--revision', required=True)
    p.add_argument('--file-prefix', required=True, help='Example: 수치해석 4주차')
    p.add_argument('--status', choices=('draft', 'web-reviewed'), default='draft')
    p.add_argument('--include', action='append', default=[], help='Additional required file relative to source, e.g. practice_week4.py')
    a = p.parse_args()
    try:
        print(json.dumps(build(a.source, {'notes': a.notes_pdf, 'workbook': a.workbook_pdf},
                               a.output, a.revision, a.file_prefix, a.status, a.include), ensure_ascii=False, indent=2))
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as e:
        p.exit(1, f'Handoff stopped: {e}\n')


if __name__ == '__main__':
    main()
