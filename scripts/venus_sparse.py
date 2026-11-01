"""Complete Android sparse encoding: bounded RAW/FILL chunks, never DONT_CARE."""
import hashlib
import os
import struct

BLOCK = 4096
WINDOW = 8 * 1024 * 1024
MAGIC, RAW, FILL = 0xed26ff3a, 0xcac1, 0xcac2
ZERO = bytes(BLOCK)

def encode(source, output):
    size = source.stat().st_size
    if not size or size % BLOCK or size // BLOCK > 0xffffffff:
        raise ValueError('Require nonempty whole 4096-byte blocks within sparse v1 extent')
    digest = hashlib.sha256()
    chunks = raw_blocks = fill_blocks = 0
    with source.open('rb') as src, output.open('xb') as dst:
        dst.write(bytes(28))
        for data in iter(lambda: src.read(WINDOW), b''):
            if len(data) % BLOCK: raise ValueError('Input changed during encoding')
            digest.update(data)
            first = 0
            while first < len(data):
                zero = data[first:first+BLOCK] == ZERO
                end = first + BLOCK
                while end < len(data) and (data[end:end+BLOCK] == ZERO) == zero:
                    end += BLOCK
                blocks = (end-first)//BLOCK
                if zero:
                    dst.write(struct.pack('<HHII', FILL, 0, blocks, 16) + bytes(4))
                    fill_blocks += blocks
                else:
                    dst.write(struct.pack('<HHII', RAW, 0, blocks, 12 + end-first))
                    dst.write(data[first:end]); raw_blocks += blocks
                chunks += 1; first = end
        if (raw_blocks + fill_blocks) * BLOCK != size: raise ValueError('Input extent changed')
        dst.seek(0)
        dst.write(struct.pack('<IHHHHIIII', MAGIC, 1, 0, 28, 12, BLOCK, size//BLOCK, chunks, 0))
        dst.flush(); os.fsync(dst.fileno())
    return {'expanded_bytes': size, 'expanded_sha256': digest.hexdigest(), 'chunks': chunks,
            'raw_blocks': raw_blocks, 'fill_blocks': fill_blocks, 'dont_care_blocks': 0}

def inspect_complete(path):
    with path.open('rb') as f:
        header = f.read(28)
        if len(header) != 28: raise ValueError('Truncated sparse header')
        magic, major, minor, hs, cs, block, total, count, checksum = struct.unpack('<IHHHHIIII', header)
        if (magic, major, minor, hs, cs, block, checksum) != (MAGIC, 1, 0, 28, 12, BLOCK, 0) or not total or not count:
            raise ValueError('Unsupported sparse header')
        covered = 0
        for _ in range(count):
            chunk = f.read(12)
            if len(chunk) != 12: raise ValueError('Truncated sparse chunk')
            kind, reserved, blocks, size = struct.unpack('<HHII', chunk)
            if reserved or not blocks or blocks > total-covered: raise ValueError('Invalid chunk extent')
            if kind == RAW:
                if blocks * BLOCK > WINDOW or size != 12 + blocks * BLOCK: raise ValueError('Invalid/unbounded RAW chunk')
                payload = blocks * BLOCK
            elif kind == FILL:
                if size != 16: raise ValueError('Invalid FILL chunk')
                payload = 4
            else:
                raise ValueError('Complete image cannot contain skipped or unknown chunks')
            if len(f.read(payload)) != payload: raise ValueError('Truncated chunk payload')
            covered += blocks
        if covered != total or f.read(1): raise ValueError('Incomplete extent or trailing bytes')
    return total * BLOCK
