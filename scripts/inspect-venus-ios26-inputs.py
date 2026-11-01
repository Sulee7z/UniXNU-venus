#!/usr/bin/env python3
"""Inspect the pinned zeta iOS26 restore identity and local storage requirement."""
import argparse
import hashlib
import json
from pathlib import Path
import plistlib
import shutil
import sys
import tomllib
import urllib.request
import zipfile

PROJECT = Path('/mnt/g/UniXNU-Port')
sys.path.insert(0, str(PROJECT / 'sources/UniXNU-guide/scripts'))
from unixnu.ipsw import RangeFile


class CheckedRangeFile(RangeFile):
    def _block(self, index):
        if index in self.cache:
            return self.cache[index]
        start = index * self.block
        end = min(start + self.block, self.size) - 1
        request = urllib.request.Request(self.url, headers={
            'Range': f'bytes={start}-{end}', 'Accept-Encoding': 'identity'})
        with urllib.request.urlopen(request, timeout=120) as response:
            if response.status != 206 or response.headers['Content-Range'] != f'bytes {start}-{end}/{self.size}':
                raise RuntimeError('Unmatched HTTP range')
            data = response.read(end - start + 2)
        if len(data) != end - start + 1:
            raise RuntimeError('Incomplete or oversized range')
        if len(self.cache) >= 4:
            self.cache.pop(next(iter(self.cache)))
        self.cache[index] = data
        return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    board = PROJECT / 'sources/UniXNU-zeta-none24smu/board.toml'
    target = tomllib.loads(board.read_text())['ipsw']
    report = dict(target=target, source_board_sha256=hashlib.sha256(board.read_bytes()).hexdigest(),
                  backing_drive_free_bytes=shutil.disk_usage(PROJECT).free,
                  phone_operations=False, component_images_downloaded=False)
    try:
        with CheckedRangeFile(target['url'], block=2 << 20) as remote, zipfile.ZipFile(remote) as archive:
            raw = archive.read('BuildManifest.plist')
            manifest = plistlib.loads(raw)
            if (manifest['ProductVersion'], manifest['ProductBuildVersion']) != (target['version'], target['build']):
                raise RuntimeError('Restore version/build mismatch')
            if target['product'] not in manifest['SupportedProductTypes']:
                raise RuntimeError('Restore product mismatch')
            identities = [row for row in manifest['BuildIdentities']
                          if row['Info']['DeviceClass'] == target['device_class'] and
                          row['Info']['RestoreBehavior'] == 'Erase' and
                          int(row['ApChipID'], 16) == target['chip_id'] and
                          int(row['ApBoardID'], 16) == target['board_id']]
            report['matching_identities'] = [dict(info=row['Info'], available_components=sorted(row['Manifest']),
                components={name: row['Manifest'].get(name, {}).get('Info', {}).get('Path') for name in
                    ('OS', 'Cryptex1,SystemOS', 'KernelCache', 'DeviceTree',
                     'StaticTrustCache', 'Cryptex1,SystemTrustCache')}) for row in identities]
            complete = [(row, record) for row, record in zip(identities, report['matching_identities'])
                        if all(record['components'].values())]
            if complete:
                identities = [row for row, record in complete]
                selected_records = [record for row, record in complete]
            else:
                selected_records = report['matching_identities']
            if not complete or any(row['components'] != selected_records[0]['components']
                                     for row in selected_records):
                raise RuntimeError('Restore identity component paths are absent or ambiguous')
            report['manifest_sha256'] = hashlib.sha256(raw).hexdigest()
            report['source_zip_bytes'] = remote.size
            report['components'] = {}
            for name in ('OS', 'Cryptex1,SystemOS', 'KernelCache', 'DeviceTree',
                         'StaticTrustCache', 'Cryptex1,SystemTrustCache'):
                item = identities[0]['Manifest'].get(name)
                if item is None:
                    raise RuntimeError('Selected restore identity lacks component: ' + name)
                member = item['Info']['Path']
                info = archive.getinfo(member)
                report['components'][name] = dict(member=member, bytes=info.file_size,
                    compressed_bytes=info.compress_size, zip_crc32=f'{info.CRC:08x}',
                    aea=member.endswith('.aea'))
            report['result'] = 'identity-inspected'
    except Exception as error:
        report.update(result='failed', error=str(error))
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return 0 if report['result'] == 'identity-inspected' else 1


if __name__ == '__main__':
    sys.exit(main())
