#!/usr/bin/env python3
"""Prepare the render runtime from pinned Drive files in a NEW directory; preserve the base Python.

Run once without archives: the result lists only the missing pinned files (wheels for this
Python, MathJax, fonts). Pass them back with --archive/--mathjax-archive/--fonts-archive.
"""
import argparse
import datetime
import hashlib
import importlib.metadata as md
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
WHEEL_SETS = (ROOT / 'offline', ROOT / 'offline/cp312')
FONT_FAMILIES = ('Noto Serif CJK KR', 'Noto Sans CJK KR', 'Noto Sans Mono CJK KR')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def save(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def wheel_set():
    """Managed wheel data for this Python; an unsupported Python fails check_target."""
    minor = '.'.join(platform.python_version_tuple()[:2])
    for offline in WHEEL_SETS:
        if json.loads((offline / 'runtime-lock.json').read_text())['target']['python'] == minor:
            return offline
    return WHEEL_SETS[0]


def check_target(target):
    actual = {'sys_platform': sys.platform,
              'machine': platform.machine().lower(),
              'python': f'{sys.version_info.major}.{sys.version_info.minor}',
              'implementation': platform.python_implementation()}
    for key, value in target.items():
        if actual.get(key) != value:
            raise RuntimeError(f'TARGET_MISMATCH: {key}: expected {value}, found {actual.get(key)}')
    actual['libc'] = platform.libc_ver()
    if actual['libc'][0] != 'glibc' or tuple(map(int, actual['libc'][1].split('.'))) < (2, 28):
        raise RuntimeError('TARGET_MISMATCH: these wheels require glibc >= 2.28')
    return actual


def snapshot(names):
    packages = {}
    for name in names:
        try:
            dist = md.distribution(name)
        except md.PackageNotFoundError:
            packages[name] = None
            continue
        files = {}
        for member in dist.files or []:
            if str(member).endswith(('.pyc', '.pyo')):
                continue
            p = dist.locate_file(member)
            if p.is_file():
                files[str(member)] = sha(p)
        packages[name] = {'version': dist.version, 'location': str(dist.locate_file('')),
                          'files_sha256': files}
    return {'platform': {'platform': platform.platform(), 'libc': platform.libc_ver()},
            'python': {'executable': sys.executable,
                       'resolved': str(Path(sys.executable).resolve()),
                       'sha256': sha(sys.executable), 'version': sys.version},
            'packages': packages}


def clean_environment():
    env = {k: v for k, v in os.environ.items()
           if not k.startswith('PIP_') and k not in ('PYTHONPATH', 'PYTHONHOME')}
    env.update(PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1',
               PIP_DISABLE_PIP_VERSION_CHECK='1', PIP_CONFIG_FILE=os.devnull)
    return env


def scrub(text):
    return re.sub(r'(https?://)[^\s/]+@', r'\1[redacted]@', text)


def command(output, label, argv, env, timeout=180):
    row = {'command': argv, 'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
    try:
        r = subprocess.run(argv, env=env, cwd=output, capture_output=True, text=True, timeout=timeout)
        row.update(returncode=r.returncode, stdout=scrub(r.stdout), stderr=scrub(r.stderr), timeout=False)
    except subprocess.TimeoutExpired as exc:
        def decode(x):
            return x.decode(errors='replace') if isinstance(x, bytes) else (x or '')
        row.update(returncode=None, stdout=scrub(decode(exc.stdout)),
                   stderr=scrub(decode(exc.stderr)), timeout=True)
    row['finished_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    save(output / 'evidence' / (label + '.json'), row)
    if row['returncode'] != 0:
        raise RuntimeError(label + ' failed; see evidence/' + label + '.json')
    return row



def verify_wheels(bundle, offline=None):
    """Trust managed PyPI hashes, never scripts or a manifest from the attachment."""
    bundle = Path(bundle).resolve()
    rows = json.loads(((offline or wheel_set()) / 'wheel-sources.json').read_text())
    expected = {r['filename']: r['sha256'] for r in rows}
    if {p.name for p in bundle.iterdir()} != set(expected):
        raise ValueError('WHEEL_FILE_SET_CHANGED: point --wheels at the exact 17-wheel directory')
    for name, digest in expected.items():
        p = bundle / name
        if Path(name).name != name or p.is_symlink() or not p.is_file() or sha(p) != digest:
            raise ValueError('WHEEL_HASH_MISMATCH: ' + name)
    return expected


def install_command(wheels, site, output, offline=None):
    return [sys.executable, '-B', '-m', 'pip', '--isolated', 'install',
            '--disable-pip-version-check', '--no-index', '--find-links', str(wheels),
            '--only-binary=:all:', '--require-hashes', '--no-cache-dir', '--no-compile',
            '--ignore-installed', '--target', str(site),
            '--report', str(output / 'evidence/install-report.json'),
            '-r', str((offline or wheel_set()) / 'requirements-offline.txt')]


def already_available():
    # The subsequent real import + synthetic preflight must still pass.
    for name, expected in {'weasyprint': '70.0', 'beautifulsoup4': '4.14.3',
                           'tinycss2': '1.5.1', 'pypdf': '6.17.0'}.items():
        try:
            if md.version(name) != expected:
                return False
        except md.PackageNotFoundError:
            return False
    return True


def mathjax_ready(env):
    try:
        r = subprocess.run(['node', str(ROOT / 'typeset.cjs'), '--identity'], env=env,
                           capture_output=True, text=True, timeout=120)
        return r.returncode == 0 and json.loads(r.stdout).get('version') == '3.2.1'
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return False


def fonts_ready(env):
    try:
        return all(subprocess.run(['fc-match', '-f', '%{family}', family], env=env, capture_output=True,
                                  text=True, timeout=30).stdout.split(',')[0] == family
                   for family in FONT_FAMILIES)
    except (OSError, subprocess.TimeoutExpired):
        return False


def install_fonts(archive, output):
    from fetch_runtime import extract_component
    spec = json.loads((ROOT / 'offline/fonts.json').read_text())
    fonts = extract_component(archive, output / 'fonts', spec)
    for name, row in spec['files'].items():
        if not (fonts / name).is_file() or sha(fonts / name) != row['sha256']:
            raise ValueError('FONT_HASH_MISMATCH: ' + name)
    conf = output / 'fonts.conf'
    conf.write_text('<?xml version="1.0"?>\n<!DOCTYPE fontconfig SYSTEM "fonts.dtd">\n<fontconfig>\n'
                    '  <include ignore_missing="yes">/etc/fonts/fonts.conf</include>\n'
                    f'  <dir>{fonts}</dir>\n  <cachedir>{output / "fontconfig-cache"}</cachedir>\n'
                    '</fontconfig>\n', encoding='utf-8')
    return conf


def required_file(spec):
    return {k: spec[k] for k in ('filename', 'bytes', 'sha256', 'drive_file_id')}


def run(output, wheels=None, mathjax_root=None, archive=None, mathjax_archive=None,
        fonts_archive=None, node=None):
    if wheels is not None and archive is not None:
        raise ValueError('Choose either --wheels or --archive')
    output = Path(output).absolute()
    if (os.path.lexists(output) or output.resolve().is_relative_to(ROOT.parent) or
            (wheels is not None and output.resolve().is_relative_to(Path(wheels).resolve()))):
        raise ValueError('Choose a NEW output directory outside the skill and wheel directory')
    output.mkdir(parents=True, exist_ok=False)
    (output / 'evidence').mkdir()
    offline = wheel_set()
    lock = json.loads((offline / 'runtime-lock.json').read_text())
    names = sorted(set(lock['versions']) | {'pip'})
    summary = {'status': 'INCOMPLETE', 'stage': 'preflight', 'installation_performed': False,
               'visual_review': 'NOT_PERFORMED', 'preservation_scope': names}
    before = None
    wheel_hashes = None
    try:
        before = snapshot(names)
        save(output / 'evidence/base-before.json', before)
        env = clean_environment()
        changed = {}
        if node is not None:
            changed['PATH'] = str(Path(node).resolve().parent) + os.pathsep + env.get('PATH', '')
        if mathjax_root is not None:
            changed['MATHJAX_MODULE_ROOT'] = str(Path(mathjax_root).resolve())
        env.update(changed)
        if shutil.which('node', path=env.get('PATH')) is None:
            raise RuntimeError('NODE_REQUIRED: pass --node with the existing Node 18+ executable')
        python_ready = already_available()
        required = []
        summary['stage'] = 'mathjax'
        if not mathjax_ready(env):
            if mathjax_archive is None:
                required.append(required_file(json.loads((ROOT / 'offline/mathjax.json').read_text())))
            else:
                from fetch_runtime import extract_component
                spec = json.loads((ROOT / 'offline/mathjax.json').read_text())
                extract_component(mathjax_archive, output / 'mathjax', spec)
                changed['MATHJAX_MODULE_ROOT'] = str(output / 'mathjax' / spec['module'])
                env.update(changed)
                if not mathjax_ready(env):
                    raise RuntimeError('MATHJAX_SETUP_FAILED')
        summary['stage'] = 'fonts'
        if not fonts_ready(env):
            if fonts_archive is None:
                required.append(required_file(json.loads((ROOT / 'offline/fonts.json').read_text())))
            else:
                changed['FONTCONFIG_FILE'] = str(install_fonts(fonts_archive, output))
                env.update(changed)
                if not fonts_ready(env):
                    raise RuntimeError('FONT_SETUP_FAILED')
        if not python_ready:
            summary['actual_target'] = check_target(lock['target'])
            if wheels is None and archive is None:
                required.append(required_file(json.loads((offline / 'attachment.json').read_text())))
        if required:
            summary['required_files'] = required
            raise RuntimeError('RUNTIME_FILES_REQUIRED: download these pinned Drive files by file ID '
                               '(raw) and rerun in a NEW output with the matching archive options: ' +
                               ', '.join(r['filename'] for r in required))
        if python_ready:
            summary['mode'] = 'REUSE_EXISTING_RUNTIME'
            # A previous isolated setup may itself be the current environment.
            # Do not fall back to base site-packages when reusing it.
            if 'PYTHONPATH' in os.environ:
                env['PYTHONPATH'] = os.environ['PYTHONPATH']
            child = [sys.executable, '-B'] + (['-S'] if sys.flags.no_site else [])
            child += [str(ROOT / 'preflight.py'), '--output', str(output / 'preflight')]
        else:
            summary['mode'] = 'ISOLATED_OFFLINE_INSTALL'
            if archive is not None:
                from fetch_runtime import fetch_bundle
                summary['stage'] = 'verify-release-archive'
                wheels = fetch_bundle(output / 'bundle', archive, offline)
            wheels = Path(wheels).resolve()
            wheel_hashes = verify_wheels(wheels, offline)
            site = output / 'site-packages'
            if os.path.lexists(site):
                raise FileExistsError('Choose a NEW site-packages directory')
            summary['stage'] = 'offline-install'
            command(output, '01-offline-install', install_command(wheels, site, output, offline), env)
            summary['installation_performed'] = True
            changed['PYTHONPATH'] = str(site)
            env.update(changed)
            child = [sys.executable, '-B', '-S', str(ROOT / 'preflight.py'),
                     '--site', str(site), '--output', str(output / 'preflight')]
            summary['runtime_command_prefix'] = [sys.executable, '-B', '-S']
        summary['runtime_environment'] = changed
        summary['stage'] = 'synthetic-preflight'
        command(output, '02-preflight', child, env, timeout=240)
        summary['preflight'] = json.loads((output / 'preflight/preflight-result.json').read_text())
        summary['status'] = 'AUTOMATED_CHECKS_PASSED_VISUAL_REVIEW_REQUIRED'
        summary['stage'] = 'complete'
    except Exception as exc:
        summary['error'] = f'{type(exc).__name__}: {exc}'
    finally:
        if before is not None:
            try:
                after = snapshot(names)
                save(output / 'evidence/base-after.json', after)
                summary['base_environment_unchanged'] = before == after
                summary['base_package_files_checked'] = sum(len(v['files_sha256']) for v in before['packages'].values() if v)
                if before != after:
                    summary['status'] = 'BASE_PRESERVATION_CHECK_FAILED'
            except Exception as exc:
                summary.update(status='BASE_PRESERVATION_CHECK_INCOMPLETE', preservation_error=str(exc))
        if wheel_hashes is not None:
            try:
                summary['wheels_unchanged'] = verify_wheels(wheels, offline) == wheel_hashes
            except Exception as exc:
                summary.update(status='WHEELS_CHANGED', wheels_unchanged=False, wheel_error=str(exc))
        save(output / 'result.json', summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group()
    inputs.add_argument('--wheels', type=Path, help='Extracted directory of the 17 official wheels')
    inputs.add_argument('--archive', type=Path, help='Pinned wheel ZIP for this Python; verify and extract only if installation is needed')
    parser.add_argument('--mathjax-archive', type=Path, help='Pinned MathJax 3.2.1 node_modules ZIP')
    parser.add_argument('--fonts-archive', type=Path, help='Pinned Noto CJK KR font ZIP')
    parser.add_argument('--node', type=Path, help='Existing Node 18+ executable when node is not on PATH')
    parser.add_argument('--verify-only', action='store_true')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--mathjax-root', type=Path, help='Existing mathjax-full 3.2.1; no Node installation')
    args = parser.parse_args()
    if args.verify_only:
        if args.wheels is None:
            parser.error('--verify-only requires --wheels')
        print(json.dumps({'wheel_hashes': verify_wheels(args.wheels), 'installation_performed': False}))
        return 0
    if args.output is None:
        parser.error('--output is required')
    result = run(args.output, args.wheels, args.mathjax_root, args.archive, args.mathjax_archive,
                 args.fonts_archive, args.node)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['status'] == 'AUTOMATED_CHECKS_PASSED_VISUAL_REVIEW_REQUIRED' else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as exc:
        print(f'Stopped: {exc}', file=sys.stderr)
        raise SystemExit(1)
