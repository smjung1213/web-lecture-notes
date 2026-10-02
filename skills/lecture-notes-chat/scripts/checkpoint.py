#!/usr/bin/env python3
"""Resume checkpoints for a web authoring folder. Not a delivery set and not a review.

  create WORK OUTPUT.zip --label L   pack WORK into a new ZIP with a hash manifest, then reopen and verify it
  verify OUTPUT.zip                  reopen a checkpoint and check every file against its manifest
  restore OUTPUT.zip NEW_DIR         verify, then extract into a new folder (no overwrite, no path escape)

A checkpoint only helps if its link reaches the user, so an answer that makes one ends there.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import sys
import zipfile

MANIFEST = 'checkpoint-manifest.json'
SKIP_DIRS = {'__pycache__', 'node_modules', '.git', 'private'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def collect(work):
    files, skipped = {}, []
    for path in sorted(work.rglob('*')):
        rel = path.relative_to(work).as_posix()
        if any(part in SKIP_DIRS for part in path.relative_to(work).parts):
            continue
        if path.is_symlink():
            skipped.append(rel)
        elif path.is_file():
            files[rel] = path.read_bytes()
    return files, skipped


def create(work, output, label):
    work, output = Path(work).resolve(), Path(output).absolute()
    if not work.is_dir():
        raise ValueError('CHECKPOINT_WORK_FOLDER_MISSING')
    if os.path.lexists(output) or output.resolve().is_relative_to(work) or output.suffix.lower() != '.zip':
        raise ValueError('CHECKPOINT_NEW_ZIP_OUTSIDE_WORK_REQUIRED')
    files, skipped = collect(work)
    if not files:
        raise ValueError('CHECKPOINT_EMPTY')
    manifest = {'checkpoint_version': 1, 'label': label, 'created': datetime.now(timezone.utc).isoformat(timespec='seconds'),
                'work_folder': str(work), 'files': {k: {'sha256': digest(v), 'bytes': len(v)} for k, v in files.items()},
                'skipped_symlinks': skipped, 'meaning': 'Resume copy of the working folder; not a delivery set or a content review.'}
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'x', zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
        archive.writestr(MANIFEST, json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    result = verify(output)
    result['skipped_symlinks'] = skipped
    return result


def load(path):
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or MANIFEST not in names:
            raise ValueError('CHECKPOINT_MANIFEST_MISSING_OR_DUPLICATE')
        manifest = json.loads(archive.read(MANIFEST))
        entries = {n: archive.read(n) for n in names if n != MANIFEST}
    return manifest, entries


def verify(path):
    path = Path(path).absolute()
    manifest, entries = load(path)
    expected = manifest.get('files', {})
    if set(entries) != set(expected):
        raise ValueError('CHECKPOINT_FILE_SET_CHANGED')
    for name, row in expected.items():
        if digest(entries[name]) != row['sha256'] or len(entries[name]) != row['bytes']:
            raise ValueError(f'CHECKPOINT_BYTES_CHANGED: {name}')
    return {'status': 'CHECKPOINT_VERIFIED', 'label': manifest.get('label'), 'zip': str(path),
            'zip_sha256': digest(path.read_bytes()), 'files': len(entries),
            'bytes': sum(r['bytes'] for r in expected.values())}


def restore(path, target):
    target = Path(target).absolute()
    if os.path.lexists(target):
        raise ValueError('CHECKPOINT_NEW_FOLDER_REQUIRED')
    result = verify(path)
    _, entries = load(path)
    for name in entries:
        parts = PurePosixPath(name).parts
        if PurePosixPath(name).is_absolute() or '..' in parts or not parts:
            raise ValueError(f'CHECKPOINT_UNSAFE_PATH: {name}')
    for name, data in entries.items():
        out = target / name
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open('xb') as stream:
            stream.write(data)
    result.update(status='CHECKPOINT_RESTORED', restored_to=str(target))
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='command', required=True)
    c = sub.add_parser('create'); c.add_argument('work'); c.add_argument('output'); c.add_argument('--label', required=True)
    v = sub.add_parser('verify'); v.add_argument('zip')
    r = sub.add_parser('restore'); r.add_argument('zip'); r.add_argument('target')
    a = p.parse_args(argv)
    try:
        if a.command == 'create':
            result = create(a.work, a.output, a.label)
        elif a.command == 'verify':
            result = verify(a.zip)
        else:
            result = restore(a.zip, a.target)
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, json.JSONDecodeError) as exc:
        print(json.dumps({'status': 'CHECKPOINT_FAILED', 'error': str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
