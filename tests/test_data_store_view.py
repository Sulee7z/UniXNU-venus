"""Regression coverage for forensic EOF, sparse extents and capture validation."""
import hashlib
import json
from pathlib import Path
import plistlib
import struct
import sys
import tempfile
import unittest

DEVICE=Path(__file__).resolve().parents[1];ROOT=DEVICE.parents[1]
sys.path.insert(0,str(DEVICE/'scripts'))
import data_store_view as store


def inode(size, allocated=4096):
    # APFS fixed inode prefix + NAME (3 bytes padded to8) + DSTREAM (40).
    value=bytearray(92)
    struct.pack_into('<Q',value,8,42)
    struct.pack_into('<H',value,80,0o100600)
    return bytes(value)+struct.pack('<HHBBHBBH',2,48,4,2,3,8,32,40)+b'x\0\0'+bytes(5)+struct.pack('<5Q',size,allocated,0,0,0)


class FakeDisk:
    length=8*4096
    def __init__(self,data):self.data=data
    def read_at(self,at,n):return self.data[at:at+n]


class FakeVolume:
    def __init__(self,value,spans):self.value=value;self.spans=spans
    def lookup(self,path):return 12
    def records(self,oid,kind):
        if kind==3:return [(b'',self.value)]
        return [(struct.pack('<QQ',0,lo),struct.pack('<3Q',n,pa,crypto)) for lo,n,pa,crypto in self.spans]


class APFS: TYPE_INODE=3;TYPE_FILE_EXTENT=8


class ForensicTests(unittest.TestCase):
    def test_plist_eof_is_not_allocation_end(self):
        wanted=plistlib.dumps({'scale':2},fmt=plistlib.FMT_BINARY)
        disk=FakeDisk(bytes(4096)+wanted+bytes(4096-len(wanted)))
        actual=store.read_file(disk,APFS,FakeVolume(inode(len(wanted)),[(0,4096,1,0)]),'/cache')
        self.assertEqual(actual,wanted)
        self.assertEqual(plistlib.loads(actual),{'scale':2})
        with self.assertRaises(plistlib.InvalidFileException):plistlib.loads(actual+bytes(10))

    def test_explicit_sparse_hole(self):
        disk=FakeDisk(bytes(4096)+b'A'*4096)
        actual=store.read_file(disk,APFS,FakeVolume(inode(4110),[(0,4096,1,0),(4096,4096,0,0)]),'/log')
        self.assertEqual(actual,b'A'*4096+bytes(14))

    def test_encryption_or_missing_data_never_becomes_zero(self):
        for spans in ([(0,4096,1,7)],[],[(4096,4096,1,0)]):
            with self.subTest(spans=spans),self.assertRaises(ValueError):
                store.read_file(FakeDisk(bytes(8192)),APFS,FakeVolume(inode(4096),spans),'/log')

    def test_truncated_inode(self):
        for cut in (0,80,95,104,143):
            with self.subTest(cut=cut),self.assertRaises(ValueError):store.inode_info(inode(16)[:cut])

    def test_real_saved_cache_and_capture_bounds(self):
        run=ROOT/'artifacts/venus-data-forensics/read-20261029T031220Z'
        view,apfs,volume=store.open_volume(run,ROOT/'artifacts/venus-deployment/Data.dbr',ROOT)
        with view:
            path='/containers/Shared/SystemGroup/systemgroup.com.apple.mobilegestaltcache/Library/Caches/com.apple.MobileGestalt.plist'
            data=store.read_file(view,apfs,volume,path)
            self.assertEqual(len(data),7477)
            decoded=plistlib.loads(data)
            self.assertEqual(struct.unpack('<3i2fi',decoded['CacheExtra']['oBbtJ8x+s1q0OkaiocPuog']),(-1,-1,-1,0.0,-1.0,-1))
            with self.assertRaises(ValueError):view.read_at(-1,1)
            with self.assertRaises(ValueError):view.page(view.pages)
            self.assertEqual(view.read_at(view.length,10),b'')
        # Metadata mismatch is rejected before any page files are opened.
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as directory:
            temp=Path(directory)
            index=json.loads((run/'index.json').read_text())
            (temp/'index.json').write_text(json.dumps(index))
            blob=bytearray((run/'metadata.bin').read_bytes());blob[1]^=1
            (temp/'metadata.bin').write_bytes(blob)
            with self.assertRaisesRegex(ValueError,'Metadata SHA'):
                store.DataView(temp,ROOT/'artifacts/venus-deployment/Data.dbr',ROOT)
            # A declared-short run must not be accepted as all-zero data.
            (temp/'metadata.bin').write_bytes((run/'metadata.bin').read_bytes())
            (temp/'run-00000.bin').write_bytes(bytes(4096))
            with self.assertRaisesRegex(ValueError,'Short/oversized'):
                store.DataView(temp,ROOT/'artifacts/venus-deployment/Data.dbr',ROOT)


if __name__=='__main__':unittest.main()
