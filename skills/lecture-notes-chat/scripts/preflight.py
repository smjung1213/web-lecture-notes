#!/usr/bin/env python3
"""Observe this environment and render the managed two-page synthetic input. No install.

--draft-renderer accepts the preinstalled WeasyPrint 68.0 for a web draft; official PDFs use 70.0.
"""
import argparse
import hashlib
import importlib
import importlib.metadata as md
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def environment():
    return {'sys_platform': sys.platform, 'machine': platform.machine().lower(),
            'implementation': platform.python_implementation(),
            'python': platform.python_version(), 'libc': platform.libc_ver(),
            'executable': sys.executable, 'executable_sha256': sha(sys.executable),
            'sys_path': sys.path[:],
            'packages': {d.metadata['Name']: d.version for d in md.distributions()}}


def check_isolation(site):
    """Must run in the unchanged Python with -S and only the new package directory."""
    if not sys.flags.no_site:
        raise RuntimeError('ISOLATION_REQUIRES_PYTHON_MINUS_S')
    site = Path(site).resolve()
    lock = json.loads((ROOT / 'offline/runtime-lock.json').read_text())
    distributions = list(md.distributions())
    normalize = lambda s: s.lower().replace('_', '-').replace('.', '-')
    if {normalize(d.metadata['Name']) for d in distributions} != {normalize(n) for n in lock['versions']}:
        raise RuntimeError('ISOLATED_PACKAGE_SET_MISMATCH')
    for name, expected in lock['versions'].items():
        d = md.distribution(name)
        if d.version != expected or not Path(d.locate_file('')).resolve().is_relative_to(site):
            raise RuntimeError('ISOLATED_PACKAGE_MISMATCH: ' + name)
    # Check actual imports too: metadata alone cannot rule out base-package leakage.
    modules = {}
    for name in ('weasyprint', 'bs4', 'tinycss2', 'pypdf', 'PIL.Image', 'cffi', 'fontTools',
                 'brotli', 'zopfli', 'soupsieve', 'typing_extensions', 'cssselect2', 'pycparser',
                 'pydyf', 'pyphen', 'tinyhtml5', 'webencodings'):
        m = importlib.import_module(name)
        if not Path(m.__file__).resolve().is_relative_to(site):
            raise RuntimeError('BASE_PACKAGE_LEAK: ' + name)
        modules[name] = m.__file__
    return modules


def sample_png(target):
    """Copy the managed PNG if its bytes are a real image; otherwise draw the same synthetic crop.

    A text-only repository connector cannot deliver the binary, and the image is only a
    synthetic readability probe, so a drawn copy is recorded as 'generated'.
    """
    from PIL import Image
    source = ROOT.parent / 'assets' / 'sample-slide-crop.png'
    try:
        with Image.open(source) as image:
            image.verify()
        shutil.copyfile(source, target)
        return 'repository'
    except Exception:
        draw_sample_png(target)
        return 'generated'


def draw_sample_png(target):
    from PIL import Image, ImageDraw, ImageFont

    def font(style, size):
        path = subprocess.check_output(['fc-match', '-f', '%{file}', f'Noto Sans CJK KR:{style}'],
                                       text=True, timeout=30).strip()
        return ImageFont.truetype(path, size)

    image = Image.new('RGB', (1500, 660), 'white')
    draw = ImageDraw.Draw(image)
    draw.text((40, 30), '처리율 = 처리량 ÷ 시간', font=font('bold', 96), fill='#1f1f1f')
    for x, label, value in ((40, '측정 A', '12 ÷ 3 = 4'), (900, '측정 B', '20 ÷ 5 = 4')):
        draw.rounded_rectangle((x, 185, x + 560, 490), radius=16, fill='#dcebf7', outline='#333333', width=4)
        draw.text((x + 45, 210), label, font=font('regular', 80), fill='#1f1f1f')
        draw.text((x + 45, 345), value, font=font('regular', 96), fill='#c00000')
    draw.line((640, 338, 860, 338), fill='#333333', width=12)
    draw.polygon([(860, 305), (900, 338), (860, 371)], fill='#333333')
    draw.text((40, 545), '단위: 개/분 · 준비 단계(2분)는 비교에서 제외', font=font('regular', 64), fill='#333333')
    image.save(target, dpi=(300, 300))


def check_note_links(page, number):
    """PDF rectangles may list either corner first; require both note directions."""
    targets = set()
    for ref in page.get('/Annots', []):
        annotation = ref.get_object()
        if annotation.get('/Subtype') != '/Link':
            continue
        rect = annotation.get('/Rect', [])
        if len(rect) == 4 and abs(rect[2] - rect[0]) > 0 and abs(rect[3] - rect[1]) > 0:
            targets.add(str(annotation.get('/Dest')))
    if not {f'fix-{number}', f'fix-{number}-call'} <= targets:
        raise RuntimeError('PDF_LINK_AREA_MISSING')


def run(output, site=None, draft=False):
    output = Path(output).absolute()
    if os.path.lexists(output) or output.resolve().is_relative_to(ROOT.parent):
        raise ValueError('Choose a NEW output directory outside the managed skill')
    output.mkdir(parents=True, exist_ok=False)
    result = {'status': 'INCOMPLETE', 'visual_review': 'NOT_PERFORMED',
              'viewer_click_search_copy': 'NOT_PERFORMED', 'pdf_accessibility': 'NOT_VERIFIED',
              'renderer_mode': 'draft' if draft else 'official'}
    try:
        result['environment'] = environment()
        import render
        result['required_versions'] = render.require_renderer(draft=True) if draft else render.require_renderer()
        if site is not None:
            result['isolated_modules'] = check_isolation(site)
        result['pypdf'] = md.version('pypdf')
        if not draft and result['pypdf'] != '6.17.0':
            raise RuntimeError('PREFLIGHT_DEPENDENCY_MISMATCH: pypdf requires 6.17.0')
        mathjax = json.loads(subprocess.check_output(
            ['node', str(ROOT / 'typeset.cjs'), '--identity'], text=True, timeout=120))
        if mathjax['version'] != '3.2.1' or int(mathjax['node'].lstrip('v').split('.')[0]) < 18:
            raise RuntimeError('Node 18+ and MathJax 3.2.1 are required')
        result['mathjax'] = mathjax
        result['fonts'] = render.check_fonts(render.DEFAULT_FONTS)
        working = output / 'sample'
        working.mkdir()
        for name in ('preflight.html', 'lecture.css'):
            shutil.copyfile(ROOT.parent / 'assets' / name, working / name)
        result['sample_png'] = sample_png(working / 'sample-slide-crop.png')
        result['source_sha256'] = {p.name: sha(p) for p in working.iterdir()}
        prepared = working / 'prepared.html'
        render.prepare(working / 'preflight.html', prepared)
        result['ready'] = render.check(prepared, ready=True)
        if result['ready'].get('math_cache') != 'REGENERATED_AND_MATCHED':
            raise RuntimeError('MATH_CACHE_MISMATCH')
        pdf = output / 'synthetic.pdf'
        render.render(prepared, pdf, draft=True) if draft else render.render(prepared, pdf)
        receipt = json.loads(pdf.with_name(pdf.name + '.render.json').read_text())
        from pypdf import PdfReader
        reader = PdfReader(pdf)
        if len(reader.pages) != 2:
            raise RuntimeError('SYNTHETIC_PAGE_COUNT_MISMATCH')
        for i, token in enumerate(('정정 검사 문장 하나', '정정 검사 문장 둘')):
            if ''.join(token.split()) not in ''.join(reader.pages[i].extract_text().split()):
                raise RuntimeError('PAGE_NOTE_TEXT_MISSING: ' + token)
        notes = receipt['page_notes']
        if len(notes) != 2 or [n['page'] for n in notes] != [1, 2] or any(
                not n['same_page'] or not n['text_matched'] for n in notes):
            raise RuntimeError('PAGE_NOTE_RESULT_MISMATCH')
        # Structural link checks are separate from an actual PDF viewer test.
        for number, page in enumerate(reader.pages, 1):
            check_note_links(page, number)
        result.update(status='AUTOMATED_CHECKS_PASSED_VISUAL_REVIEW_REQUIRED', pages=2,
                      pdf=pdf.name, pdf_sha256=sha(pdf), page_notes=notes)
    except Exception as exc:
        result['error'] = f'{type(exc).__name__}: {exc}'
    save(output / 'preflight-result.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--site', type=Path, help='Verify isolation; use only with Python -B -S and PYTHONPATH')
    parser.add_argument('--draft-renderer', action='store_true',
                        help='Web draft only: accept the preinstalled WeasyPrint 68.0 (see render.py)')
    args = parser.parse_args()
    if args.site and args.draft_renderer:
        parser.error('--site checks the isolated 70.0 runtime; do not combine it with --draft-renderer')
    result = run(args.output, args.site, args.draft_renderer)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['status'] == 'AUTOMATED_CHECKS_PASSED_VISUAL_REVIEW_REQUIRED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
