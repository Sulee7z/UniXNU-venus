#!/usr/bin/env python3
"""Prepare a complete RAW/FILL transfer using the first successful Venus recipe.

Every source block is covered, including explicit zero fills. Independently
decode from an empty base and compare the entire expanded hash before publishing
the transfer file. This script has no device commands.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

from venus_sparse import encode, inspect_complete

PROJECT = Path(__file__).resolve().parents[3]


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--report', required=True, type=Path)
    parser.add_argument('--expected-sha256', required=True)
    parser.add_argument('--expected-bytes', required=True, type=int)
    args = parser.parse_args()
    partial = args.output.with_suffix(args.output.suffix + '.partial')
    if any(path.exists() for path in (args.output, partial, args.report)):
        raise SystemExit('Output/partial/report exists; preserve it and use a new output name')
    if not args.output.parent.is_dir() or not args.report.parent.is_dir():
        raise SystemExit('Output and report parents must exist')
    if args.input.stat().st_size != args.expected_bytes:
        raise SystemExit('Raw source size differs from the pinned image')
    # Upper bound: every input block RAW plus one chunk header per block.
    bound = args.expected_bytes + args.expected_bytes // 4096 * 12 + (1 << 30)
    if shutil.disk_usage(args.output.parent).free < bound:
        raise SystemExit('Not enough staging space; preserve the pinned raw image')
    print('Encoding with the original RAW/FILL-only Venus encoder', flush=True)
    result = encode(args.input, partial)
    if (result['expanded_sha256'] != args.expected_sha256 or
            result['expanded_bytes'] != args.expected_bytes):
        raise SystemExit('Raw source hash/size changed during encoding')
    if inspect_complete(partial) != args.expected_bytes:
        raise SystemExit('Complete sparse extent check failed')
    reference_path = PROJECT / 'sources/UniXNU-zeta-reference/scripts/make-zeta-root-delta.py'
    spec = importlib.util.spec_from_file_location('independent_sparse', reference_path)
    reference = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reference)
    print('Independently decoding every block from an empty base', flush=True)
    with tempfile.TemporaryDirectory(prefix='venus-full-sparse-', dir=args.report.parent) as temporary:
        empty = Path(temporary) / 'empty-base'
        empty.write_bytes(b'')
        reconstructed = reference.apply_and_hash(empty, partial)
    if reconstructed != args.expected_sha256:
        raise SystemExit('Independent expanded SHA-256 differs')
    partial.rename(args.output)
    result.update(input=str(args.input.resolve()), sparse_path=str(args.output.resolve()),
                  sparse_bytes=args.output.stat().st_size, sparse_sha256=sha(args.output),
                  independent_expanded_sha256=reconstructed,
                  encoder_sha256=sha(Path(__file__).with_name('venus_sparse.py')),
                  independent_decoder_sha256=sha(reference_path),
                  complete_write_coverage=True, requires_existing_device_bytes=False,
                  fastboot_chunk_limit='128M', device_written=False,
                  prepared_at=datetime.now(timezone.utc).isoformat())
    with args.report.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    print('PASS: full RAW/FILL coverage, zero DONT_CARE, independent expanded SHA matches', flush=True)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    sys.exit(main())
