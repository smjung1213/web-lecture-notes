"""Render one authored HTML to a new PDF; no source edits or model/API calls.

Resource loads stay within the HTML's directory. Missing resources are fatal,
including loads that WeasyPrint would otherwise log and silently omit.
"""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlparse, unquote, urljoin
import argparse
import sys


class References(HTMLParser):
    def __init__(self):
        super().__init__()
        self.resources = []
        self.ids = set()
        self.links = []
        self.errors = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get('id'):
            if a['id'] in self.ids:
                self.errors.append(f"Duplicate id: {a['id']}")
            self.ids.add(a['id'])
        if tag == 'a' and a.get('href', '').startswith('#'):
            self.links.append(a['href'][1:])
        if tag == 'img':
            if not a.get('src'):
                self.errors.append('Image has no src')
            else:
                self.resources.append(a['src'])
        if tag == 'link' and 'stylesheet' in a.get('rel', '').split():
            self.resources.append(a.get('href', ''))
        if tag in ('script', 'base', 'iframe', 'object'):
            self.errors.append(f'Unsupported active/base element: {tag}')


def local_resource(url, root):
    parsed = urlparse(url)
    if parsed.scheme == 'data':
        return None
    if parsed.scheme != 'file' or parsed.netloc not in ('', 'localhost'):
        raise ValueError(f'Use a bundled local resource, not: {url}')
    path = Path(unquote(parsed.path)).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f'Resource outside authored package: {path}')
    if not path.is_file():
        raise FileNotFoundError(f'Missing resource: {path}')
    return path


def render(source, output):
    source = Path(source).resolve()
    output = Path(output).resolve()
    if not source.is_file() or source.suffix.lower() not in ('.html', '.htm'):
        raise ValueError('Input must be an existing HTML file')
    if output.suffix.lower() != '.pdf':
        raise ValueError('Output must have a .pdf extension')
    if output.exists():
        raise FileExistsError(f'Choose a new output file: {output}')
    root = source.parent
    parser = References()
    parser.feed(source.read_text(encoding='utf-8'))
    for target in parser.links:
        if target not in parser.ids:
            parser.errors.append(f'Missing internal link target: #{target}')
    if parser.errors:
        raise ValueError('\n'.join(parser.errors))
    for resource in parser.resources:
        local_resource(urljoin(source.as_uri(), resource), root)
    try:
        from weasyprint import HTML, default_url_fetcher
    except ImportError as exc:
        raise RuntimeError('WeasyPrint is unavailable. Use an available renderer or deliver HTML; do not claim a PDF was made.') from exc
    failed = []

    def fetch(url):
        try:
            local_resource(url, root)
            return default_url_fetcher(url)
        except Exception as exc:
            failed.append(str(exc))
            raise

    document = HTML(filename=str(source), url_fetcher=fetch).render()
    data = document.write_pdf()
    if failed:
        raise RuntimeError('Resource loading failed; no PDF saved:\n' + '\n'.join(failed))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('xb') as stream:
        stream.write(data)
    print(f'Created {output} ({len(document.pages)} pages). Content and visual review are still required.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    try:
        render(args.source, args.output)
    except (ValueError, OSError, RuntimeError) as exc:
        print(f'Render stopped: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
