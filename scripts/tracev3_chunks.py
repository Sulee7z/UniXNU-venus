#!/usr/bin/env python3
"""Bounded tracev3 preamble/chunkset decoding; not an os_log event parser.

Format cross-check: mandiant/macos-UnifiedLogs src/preamble.rs, src/chunkset.rs.
Use declared little-endian sizes and bv41/bv4-/bv4$; never guess page boundaries.
"""
import struct

MAX_BLOCK=4<<20


def lz4_block(data, expected):
    if not 0<=expected<=MAX_BLOCK:raise ValueError('Invalid LZ4 output size')
    out=bytearray();at=0
    def length(value):
        nonlocal at
        if value==15:
            while True:
                if at>=len(data):raise ValueError('Truncated LZ4 length')
                extra=data[at];at+=1;value+=extra
                if extra!=255:break
        return value
    while at<len(data):
        token=data[at];at+=1
        literals=length(token>>4)
        if at+literals>len(data) or len(out)+literals>expected:
            raise ValueError('LZ4 literal bounds')
        out.extend(data[at:at+literals]);at+=literals
        if at==len(data):break
        if at+2>len(data):raise ValueError('Truncated LZ4 offset')
        offset=int.from_bytes(data[at:at+2],'little');at+=2
        match=length(token&15)+4
        if not offset or offset>len(out) or len(out)+match>expected:
            raise ValueError('LZ4 match bounds')
        pattern=out[-offset:]
        copies,remainder=divmod(match,offset)
        out.extend(pattern*copies);out.extend(pattern[:remainder])
    if len(out)!=expected:raise ValueError('LZ4 output length mismatch')
    return bytes(out)


def chunks(blob):
    at=0
    while at<len(blob):
        if len(blob)-at<16:
            if not any(blob[at:]):return
            raise ValueError(f'Truncated preamble at {at:#x}')
        tag,sub,size=struct.unpack_from('<IIQ',blob,at)
        end=at+16+size
        if not tag or end>len(blob):raise ValueError(f'Invalid chunk range at {at:#x}')
        yield at,tag,sub,blob[at+16:end]
        padded=(end+7)&~7
        if any(blob[end:min(padded,len(blob))]):raise ValueError('Nonzero alignment padding')
        at=padded


def chunkset(body):
    if len(body)<12:raise ValueError('Truncated chunkset')
    signature=body[:4];size=int.from_bytes(body[4:8],'little')
    if size>MAX_BLOCK:raise ValueError('Chunkset exceeds bound')
    if signature==b'bv41':
        packed=int.from_bytes(body[8:12],'little');end=12+packed
        if end+4!=len(body):raise ValueError('Chunkset compressed length mismatch')
        decoded=lz4_block(body[12:end],size)
    elif signature==b'bv4-':
        end=8+size
        if end+4!=len(body):raise ValueError('Chunkset plain length mismatch')
        decoded=body[8:end]
    else:raise ValueError('Unsupported chunkset signature: '+signature.hex())
    if body[end:end+4]!=b'bv4$':raise ValueError('Wrong chunkset footer')
    return decoded
