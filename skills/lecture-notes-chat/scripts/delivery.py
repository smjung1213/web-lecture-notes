"""Freeze the web edit handoff: HTML, CSS, assets and records in one ZIP.

Standard library only and self-contained: the web needs no other script file.
The web creates no PDF: local lecture-week renders the handoff with WeasyPrint
70.0 first. Never render, execute package code or publish.
Legacy handoff_version 1 packages (with PDFs) are still inspected for local review."""
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse, unquote
import argparse
import hashlib
import io
import json
import os
import re
import shutil
import stat
import tempfile
import unicodedata
import zipfile

ROLES = ('notes', 'workbook')
HANDOFF_VERSION = 2
# Legacy v1 packages carried the renderer that made their PDFs.
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


def validate_v1(entries):
    """Legacy (<=0.6.x) handoff with PDFs: check captured bytes, not the installed environment."""
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


def validate(entries):
    """Current handoff: exact file set and bytes, both manuscripts, no PDF."""
    m = json.loads(entries['delivery-manifest.json'])
    if m.get('handoff_version') == 1:
        return validate_v1(entries)
    if m.get('handoff_version') != HANDOFF_VERSION or set(m.get('manuscripts', {})) != set(ROLES):
        raise ValueError('HANDOFF_MANIFEST_INVALID')
    expected = m['files']
    if set(expected) != set(entries) - {'delivery-manifest.json'}:
        raise ValueError('PACKAGE_FILE_SET_CHANGED')
    for name, h in expected.items():
        safe_name(name)
        if name.lower().endswith('.pdf'):
            raise ValueError(f'PDF_NOT_PART_OF_WEB_HANDOFF: {name}')
        if digest(entries[name]) != h:
            raise ValueError(f'PACKAGE_BYTES_CHANGED: {name}')
    for role in ROLES:
        if m['manuscripts'][role] != {'file': role + '.html', 'sha256': expected.get(role + '.html')}:
            raise ValueError(f'MANUSCRIPT_RECORD_CHANGED: {role}')
    return m


class Manuscript(HTMLParser):
    """Counts editable math sources; the stdlib parser keeps the web free of bs4."""
    def __init__(self):
        super().__init__()
        self.math = 0

    def handle_starttag(self, tag, attrs):
        if any(k == 'data-latex' for k, _ in attrs):
            self.math += 1


# References, local_resource and css_resources are copies of the local renderer's
# render.References, render.local_resource and css_resources.css_resources, so the
# web downloads only this file. test_web_delivery keeps the copies identical.
class References(HTMLParser):
    def __init__(self):
        super().__init__()
        self.resources, self.links, self.errors, self.styles = [], [], [], []
        self.ids = set()
        self.in_style = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get('id'):
            if a['id'] in self.ids:
                self.errors.append(f"Duplicate id: {a['id']}")
            self.ids.add(a['id'])
        if tag == 'a' and (a.get('href') or '').startswith('#'):
            self.links.append(unquote(a['href'][1:]))
        if tag in ('img', 'source'):
            if tag == 'img' and not a.get('src'):
                self.errors.append('Image has no src')
            if a.get('src'):
                self.resources.append(a['src'])
            if a.get('srcset'):
                self.errors.append('Use one explicit bundled src instead of srcset')
        if tag == 'link' and 'stylesheet' in (a.get('rel') or '').split():
            self.resources.append(a.get('href', ''))
        if tag in ('script', 'base', 'iframe', 'object', 'embed'):
            self.errors.append(f'Unsupported active/base element: {tag}')
        if any(k.lower().startswith('on') for k in a):
            self.errors.append('Inline event handlers are unsupported')
        if 'style' in a:
            if a['style'] is None:
                self.errors.append('Empty style attribute')
            else:
                self.styles.append(a['style'])
        if tag == 'style':
            self.in_style = True

    def handle_endtag(self, tag):
        if tag == 'style':
            self.in_style = False

    def handle_data(self, data):
        if self.in_style:
            self.styles.append(data)


def local_resource(url, root):
    parsed = urlparse(url)
    if parsed.scheme == 'data':
        return None
    if parsed.scheme != 'file' or parsed.netloc not in ('', 'localhost'):
        raise ValueError(f'Use a bundled local resource, not: {url}')
    path = Path(unquote(parsed.path)).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f'Resource outside authored package: {path}')
    if not path.is_file():
        raise FileNotFoundError(f'Missing resource: {path}')
    return path


def css_resources(text):
    import tinycss2
    def walk(tokens):
        for token in tokens:
            if token.type == 'url':
                yield token.value
            elif token.type == 'function' and token.lower_name == 'url':
                values = [t for t in token.arguments if t.type not in ('whitespace', 'comment')]
                if len(values) != 1 or values[0].type != 'string':
                    raise ValueError('Malformed CSS url()')
                yield values[0].value
            elif hasattr(token, 'content') and token.content is not None:
                yield from walk(token.content)
            elif hasattr(token, 'arguments'):
                yield from walk(token.arguments)
    rules = tinycss2.parse_stylesheet(text, skip_comments=True, skip_whitespace=True)
    for rule in rules:
        if rule.type == 'at-rule' and rule.lower_at_keyword == 'import':
            values = [t for t in rule.prelude if t.type not in ('whitespace', 'comment')]
            if values and values[0].type == 'string':
                yield values[0].value
        yield from walk(getattr(rule, 'prelude', []))
        yield from walk(getattr(rule, 'content', None) or [])
    # Inline declarations also appear as parser error tokens; scan their components.
    yield from walk(tinycss2.parse_component_value_list(text))


CSS_COMMENT = re.compile(r'/\*.*?\*/', re.S)
CSS_URL = re.compile(r"""url\(\s*(?:"([^"]*)"|'([^']*)'|([^)'"\s]+))\s*\)""", re.I)
CSS_IMPORT = re.compile(r"""@import\s+(?:"([^"]*)"|'([^']*)')""", re.I)


def css_references(text):
    """url() and @import targets. Uses the managed tinycss2 parser when installed;
    the web runtime may lack it, so a standard-library scan is the fallback."""
    try:
        import tinycss2  # noqa: F401
    except ImportError:
        text = CSS_COMMENT.sub(' ', text)
        found = [next(g for g in m.groups() if g is not None) for m in CSS_URL.finditer(text)]
        found += [next(g for g in m.groups() if g is not None) for m in CSS_IMPORT.finditer(text)]
        return found, 'stdlib'
    return list(css_resources(text)), 'tinycss2'


def html_check(path):
    """Same local boundary as render.check_text, without bs4, tinycss2 or the renderer.

    Ids, internal links, active elements and every referenced CSS/image (also
    inside CSS) must be bundled. Page-note markup and math conversion are
    checked by the local WeasyPrint 70.0 render."""
    from urllib.parse import urljoin
    path = Path(path).resolve()
    text = path.read_text(encoding='utf-8')
    parser = References()
    parser.feed(text)
    for target in parser.links:
        if target and target not in parser.ids:
            parser.errors.append(f'Missing internal link target: #{target}')
    if parser.errors:
        raise ValueError(f'HTML_CHECK_FAILED: {path.name}: ' + '; '.join(parser.errors))
    seen, parsers = set(), set()
    def references(css):
        found, used = css_references(css)
        parsers.add(used)
        return found
    def inspect(resource, base):
        p = local_resource(urljoin(base, resource), path.parent)
        if p is None or p in seen:
            return
        seen.add(p)
        if p.suffix.lower() == '.css':
            for item in references(p.read_text(encoding='utf-8')):
                inspect(item, p.as_uri())
    try:
        for item in parser.resources:
            inspect(item, path.as_uri())
        for style in parser.styles:
            for item in references(style):
                inspect(item, path.as_uri())
    except (ValueError, FileNotFoundError) as e:
        raise ValueError(f'HTML_CHECK_FAILED: {path.name}: {e}') from e
    math = Manuscript()
    math.feed(text)
    return {'resources': len(seen), 'ids': len(parser.ids), 'internal_links': len(parser.links),
            'math_sources': math.math, 'css_parser': '+'.join(sorted(parsers)) or 'none'}


def build(source, output, revision, prefix, status='draft', include=()):
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
                    if any(x in p.relative_to(source).parts for x in ('__pycache__', 'node_modules', '.git', 'private')):
                        raise ValueError('UNSUPPORTED_RESOURCE_DIRECTORY')
                    if p.suffix.lower() == '.pdf':
                        raise ValueError(f'PDF_NOT_PART_OF_WEB_HANDOFF: {name}')
                    entries[name] = read_regular(p)
    for name in include:
        safe_name(name)
        p = source / name
        if (not p.resolve().is_relative_to(source) or p.suffix.lower() == '.pdf' or name in entries
                or name == 'delivery-manifest.json'):
            raise ValueError('EXTRA_FILE_CONFLICT_OR_BOUNDARY')
        entries[name] = read_regular(p)
    if sum(map(len, entries.values())) > MAX_BYTES:
        raise ValueError('PACKAGE_TOO_LARGE')
    if len({n.casefold() for n in entries}) != len(entries):
        raise ValueError('DUPLICATE_PACKAGE_PATH')
    files = {n: digest(b) for n, b in entries.items()}
    manifest = {'handoff_version': HANDOFF_VERSION, 'revision': revision, 'status': status,
                'semantic_review_complete': False, 'pdf': 'none; local lecture-week renders with WeasyPrint 70.0',
                'manuscripts': {role: {'file': role + '.html', 'sha256': files[role + '.html']} for role in ROLES},
                'files': files}
    entries['delivery-manifest.json'] = json_bytes(manifest)
    validate(entries)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.handoff-', dir=output.parent) as tmp:
        # Check the exact frozen HTML/resources in an isolated staging directory.
        stage = Path(tmp) / 'package'
        stage.mkdir()
        for name, data in entries.items():
            p = stage / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
        checks = {role: html_check(stage / f'{role}.html') for role in ROLES}
        ready = Path(tmp) / 'delivery'
        ready.mkdir()
        archive = ready / f'{prefix} 편집본.zip'
        with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED) as z:
            for name, data in entries.items():
                z.writestr(name, data)
        validate(load_archive(archive))
        data = archive.read_bytes()
        receipt = {'revision': revision, 'status': status, 'handoff_version': HANDOFF_VERSION,
                   'zip': {'file': archive.name, 'sha256': digest(data), 'bytes': len(data)},
                   'html_checks': checks, 'files': len(entries)}
        (ready / 'delivery.json').write_bytes(json_bytes(receipt))
        # Output is not exposed until every byte check passes. Existing targets are refused.
        output.mkdir()
        try:
            for p in ready.iterdir():
                shutil.copyfile(p, output / p.name)
            if digest((output / archive.name).read_bytes()) != receipt['zip']['sha256']:
                raise ValueError('DELIVERY_COPY_CHANGED')
            validate(load_archive(output / archive.name))
        except BaseException:
            shutil.rmtree(output)
            raise
    return receipt


def inspect_received(root, pdfs, baseline=False):
    """Measure received files; a byte difference alone does not prove manuscript change.

    baseline=True: the PDFs were rendered locally from this package (no web PDF)."""
    root = Path(root)
    try:
        m = json.loads((root / 'delivery-manifest.json').read_text())
        if not isinstance(m, dict):
            m = {}
    except (FileNotFoundError, ValueError):
        m = {}
    binding = {'status': 'UNVERIFIED', 'reason': 'Legacy or absent handoff manifest; inspect content/receipts separately.'}
    if m.get('handoff_version') in (1, HANDOFF_VERSION):
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
            binding = {'status': 'VERIFIED', 'revision': m.get('revision'), 'handoff_version': m['handoff_version'],
                       'meaning': ('Captured HTML/resources/renderer/PDF receipt bytes match; no semantic approval.'
                                   if m['handoff_version'] == 1 else
                                   'Captured HTML/CSS/assets/records bytes match; no PDF, no semantic approval.')}
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
        elif baseline:
            state = 'LOCAL_BASELINE'
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
    p.add_argument('--revision', required=True)
    p.add_argument('--file-prefix', required=True, help='Example: 수치해석 4주차')
    p.add_argument('--status', choices=('draft', 'web-reviewed'), default='draft')
    p.add_argument('--include', action='append', default=[], help='Additional required file relative to source, e.g. practice_week4.py')
    a = p.parse_args()
    try:
        print(json.dumps(build(a.source, a.output, a.revision, a.file_prefix, a.status, a.include),
                         ensure_ascii=False, indent=2))
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as e:
        p.exit(1, f'Handoff stopped: {e}\n')


if __name__ == '__main__':
    main()
