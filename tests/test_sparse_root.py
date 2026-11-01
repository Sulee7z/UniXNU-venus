import hashlib
import importlib.util
from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from venus_sparse import BLOCK, encode, inspect_complete
root = Path('/mnt/g/UniXNU-Port')
spec = importlib.util.spec_from_file_location('reference_sparse', root/'sources/UniXNU-zeta-reference/scripts/make-zeta-root-delta.py')
reference = importlib.util.module_from_spec(spec); spec.loader.exec_module(reference)

class SparseRoot(unittest.TestCase):
    def test_complete_reconstruction_without_existing_disk_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary); empty = work/'empty'; empty.write_bytes(b'')
            cases = [bytes(BLOCK*4), b'A'*BLOCK + bytes(BLOCK*2) + b'B'*BLOCK,
                     b'x'*(9*1024*1024) + bytes(BLOCK)]
            for i, data in enumerate(cases):
                raw, sparse = work/f'{i}.raw', work/f'{i}.sparse'
                raw.write_bytes(data); report = encode(raw, sparse)
                self.assertEqual(inspect_complete(sparse), len(data))
                self.assertEqual(report['dont_care_blocks'], 0)
                self.assertEqual(reference.apply_and_hash(empty, sparse), hashlib.sha256(data).hexdigest())
    def test_skips_truncation_and_trailing_bytes_refuse(self):
        with tempfile.TemporaryDirectory() as temporary:
            work=Path(temporary); raw=work/'raw'; raw.write_bytes(bytes(BLOCK)); sparse=work/'sparse'
            encode(raw,sparse); good=sparse.read_bytes()
            skipped=bytearray(good); struct.pack_into('<H',skipped,28,0xcac3)
            for bad in (bytes(skipped), good[:-1], good+b'\0'):
                sparse.write_bytes(bad)
                with self.assertRaises(ValueError): inspect_complete(sparse)
    def test_unaligned_input_refuses(self):
        with tempfile.TemporaryDirectory() as temporary:
            raw=Path(temporary)/'raw'; raw.write_bytes(b'bad')
            with self.assertRaises(ValueError): encode(raw,Path(temporary)/'output')

if __name__ == '__main__': unittest.main()
