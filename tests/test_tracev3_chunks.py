import struct
import sys
from pathlib import Path
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from tracev3_chunks import chunks,chunkset,lz4_block


class TraceChunksTest(unittest.TestCase):
    def test_literal_and_overlapping_match(self):
        self.assertEqual(lz4_block(b'\x50hello',5),b'hello')
        self.assertEqual(lz4_block(b'\x32abc\x03\x00\x50final',14),b'abcabcabcfinal')

    def test_bad_lengths_offsets_and_sizes(self):
        for data,size in ((b'\x50abc',5),(b'\xf0',20),(b'\x10a\x00\x00',5),
                          (b'\x10a\x02\x00',5),(b'\x50hello',4),(b'\x50hello',6)):
            with self.subTest(data=data,size=size),self.assertRaises(ValueError):lz4_block(data,size)

    def test_framing_and_footer(self):
        plain=b'bv4-'+struct.pack('<I',5)+b'hello'+b'bv4$'
        packed=b'bv41'+struct.pack('<II',5,6)+b'\x50hello'+b'bv4$'
        self.assertEqual(chunkset(plain),b'hello');self.assertEqual(chunkset(packed),b'hello')
        for data in (packed[:-1],packed[:-4]+b'bad!',packed+b'\0',b'BAD!'+packed[4:]):
            with self.assertRaises(ValueError):chunkset(data)
        blob=struct.pack('<IIQ',0x600d,17,len(plain))+plain+bytes((-len(plain))%8)
        self.assertEqual(list(chunks(blob)),[(0,0x600d,17,plain)])
        with self.assertRaises(ValueError):list(chunks(blob[:16+len(plain)-1]))
        with self.assertRaises(ValueError):list(chunks(blob[:-1]+b'x'))


if __name__=='__main__':unittest.main()
