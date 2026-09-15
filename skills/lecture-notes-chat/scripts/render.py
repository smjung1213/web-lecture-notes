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
        if tag == 'a' and a.get('href', '').startswith('#'):
            self.links.append(unquote(a['href'][1:]))
        if tag in ('img', 'source'):
            if tag == 'img' and not a.get('src'):
                self.errors.append('Image has no src')
            if a.get('src'):
                self.resources.append(a['src'])
            if a.get('srcset'):
                self.errors.append('Use one explicit bundled src instead of srcset')
        if tag == 'link' and 'stylesheet' in a.get('rel', '').split():
            self.resources.append(a.get('href', ''))
        if tag in ('script', 'base', 'iframe', 'object', 'embed'):
            self.errors.append(f'Unsupported active/base element: {tag}')
        if any(k.lower().startswith('on') for k in a):
            self.errors.append('Inline event handlers are unsupported')
        if 'style' in a:
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


def check(source):
    source = Path(source).resolve()
    if not source.is_file() or source.suffix.lower() not in ('.html', '.htm'):
        raise ValueError('Input must be an existing HTML file')
    root = source.parent
    parser = References()
    parser.feed(source.read_text(encoding='utf-8'))
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
            'internal_links': len(parser.links)}


def check_fonts(families):
    for family in families:
        result = subprocess.run(['fc-match', '-f', '%{family}', family],
                                text=True, capture_output=True, check=True, timeout=10)
        found = [s.strip().casefold() for s in result.stdout.split(',')]
        if family.casefold() not in found:
            raise RuntimeError(f'Required font unavailable: {family} (matched {result.stdout})')


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
    if os.path.lexists(output):
        raise FileExistsError(f'Choose a new output file: {output}')
    check(source)
    check_fonts(fonts or ['Noto Sans CJK KR'])
    # Homebrew's shared libraries are not on macOS's default loader path.
    if sys.platform == 'darwin' and Path('/opt/homebrew/lib/libgobject-2.0.dylib').exists():
        os.environ.setdefault('DYLD_FALLBACK_LIBRARY_PATH', '/opt/homebrew/lib')
    try:
        from weasyprint import HTML, default_url_fetcher
    except (ImportError, OSError) as exc:
        raise RuntimeError('WeasyPrint or its native libraries are unavailable; no PDF created') from exc
    failed = []
    class ResourceErrors(logging.Handler):
        def emit(self, record):
            message = record.getMessage()
            if record.levelno >= logging.ERROR or 'Font-face' in message or 'font cannot' in message.lower():
                failed.append(message)
    handler = ResourceErrors()
    logger = logging.getLogger('weasyprint')
    def fetch(url):
        try:
            local_resource(url, source.parent)
            return default_url_fetcher(url)
        except Exception as exc:
            failed.append(str(exc))
            raise
    logger.addHandler(handler)
    try:
        document = HTML(filename=str(source), url_fetcher=fetch).render()
        data = document.write_pdf()
    finally:
        logger.removeHandler(handler)
    if failed:
        raise RuntimeError('Resource/font/render failure; no PDF saved:\n' + '\n'.join(failed))
    if not document.pages or not data.startswith(b'%PDF-'):
        raise RuntimeError('Renderer did not produce a PDF')
    save_new(output, data)
    print(f'Created {output} ({len(document.pages)} pages). Content and visual review are still required.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path, nargs='?')
    parser.add_argument('--check', action='store_true', help='Check local resources and links without rendering')
    parser.add_argument('--font', action='append', help='Required installed font family; default Noto Sans CJK KR')
    args = parser.parse_args()
    try:
        if args.check:
            print(check(args.source))
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
