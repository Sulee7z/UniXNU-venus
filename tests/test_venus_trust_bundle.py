import struct
import sys
from pathlib import Path
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'package/Metal13'))
from venus_trust_bundle import entries,merge_static


def bundle(*rows):
    modules=[struct.pack('<I16sI',2,bytes(16),len(items))+b''.join(key+attrs for key,attrs in items) for items in rows]
    starts=[];at=4+4*len(modules)
    for module in modules:starts.append(at);at+=len(module)
    return struct.pack('<I',len(modules))+struct.pack('<'+str(len(starts))+'I',*starts)+b''.join(modules)


class TrustBundleTests(unittest.TestCase):
    a=(bytes([1])*20,bytes([2,1,7,0]))
    b=(bytes([2])*20,bytes([2,0,0,0]))
    owner=(bytes([3])*20,bytes([2,0,0,0]))

    def test_every_original_attribute_is_in_first_static_module(self):
        original=bundle([self.a],[self.b])
        old=bundle([self.owner],[self.a],[self.b])
        # Model the first-module-only view of the public static loader policy.
        first=struct.unpack_from('<I',old,4)[0];end=struct.unpack_from('<I',old,8)[0]
        first_only=struct.pack('<II',1,8)+old[first:end]
        self.assertNotIn(self.a[0],entries(first_only))
        fixed,report=merge_static(original,[self.owner])
        self.assertEqual(struct.unpack_from('<II',fixed),(1,8))
        self.assertEqual(entries(fixed),dict([self.a,self.b,self.owner]))
        self.assertTrue(report['all_original_attributes_preserved'])
        self.assertEqual(report['new_entries'],1)

    def test_same_entry_deduplicates_deterministically(self):
        original=bundle([self.a],[self.a])
        fixed,_=merge_static(original,[self.a,self.owner,self.owner])
        again,_=merge_static(original,[self.owner,self.a])
        self.assertEqual(fixed,again)
        self.assertEqual(len(entries(fixed)),2)

    def test_attribute_changes_are_rejected(self):
        with self.assertRaises(ValueError):merge_static(bundle([self.a]),[(self.a[0],bytes([2,0,0,0]))])
        with self.assertRaises(ValueError):entries(bundle([self.a],[(self.a[0],bytes([2,0,0,0]))]))

    def test_malformed_extents_and_entries_are_rejected(self):
        for data in (b'',bytes(8),bundle([self.a])[:-1],bundle([self.b,self.a]),bundle([self.a,self.a])):
            with self.subTest(data=data[:8]),self.assertRaises(ValueError):entries(data)
        for owner in ((bytes(19),bytes([2,0,0,0])),(bytes(20),bytes([0,0,0,0])),(bytes(20),bytes([2,0,0,1]))):
            with self.subTest(owner=owner),self.assertRaises(ValueError):merge_static(bundle([self.a]),[owner])


if __name__=='__main__':unittest.main()
