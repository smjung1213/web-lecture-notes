#!/usr/bin/env python3
"""Fetch or read a pinned runtime ZIP (wheels, MathJax, fonts), verify it, extract into a NEW directory."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import urllib.error
import urllib.parse
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent
HOSTS = {'github.com', 'release-assets.githubusercontent.com', 'objects.githubusercontent.com'}


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


class ReleaseRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, new_url):
        parsed = urllib.parse.urlsplit(new_url)
        if parsed.scheme != 'https' or parsed.hostname not in HOSTS or parsed.username or parsed.password:
            raise ValueError('UNEXPECTED_RELEASE_REDIRECT')
        return super().redirect_request(request, fp, code, message, headers, new_url)


def download(url, target, expected_size):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != 'https' or parsed.hostname != 'github.com' or parsed.username or parsed.password:
        raise ValueError('INVALID_RELEASE_URL')
    # No browser cookies, tokens, private keys or credential forwarding. A private
    # release needs an authorized download tool, followed by --archive instead.
    opener = urllib.request.build_opener(ReleaseRedirect())
    request = urllib.request.Request(url, headers={'User-Agent': 'lecture-notes-runtime-fetch/1'})
    try:
        with opener.open(request, timeout=30) as response, target.open('xb') as stream:
            size = 0
            while chunk := response.read(1024 * 1024):
                size += len(chunk)
                if size > expected_size:
                    raise ValueError('ARCHIVE_SIZE_MISMATCH')
                stream.write(chunk)
            if size != expected_size:
                raise ValueError('ARCHIVE_SIZE_MISMATCH')
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403, 404):
            raise RuntimeError(f'RELEASE_ACCESS_REQUIRED: HTTP {exc.code}; use an authorized '
                               'GitHub download and --archive, or attach the exact ZIP; '
                               'do not expose credentials or change repository visibility') from exc
        raise RuntimeError(f'RELEASE_DOWNLOAD_FAILED: HTTP {exc.code}') from exc


def extract_verified(archive, output, attachment, rows):
    if archive.stat().st_size != attachment['bytes'] or digest(archive) != attachment['sha256']:
        raise ValueError('ARCHIVE_HASH_OR_SIZE_MISMATCH')
    expected = {'wheels/' + row['filename']: row for row in rows}
    with zipfile.ZipFile(archive) as z:
        entries = z.infolist()
        if len(entries) != len(expected) or {i.filename for i in entries} != set(expected):
            raise ValueError('ARCHIVE_FILE_SET_CHANGED')
        # Check the entire archive before writing any extracted entry.
        for info in entries:
            row = expected[info.filename]
            mode = info.external_attr >> 16
            if (info.is_dir() or (stat.S_IFMT(mode) and not stat.S_ISREG(mode)) or
                    info.flag_bits & 1 or info.file_size != row['bytes']):
                raise ValueError('UNSAFE_ARCHIVE_MEMBER: ' + info.filename)
            if hashlib.sha256(z.read(info)).hexdigest() != row['sha256']:
                raise ValueError('WHEEL_HASH_MISMATCH: ' + info.filename)
        wheels = output / 'wheels'
        wheels.mkdir()
        for info in entries:
            # Paths come from the managed manifest, never extractall/untrusted paths.
            with (wheels / expected[info.filename]['filename']).open('xb') as f:
                f.write(z.read(info))
    return wheels


def extract_component(archive, output, spec):
    """MathJax/font ZIP: the managed archive SHA-256 pins every byte; extract regular files only."""
    archive, output = Path(archive), Path(output).absolute()
    if not archive.is_file() or archive.stat().st_size != spec['bytes'] or digest(archive) != spec['sha256']:
        raise ValueError('ARCHIVE_HASH_OR_SIZE_MISMATCH: ' + spec['filename'])
    if os.path.lexists(output):
        raise ValueError('Choose a NEW output directory')
    with zipfile.ZipFile(archive) as z:
        entries = [i for i in z.infolist() if not i.is_dir()]
        for info in entries:
            path, mode = PurePosixPath(info.filename), info.external_attr >> 16
            if (path.is_absolute() or '..' in path.parts or info.flag_bits & 1 or
                    (stat.S_IFMT(mode) and not stat.S_ISREG(mode))):
                raise ValueError('UNSAFE_ARCHIVE_MEMBER: ' + info.filename)
        if len(entries) != spec['file_count']:
            raise ValueError('ARCHIVE_FILE_SET_CHANGED: ' + spec['filename'])
        output.mkdir(parents=True)
        for info in entries:
            target = output.joinpath(*PurePosixPath(info.filename).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(info) as source, target.open('xb') as dest:
                shutil.copyfileobj(source, dest)
    return output


def fetch_bundle(output, archive=None, offline=None):
    offline = offline or ROOT / 'offline'
    output = Path(output).absolute()
    if os.path.lexists(output) or output.resolve().is_relative_to(ROOT.parent):
        raise ValueError('Choose a NEW output directory outside the managed skill')
    attachment = json.loads((offline / 'attachment.json').read_text())
    rows = json.loads((offline / 'wheel-sources.json').read_text())
    output.mkdir(parents=True, exist_ok=False)
    result = {'status': 'INCOMPLETE', 'download_url': attachment.get('download_url'),
              'source': 'local_archive' if archive is not None else 'https_download',
              'installation_performed': False}
    try:
        local = output / attachment['filename']
        if archive is None:
            download(attachment['download_url'], local, attachment['bytes'])
        else:
            archive = Path(archive)
            if not archive.is_file() or archive.stat().st_size != attachment['bytes']:
                raise ValueError('ARCHIVE_HASH_OR_SIZE_MISMATCH')
            with archive.open('rb') as source, local.open('xb') as dest:
                shutil.copyfileobj(source, dest)
        wheels = extract_verified(local, output, attachment, rows)
        result.update(status='VERIFIED', archive_sha256=digest(local), wheels=str(wheels),
                      wheel_count=len(rows), wheel_hashes={r['filename']: r['sha256'] for r in rows})
        return wheels
    except Exception as exc:
        result['error'] = f'{type(exc).__name__}: {exc}'
        raise
    finally:
        with (output / 'fetch-result.json').open('x', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
            f.write('\n')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--download', action='store_true', help='One HTTPS attempt to the pinned Release URL')
    mode.add_argument('--archive', type=Path, help='ZIP downloaded by an authorized tool or attached by the user')
    args = p.parse_args()
    try:
        print(fetch_bundle(args.output, args.archive))
    except (OSError, ValueError, RuntimeError, zipfile.BadZipFile) as exc:
        print(f'Fetch stopped: {exc}')
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
