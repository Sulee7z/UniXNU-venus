#!/usr/bin/env python3
"""Assemble a local iOS26 root candidate from verified rewrites and APFS inputs."""
import argparse
import hashlib
import json
from pathlib import Path
import os
import stat
import subprocess
import sys

ROOT = Path('/root/unixnu-build')
DEVICE = Path('/mnt/g/UniXNU-Port/ports/UniXNU-venus')
BASE = ROOT / 'venus-ios26-inputs'
USERLAND = ROOT / 'venus-ios26-userland'
CACHE = ROOT / 'venus-ios26-cache-rewritten'
TRUST = ROOT / 'venus-ios26-trustcache.bundle'
OUT = ROOT / 'venus-ios26-root-candidate'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def run(command, log=None):
    print('RUN', ' '.join(map(str, command)), flush=True)
    if log:
        with log.open('w') as stream:
            result = subprocess.run([str(v) for v in command], stdout=stream,
                                    stderr=subprocess.STDOUT)
    else:
        result = subprocess.run([str(v) for v in command])
    if result.returncode:
        raise RuntimeError(f'command failed: {command}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rebuild', action='store_true')
    parser.add_argument('--accel', choices=['kvm', 'tcg'], default='tcg')
    args = parser.parse_args()
    if OUT.exists() and not args.rebuild:
        raise RuntimeError(f'{OUT} exists; use --rebuild only for a new local candidate')
    if args.rebuild and OUT.exists():
        import shutil
        shutil.rmtree(OUT)
    OUT.mkdir()
    report = dict(result='preparing', phone_operations=False,
                  source_root_sha256=sha(BASE / 'OS-grown.json'),
                  source_userland_report_sha256=sha(USERLAND / 'report.json'),
                  source_cache_report_sha256=sha(CACHE / 'report.json'))
    try:
        python = ROOT / 'venus-zeta-audit-venv/bin/python'
        run([python, '/mnt/g/UniXNU-Port/sources/UniXNU-zeta-none24smu/scripts/make-zeta-trust-bundle.py',
             '--apple-trust-cache', BASE / '094-54256-108.dmg.aea.trustcache',
             '--apple-trust-cache', BASE / '094-54345-109.dmg.aea.trustcache',
             '--rewrite-report', USERLAND / 'report.json', '--rewrite-report', CACHE / 'report.json',
             '--output', TRUST, '--report', ROOT / 'venus-ios26-trustcache.json'])
        trust_report = json.loads((ROOT / 'venus-ios26-trustcache.json').read_text())
        user_report = json.loads((USERLAND / 'report.json').read_text())
        cache_report = json.loads((CACHE / 'report.json').read_text())
        entries = []
        for item in user_report['images']:
            source = USERLAND / item['output'].lstrip('/')
            if sha(source) != item['output_sha256']:
                raise RuntimeError(f'userland rewrite hash mismatch: {source}')
            for path in item['paths']:
                entries.append(dict(source=str(source), path=path, uid=item['uid'],
                                    gid=item['gid'], mode=item['mode']))
        cache_source_root = BASE / 'mount-SystemOS/root/System/Library/Caches/com.apple.dyld'
        cache_target = '/System/Library/Caches/com.apple.dyld'
        for item in cache_report['files']:
            source = CACHE / item['name']
            if sha(source) != item['sha256']:
                raise RuntimeError(f'cache rewrite hash mismatch: {source}')
            original = cache_source_root / item['name']
            mode = f'{stat.S_IMODE(original.stat().st_mode):o}' if original.exists() else '644'
            uid = original.stat().st_uid if original.exists() else 0
            gid = original.stat().st_gid if original.exists() else 0
            entries.append(dict(source=str(source), path=cache_target + '/' + item['name'],
                                uid=uid, gid=gid, mode=mode))
        file_list = OUT / 'files.json'
        file_list.write_text(json.dumps(entries, indent=2) + '\n')
        report['rewritten_userland_images'] = len(user_report['images'])
        report['userland_failures'] = user_report['failures']
        report['rewritten_cache_files'] = len(cache_report['files'])
        report['trust_entries'] = trust_report['entries']
        report['trust_sha256'] = sha(TRUST)
        report['file_list_sha256'] = sha(file_list)
        container = BASE / 'OS-grown.apfs'
        if not container.is_file():
            raise RuntimeError('OS-grown.apfs is missing')
        report['input_container_sha256'] = sha(container)
        kernel = ROOT / 'venus-apfs-tools/guest/boot/vmlinuz-6.8.0-147-generic'
        module = ROOT / 'venus-apfs-tools/guest/lib/modules/6.8.0-147-generic/extra/apfs.ko'
        write_report = OUT / 'write.json'
        directories = set()
        for item in entries:
            directories.update(str(p) for p in Path(item['path']).parents if str(p) != '/')
        dir_file = OUT / 'directories.json'
        dir_file.write_text(json.dumps([dict(path=p, uid=0, gid=0, mode='755')
            for p in sorted(directories, key=lambda p: (p.count('/'), p))], indent=2) + '\n')
        run([python, '/mnt/g/UniXNU-Port/sources/UniXNU-zeta-none24smu/scripts/write-zeta-apfs-files.py',
             '--container', container, '--kernel', kernel, '--module', module,
             '--module-tree', ROOT / 'venus-apfs-tools/guest/lib/modules/6.8.0-147-generic/kernel',
             '--file-list', file_list, '--directory-list', dir_file, '--accel', args.accel,
             '--replace', '--report', write_report], OUT / 'write.log')
        write = json.loads(write_report.read_text())
        if write['failures']:
            raise RuntimeError('APFS guest write reported failures')
        report['write'] = dict(report=str(write_report), sha256=sha(write_report),
                               files=len(write['files']), bytes=sum(row['bytes'] for row in write['files']),
                               container_sha256=write['container_sha256'])
        run([ROOT / 'venus-apfs-tools/apfsprogs/apfsck/apfsck', container], OUT / 'apfsck.log')
        report['root_container'] = dict(path=str(container), bytes=container.stat().st_size,
                                        sha256=sha(container), apfsck=True)
        report['result'] = 'root-files-written-and-apfsck-passed'
    except Exception as error:
        report.update(result='failed', error=str(error))
        (OUT / 'root-report.json').write_text(json.dumps(report, indent=2) + '\n')
        raise
    (OUT / 'root-report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
