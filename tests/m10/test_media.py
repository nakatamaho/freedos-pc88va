# SPDX-License-Identifier: GPL-2.0-or-later
"""ROM-free fixed-loader-extent allocation and independent extraction tests."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('m10_media',ROOT/'tools/m10/media.py')
media=importlib.util.module_from_spec(spec);spec.loader.exec_module(media)


class MediaTests(unittest.TestCase):
    def setUp(self):
        self.spec=json.loads((ROOT/'config/m05/media.json').read_text())
        self.accepted=json.loads((ROOT/'qa/golden/m09/manifest.json').read_text())['artifacts']
        self.stage2=bytes([0x5a])*self.accepted['loader_stage2']['size']
        self.extents=[]

    def records(self,kernel_size=8192):
        values=[]
        for index,(name,size) in enumerate((('KERNEL.SYS',kernel_size),('COMMAND.COM',91143),('COUNTRY.SYS',42614))):
            data=bytes([index+1])*size
            values.append({'dos_name':name,'data':data,'size':size,
                           'sha256':hashlib.sha256(data).hexdigest(),'source_date_epoch':1787814827})
        return values

    def boot(self,extent):
        self.extents.append(extent)
        return b'\xeb\x3c\x90'+bytes(1021)

    def compose(self,records):
        return media.compose(self.spec,records,self.stage2,self.boot,{510:False,1022:False},self.accepted)

    def test_growing_kernel_keeps_loader_extent(self):
        for size in (6034,8192,16384):
            raw,d88,result=self.compose(self.records(size))
            self.assertTrue(result['payloads_verified'])
            self.assertTrue(result['round_trip_byte_identical'])
            chains=[set(a['clusters']) for a in result['allocations']]
            self.assertEqual(sum(map(len,chains)),len(set.union(*chains)))
        self.assertEqual(self.extents,[self.extents[0]]*3)

    def test_fragmentation_uses_accepted_fat_reader(self):
        raw,d88,result=self.compose(self.records())
        country=result['allocations'][2]['clusters']
        self.assertNotEqual(country,list(range(country[0],country[0]+len(country))))
        self.assertTrue(result['payloads_verified'])

    def test_two_compositions_byte_identical(self):
        self.assertEqual(self.compose(self.records()),self.compose(self.records()))

    def test_payload_digest_drift(self):
        records=self.records();records[0]['sha256']='0'*64
        with self.assertRaises(media.ValidationError):self.compose(records)

    def test_payload_size_drift(self):
        records=self.records();records[0]['size']+=1
        with self.assertRaises(media.ValidationError):self.compose(records)

    def test_capacity_overflow(self):
        with self.assertRaises(media.ValidationError):self.compose(self.records(2*1024*1024))

    def test_wrong_payload_set(self):
        records=self.records();records[0]['dos_name']='OTHER.SYS'
        with self.assertRaises(media.ValidationError):self.compose(records)

    def test_bootstrap_field_overlap_rejected(self):
        def invalid(extent):return b'\xeb\x3c\x90'+bytes([1])+bytes(1020)
        with self.assertRaises(media.ValidationError):
            media.compose(self.spec,self.records(),self.stage2,invalid,{510:False,1022:False},self.accepted)


if __name__=='__main__':unittest.main()
