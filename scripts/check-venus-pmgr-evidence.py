#!/usr/bin/env python3
"""Bind the PMGR build, real runtime cases and phone candidate to exact hashes."""
import hashlib
import json
from pathlib import Path

root = Path('/mnt/g/UniXNU-Port')
artifact = root / 'artifacts/venus-guide-pmgr'
device = root / 'ports/UniXNU-venus'
build = Path('/root/unixnu-build/venus-guide-out/venus/ipados-17.7.11-21H461/venus/tree/build/sheng-platform-power')

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def need(condition, message):
    if not condition:
        raise SystemExit(message)

kernel_hash = sha(artifact / 'kernel/kernel.macho')
cases = {}
for mode in ('lifecycle', 'publish', 'refusal', 'amfi'):
    path = artifact / ('qemu-' + mode) / 'pmgr-checked.json'
    case = json.loads(path.read_text())
    need(case['kernel_sha256'] == kernel_hash and case['mode'] == mode, 'Mismatched PMGR case')
    if mode == 'amfi':
        need(case['amfi_lookup_qualified'], 'Original AMFI did not complete the actual lookup/call')
    cases[mode] = case
payload = json.loads((artifact / 'phone/payload.json').read_text())
verify = json.loads((artifact / 'phone/verification.json').read_text())
need(payload['kernel_sha256'] == kernel_hash, 'Payload source kernel differs')
need(sha(artifact / 'phone/kernel.macho') == payload['payload_kernel_sha256'], 'Payload kernel differs')
need(sha(artifact / 'phone/boot-venus-unixnu.img') == verify['sha256'] and verify['roundtrip_verified'], 'Boot image differs')
need(payload['kernel_args'].split().count('sheng-pmgr=2') == 1, 'Wrong PMGR publication selection')
root_reports = {}
for key, path, expected_hash in [('kernel', artifact / 'qemu-root-finder/gdb-stop.json', kernel_hash),
                                ('payload', artifact / 'phone/qemu-root-finder/gdb-stop.json', payload['payload_kernel_sha256'])]:
    report = json.loads(path.read_text())
    need(report['kernel_sha256'] == expected_hash and report['stop_symbol'] == '_IOFindBSDRoot' and
         not report['bounded_timeout_interrupted'], 'Root-finder entry not observed for ' + key)
    state = report['sheng_pmgr_observation']
    need(state['stage'] == 5 and state['status'] == 0 and state['attached'] == 1 and state['registered'] == 2,
         'Published PMGR state missing for ' + key)
    root_reports[key] = {'report_sha256': sha(path), 'stop_symbol': report['stop_symbol'], 'state': state}
build_report = json.loads((build / 'build-report.json').read_text())
need(sha(build / 'libShengPlatformPower.a') == build_report['archive_sha256'], 'Archive differs from its build report')
need(sha(device / 'package/ShengPlatformPower.cpp') == build_report['source_sha256'], 'PMGR source changed after build')
result = {'upstream_revision': '16e592abee8a550dec8154ed1f38b5ebc4f16213',
          'reference_revision': '0e1f6e52638137db15905db8d775ad73757f39fa',
          'build': build_report, 'build_inputs': json.loads((build / 'venus-inputs.json').read_text()),
          'cases': cases, 'root_finder': root_reports, 'candidate': verify, 'payload': payload,
          'phone_tested': False, 'root_mounted': False, 'ios_userspace_booted': False,
          'functional_power_backend': False}
(device / 'evidence/pmgr-integration.json').write_text(json.dumps(result, indent=2) + '\n')
print('PASS: PMGR lifecycle/publication/refusal/original-AMFI cases and both kernel/payload root-finder entries')
print('Candidate:', verify['sha256'], verify['bytes'])
