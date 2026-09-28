"""Validate bundled HTML resources and render a new PDF. No model or network calls."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlparse, unquote, urljoin
import argparse
import logging
import os
import subprocess
import sys
import tempfile
import json
import hashlib
import re


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


# The managed engine loads this file through an internal symlink; resolve its
# owner so direct CLI, package imports and standalone rebuild share one parser.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from css_resources import css_resources


def check(source, *, ready=False):
    source = Path(source).resolve()
    if not source.is_file() or source.suffix.lower() not in ('.html', '.htm'):
        raise ValueError('Input must be an existing HTML file')
    text = source.read_text(encoding='utf-8')
    result = check_text(text, source)
    if ready and math_nodes(text):
        versions = {n.get('data-math-renderer') for n in math_nodes(text)}
        if versions - {None, MATH_RENDERER}:
            raise ValueError('MATH_RENDERER_CHANGED: preserve old revision; prepare a new copy with the managed renderer, then render and inspect the final PDF')
        prepared = prepare_html(source)
        if math_signature(text) != math_signature(prepared):
            raise ValueError('Math cache is absent/stale; prepare the HTML before delivery')
        result['math_cache'] = 'REGENERATED_AND_MATCHED'
    return result


def check_text(text, source):
    root = source.parent
    parser = References()
    parser.feed(text)
    for target in parser.links:
        if target and target not in parser.ids:
            parser.errors.append(f'Missing internal link target: #{target}')
    if parser.errors:
        raise ValueError('\n'.join(parser.errors))
    seen = set()
    def inspect(resource, base):
        p = local_resource(urljoin(base, resource), root)
        if p is None or p in seen:
            return
        seen.add(p)
        if p.suffix.lower() == '.css':
            for item in css_resources(p.read_text(encoding='utf-8')):
                inspect(item, p.as_uri())
    for item in parser.resources:
        inspect(item, source.as_uri())
    for style in parser.styles:
        for item in css_resources(style):
            inspect(item, source.as_uri())
    return {'html': str(source), 'resources': len(seen), 'ids': len(parser.ids),
            'internal_links': len(parser.links), 'math_source_count': len(math_nodes(text)),
            'math_cache': 'NOT_CHECKED'}



MATH_RENDERER = 'mathjax-3.2.1-svg-base-ams-v2'


def math_nodes(text):
    """LaTeX in data-latex is the only editable formula source; children are caches."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(text, 'html.parser')
    nodes = soup.select('[data-latex]')
    for n in nodes:
        classes = n.get('class', [])
        expected = 'span' if 'math-inline' in classes else 'div' if 'math-display' in classes else None
        if n.name != expected or ('math-inline' in classes and 'math-display' in classes):
            raise ValueError('Use span.math-inline or div.math-display with data-latex')
        if not n['data-latex'].strip() or n.select('[data-latex]'):
            raise ValueError('Empty/nested math source')
        latex = n['data-latex'].strip()
        if (latex.startswith('$$') or latex.endswith('$$') or latex.startswith('\\[') or latex.endswith('\\]')
                or latex.startswith('\\(') or latex.endswith('\\)')
                or (latex.startswith('$') and not latex.startswith('\\$'))
                or (latex.endswith('$') and not latex.endswith('\\$'))):
            raise ValueError('Remove outer TeX delimiters from data-latex')
        if n.get('data-math-renderer') is None and n.decode_contents().strip():
            raise ValueError('Keep explanations outside math; unprepared math must be empty')
        if n.get('data-math-renderer') is not None:
            from bs4 import Tag
            for child in n.contents:
                if isinstance(child, Tag):
                    if child.name != 'span' or not set(child.get('class', [])).intersection({'math-visual', 'math-assistive'}):
                        raise ValueError('Prepared math children must be generated caches; keep explanations outside math')
                elif str(child).strip():
                    raise ValueError('Text inside prepared math would be lost; move explanations outside math')
    for n in soup.select('.math-inline, .math-display'):
        if 'data-latex' not in n.attrs:
            raise ValueError('Math element has no data-latex source')
    return nodes


def math_signature(text):
    # Structural cache comparison ignores attribute ordering only, not path geometry.
    return [str(n) for n in math_nodes(text)]



def inline_table_rules(svg):
    """MathJax 3.2.1 SVGmtable CSS, in SVG user units (1000/em).

    setLineThickness emits stroke-thickness, which SVG does not understand;
    bridge it to stroke-width, preserving the supplied custom dash lengths.
    Only generated table rules are touched; glyphs/boxed/matrix paths are not.
    """
    for rule in svg.select('line[data-line], rect[data-frame]'):
        rule['stroke'] = rule.get('stroke', 'currentColor')
        rule['stroke-width'] = rule.get('stroke-width', rule.get('stroke-thickness', '70'))
        rule['fill'] = 'none'
        classes = rule.get('class', [])
        if 'mjx-dotted' in classes:
            rule['stroke-linecap'] = rule.get('stroke-linecap', 'round')
            rule['stroke-dasharray'] = rule.get('stroke-dasharray', '0,140')
        elif 'mjx-dashed' in classes:
            rule['stroke-dasharray'] = rule.get('stroke-dasharray', '140')


def prepare_html(source):
    """Always regenerate caches from LaTeX. No author JS, network or font download."""
    from bs4 import BeautifulSoup
    source = Path(source).resolve()
    check(source)
    text = source.read_text(encoding='utf-8')
    nodes = math_nodes(text)
    if not nodes:
        return text  # Legacy/non-math documents remain usable; no silent conversion.
    payload = [{'latex': n['data-latex'], 'display': 'math-display' in n['class']} for n in nodes]
    result = subprocess.run(
        ['node', str(Path(__file__).resolve().with_name('typeset.cjs'))],
        input=json.dumps(payload, ensure_ascii=False), text=True, encoding='utf-8',
        capture_output=True, timeout=120, check=False)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or 'MathJax conversion failed')
    converted = json.loads(result.stdout)
    if converted.get('renderer') != MATH_RENDERER or len(converted.get('expressions', [])) != len(nodes):
        raise RuntimeError('Unexpected MathJax conversion result')
    soup = BeautifulSoup(text, 'html.parser')
    for n, item, original in zip(soup.select('[data-latex]'), converted['expressions'], payload):
        fragment = BeautifulSoup(item['html'], 'html.parser')
        svg = fragment.find('svg')
        mml = BeautifulSoup(item['mathml'], 'html.parser').find('math')
        if not svg or not mml:
            raise RuntimeError('Incomplete SVG/MathML conversion')
        # SVG presentation + hidden semantic MathML in HTML. This is not PDF/UA.
        inline_table_rules(svg)
        svg['aria-hidden'] = 'true'
        svg.attrs.pop('role', None)
        n.clear()
        visual = soup.new_tag('span', attrs={'class': 'math-visual', 'aria-hidden': 'true'})
        visual.append(svg)
        assistive = soup.new_tag('span', attrs={'class': 'math-assistive'})
        assistive.append(mml)
        n.append(visual); n.append(assistive)
        n['data-math-renderer'] = MATH_RENDERER
        n['data-math-sha256'] = hashlib.sha256(json.dumps(
            original, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    # Embedded critical math CSS makes prepared HTML independently viewable.
    style = soup.find('style', id='static-math-style')
    if style:
        style.decompose()
    style = soup.new_tag('style', id='static-math-style')
    style.string = MATH_STYLE
    if not soup.head:
        raise ValueError('Prepared HTML requires a head element')
    soup.head.append(style)
    prepared = str(soup)
    check_text(prepared, source)
    return prepared


MATH_STYLE = """
.math-inline { white-space: nowrap; }
.math-display { margin: 3mm 0; text-align: left; break-inside: avoid; }
.math-visual { display: inline; }
.math-visual svg { overflow: visible; max-width: none; }
.math-assistive { position: absolute; width: 1px; height: 1px; padding: 0;
  overflow: hidden; clip: rect(1px,1px,1px,1px); white-space: nowrap; }
@media print { .math-assistive { display: none; } }
"""


def prepare(source, output):
    source, output = Path(source).resolve(), Path(output).absolute()
    if output.suffix.lower() not in ('.html', '.htm'):
        raise ValueError('Prepared output must be HTML')
    data = prepare_html(source)
    # If moved, CSS/assets must already exist at their relative destination paths.
    check_text(data, output)
    save_new(output, data.encode('utf-8'))
    print(f'Prepared {output}; SVG/MathML caches derived from editable LaTeX.')


DEFAULT_FONTS = ['Noto Sans CJK KR', 'Noto Sans Mono CJK KR']


def check_fonts(families):
    identities = {}
    for family in families:
        result = subprocess.run(['fc-match', '-f', '%{family}', family],
                                text=True, capture_output=True, check=True, timeout=10)
        found = [s.strip().casefold() for s in result.stdout.split(',')]
        if family.casefold() not in found:
            raise RuntimeError(f'Required font unavailable: {family} (matched {result.stdout})')
        files = subprocess.run(['fc-match', '-f', '%{file}', family], text=True, capture_output=True, check=True, timeout=10)
        identities[family] = hashlib.sha256(Path(files.stdout).read_bytes()).hexdigest()
    return identities



def renderer_identity(source, fonts=None):
    """Byte identity of executable inputs plus the actual installed dependencies."""
    from importlib.metadata import version
    scripts = Path(__file__).resolve().parent
    identity = {'files': {name: hashlib.sha256((scripts/name).read_bytes()).hexdigest()
                         for name in ('render.py', 'css_resources.py', 'typeset.cjs',
                                      'requirements.txt', 'package.json', 'package-lock.json')},
                'python_packages': {name: version(name) for name in ('weasyprint', 'beautifulsoup4', 'tinycss2')},
                'fonts': check_fonts(fonts or DEFAULT_FONTS)}
    if math_nodes(Path(source).read_text(encoding='utf-8')):
        result = subprocess.run(['node', str(scripts/'typeset.cjs'), '--identity'],
                                capture_output=True, text=True, check=True, timeout=120)
        identity['mathjax'] = json.loads(result.stdout)
    return identity


def save_new(output, data):
    """Link a complete same-directory temporary file to a new name; never replace."""
    output = Path(output).absolute()
    if os.path.lexists(output):
        raise FileExistsError(f'Choose a new output file: {output}')
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.render-', dir=output.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, output)
    finally:
        os.unlink(temporary)


def render(source, output, fonts=None):
    source, output = Path(source).resolve(), Path(output).absolute()
    if output.suffix.lower() != '.pdf':
        raise ValueError('Output must have a .pdf extension')
    receipt_path = output.with_name(output.name + '.render.json')
    if os.path.lexists(output) or os.path.lexists(receipt_path):
        raise FileExistsError(f'Choose a new output file and receipt: {output}')
    source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    identity = renderer_identity(source, fonts)
    prepared = prepare_html(source)
    # Homebrew's shared libraries are not on macOS's default loader path.
    if sys.platform == 'darwin' and Path('/opt/homebrew/lib/libgobject-2.0.dylib').exists():
        os.environ.setdefault('DYLD_FALLBACK_LIBRARY_PATH', '/opt/homebrew/lib')
    try:
        from weasyprint import HTML, URLFetcher
    except (ImportError, OSError) as exc:
        raise RuntimeError('WeasyPrint or its native libraries are unavailable; no PDF created') from exc
    failed = []
    resources = {}
    class ResourceErrors(logging.Handler):
        def emit(self, record):
            message = record.getMessage()
            if record.levelno >= logging.ERROR or 'Font-face' in message or 'font cannot' in message.lower():
                failed.append(message)
    handler = ResourceErrors()
    logger = logging.getLogger('weasyprint')
    class LocalFetcher(URLFetcher):
        def fetch(self, url, headers=None):
            try:
                local = local_resource(url, source.parent)
                if local is not None:
                    resources[str(local.relative_to(source.parent))] = hashlib.sha256(local.read_bytes()).hexdigest()
                return super().fetch(url, headers)
            except Exception as exc:
                failed.append(str(exc))
                raise
    fetcher = LocalFetcher(allowed_protocols={'file', 'data'}, allow_redirects=False)
    logger.addHandler(handler)
    try:
        document = HTML(string=prepared, base_url=source.as_uri(), url_fetcher=fetcher).render()
        data = document.write_pdf()
    finally:
        logger.removeHandler(handler)
    if failed:
        raise RuntimeError('Resource/font/render failure; no PDF saved:\n' + '\n'.join(failed))
    if not document.pages or not data.startswith(b'%PDF-'):
        raise RuntimeError('Renderer did not produce a PDF')
    if hashlib.sha256(source.read_bytes()).hexdigest() != source_sha or any(
            hashlib.sha256((source.parent/name).read_bytes()).hexdigest() != h for name,h in resources.items()):
        raise RuntimeError('RENDER_INPUT_CHANGED: no PDF saved')
    if renderer_identity(source, fonts) != identity:
        raise RuntimeError('RENDER_TOOLCHAIN_CHANGED: no PDF saved')
    from importlib.metadata import version
    receipt = {'render_receipt_version':1, 'source_name':source.name, 'source_sha256':source_sha,
               'prepared_sha256':hashlib.sha256(prepared.encode('utf-8')).hexdigest(),
               'resources':resources, 'math_renderer':MATH_RENDERER,
               'renderer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               'toolchain':identity,
               'weasyprint_version':version('weasyprint'), 'font_families':fonts or DEFAULT_FONTS,
               'pdf_sha256':hashlib.sha256(data).hexdigest(), 'pages':len(document.pages)}
    save_new(output, data)
    save_new(receipt_path, (json.dumps(receipt,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    print(f'Created {output} ({len(document.pages)} pages). Content and visual review are still required.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path, nargs='?')
    parser.add_argument('--check', action='store_true', help='Check local resources and links without rendering')
    parser.add_argument('--prepare', action='store_true', help='Write new static HTML, not PDF')
    parser.add_argument('--ready', action='store_true', help='With --check, regenerate and compare math caches')
    parser.add_argument('--font', action='append', help='Required installed font family; default Noto Sans CJK KR + Noto Sans Mono CJK KR')
    args = parser.parse_args()
    try:
        if args.prepare and args.check:
            parser.error('--prepare and --check are mutually exclusive')
        if args.ready and not args.check:
            parser.error('--ready requires --check')
        if args.check:
            print(check(args.source, ready=args.ready))
        elif args.prepare and args.output:
            prepare(args.source, args.output)
        elif args.output:
            render(args.source, args.output, args.font)
        else:
            parser.error('output is required unless --check is given')
    except (ValueError, OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f'Render stopped: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
