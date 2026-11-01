#!/usr/bin/env python3
"""Check, or execute one separately authorized bounded iOS26 root recovery.

Default is local validation only. Execution starts in fastboot and flashes only
unixnu. There is no reboot, RAM boot, Android erase, or automatic retry.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys

PROJECT = Path(__file__).resolve().parents[3]
EVIDENCE = PROJECT / 'ports/UniXNU-venus/evidence'
SERIAL = '55870427'


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save(path, value):
    temporary = path.with_suffix('.new')
    with temporary.open('w', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, default=EVIDENCE / 'ios26-bounded-fragment-plan.json')
    parser.add_argument('--execute-authorized', action='store_true')
    parser.add_argument('--authorization', type=Path,
                        default=EVIDENCE / 'ios26-root-recovery-authorization.json')
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text(encoding='utf-8'))
    helper_path = Path(__file__).with_name('prepare-ios26-flash-fragments.py')
    spec = importlib.util.spec_from_file_location('bounded_root_fragments', helper_path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    source, raw = Path(plan['source']), Path(plan['raw'])
    if (plan['raw_sha256'] != helper.EXPECTED_RAW_SHA or
            plan['source_sha256'] != helper.EXPECTED_SPARSE_SHA or
            plan['expanded_bytes'] != helper.EXPECTED_RAW_BYTES or
            not plan['fragment_assigned_ranges_cover_entire_root'] or
            not plan['original_zero_blocks_written_as_fill']):
        raise RuntimeError('Transfer plan is not the complete pinned root')
    if sha(source) != plan['source_sha256'] or sha(raw) != plan['raw_sha256']:
        raise RuntimeError('Pinned root/complete sparse input changed')
    parts, total = helper.plan_fragments(source, 128 << 20)
    if parts != plan['fragments'] or total != plan['total_blocks']:
        raise RuntimeError('Stored fragment plan differs from the actual source')
    plan_sha = sha(args.plan)
    if not args.execute_authorized:
        print(json.dumps(dict(result='local-plan-verified', plan_sha256=plan_sha,
            fragments=len(parts), maximum_fragment_bytes=max(p['encoded_bytes'] for p in parts),
            expanded_bytes=plan['expanded_bytes'], expanded_sha256=plan['raw_sha256'],
            all_zero_ranges_written=True, phone_operations=False), indent=2))
        return 0

    authorization = json.loads(args.authorization.read_text(encoding='utf-8'))
    if (authorization.get('approved_by_user') is not True or
            authorization.get('serial') != SERIAL or
            authorization.get('partition') != 'unixnu' or
            authorization.get('expanded_sha256') != plan['raw_sha256'] or
            authorization.get('sparse_sha256') != plan['source_sha256'] or
            authorization.get('plan_sha256') != plan_sha or
            authorization.get('fragment_count') != len(parts)):
        raise RuntimeError('No matching authorization for this exact recovery transfer')
    journal = EVIDENCE / 'ios26-root-recovery-execution.json'
    log_path = PROJECT / 'logs/venus-ios26-root-recovery.log'
    work = source.parent / 'recovery-transfer-staging'
    if journal.exists() or log_path.exists() or work.exists():
        raise RuntimeError('Previous execution/staging exists; inspect it before any new operation')
    if not log_path.parent.is_dir():
        raise RuntimeError('Execution log parent missing')
    work.mkdir()
    fastboot = PROJECT / 'tools/platform-tools/fastboot.exe'
    if not fastboot.is_file():
        raise RuntimeError('Windows fastboot missing')
    record = dict(serial=SERIAL, partition='unixnu', plan_sha256=plan_sha,
                  source_sha256=plan['source_sha256'], expanded_sha256=plan['raw_sha256'],
                  executor_sha256=sha(Path(__file__)), helper_sha256=sha(helper_path),
                  fastboot_sha256=sha(fastboot), authorization_sha256=sha(args.authorization),
                  flash_started=False, flash_completed=False, fragment_count=len(parts),
                  acknowledged_fragments=[], commands=[], created_at=now(),
                  log=str(log_path), phone_reboot=False, ram_boot=False)

    def phase(name):
        record.update(phase=name, updated_at=now())
        save(journal, record)

    def command(argv, timeout=30):
        row = dict(argv=list(map(str, argv)), started_at=now(), result='started')
        record['commands'].append(row)
        phase(record['phase'])
        process = None
        try:
            with log_path.open('ab') as log:
                log.write(('\nCOMMAND ' + json.dumps(row) + '\n').encode())
                log.flush()
                os.fsync(log.fileno())
                process = subprocess.Popen(row['argv'], stdout=subprocess.PIPE,
                                           stderr=subprocess.STDOUT,
                                           stdin=subprocess.DEVNULL)
                try:
                    output, _ = process.communicate(timeout=timeout)
                except subprocess.TimeoutExpired:
                    process.kill()
                    output, _ = process.communicate()
                    log.write(output)
                    log.flush()
                    os.fsync(log.fileno())
                    raise TimeoutError('Device command deadline exceeded')
                log.write(output)
                log.flush()
                os.fsync(log.fileno())
            text = output.decode('utf-8', 'replace')
            print(text, end='', flush=True)
            row.update(result='finished', exit_code=process.returncode, output=text, finished_at=now())
            phase(record['phase'])
            if process.returncode:
                raise RuntimeError(f'Device command exited{process.returncode}')
            return text
        except BaseException:
            if process is not None and process.poll() is None:
                process.kill()
                process.wait()
            row.update(result='interrupted-or-failed', finished_at=now())
            phase('stopped-review-required')
            raise

    def variable(name):
        text = command([fastboot, '-s', SERIAL, 'getvar', name])
        match = re.search(r'(?:^|\n)\s*(?:\(bootloader\)\s*)?' + re.escape(name) + r':\s*(\S+)', text)
        if not match:
            raise RuntimeError('Missing fastboot variable:' + name)
        return match.group(1)

    phase('local-inputs-verified')
    try:
        if (variable('serialno') != SERIAL or variable('product') != 'venus' or
                variable('current-slot').lstrip('_') != 'a' or
                int(variable('partition-size:unixnu'), 0) != 68719476736 or
                int(variable('partition-size:userdata'), 0) != 172426788864 or
                variable('partition-type:unixnu') != 'raw'):
            raise RuntimeError('Device/slot/partition geometry mismatch')
        phase('fastboot-identity-and-geometry-verified')
        for part in parts:
            index = part['index']
            stage = work / f'fragment-{index:04}.sparse.img'
            phase(f'staging-fragment-{index:04}')
            helper.build_fragment(source, stage, part, total)
            verified = helper.verify_fragment(stage, raw, part, total)
            record['current_fragment'] = verified
            record['flash_started'] = True
            phase(f'flash-fragment-{index:04}-started')
            text = command([fastboot, '-s', SERIAL, '-S', '128M', 'flash', 'unixnu', stage], timeout=180)
            if not re.search(r"Writing\s+'unixnu'.*OKAY", text):
                raise RuntimeError('Missing explicit unixnu Writing OKAY acknowledgement')
            record['acknowledged_fragments'].append(verified)
            phase(f'flash-fragment-{index:04}-acknowledged')
            stage.unlink()  # Journal preserves the exact successful staged SHA.
        record['flash_completed'] = True
        phase('root-flash-completed-no-ram-boot')
        print('PASS: complete recovery transfer acknowledged; no RAM boot/reboot executed', flush=True)
        return 0
    except BaseException as error:
        record['error'] = f'{type(error).__name__}: {error}'
        phase('stopped-review-required')
        raise


if __name__ == '__main__':
    sys.exit(main())
