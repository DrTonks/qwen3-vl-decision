import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from qwenlab import financial_jev_cache as cache
from qwenlab import financial_jev_reference as j


class OfflineCacheTests(unittest.TestCase):
    def test_hash_bound_replay_and_tampering_rejected_without_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);public=root/'public';data=root/'data';source=data/'evaluation/development.json'
            row={'id':'one','split':'development','annotation':{'action':'answer'},'input':{
                'message':'你好','state':{},'history':[],'images':[],'available_tools':[],
                'capabilities':{'knowledge_collections':[]}}}
            j.write(source,[row])
            protocol={'specification':j.specification(),'split_sha256':{'development':j.file_sha(source)}}
            pred={'id':'one','model':'jev-test','request_sha256':j.digest(j.payload(row))}
            j.write(public/'protocol.json',protocol)
            j.write(public/'completion.json',{'model':'jev-test','protocol_sha256':j.digest(protocol)})
            j.write(public/'development-predictions.json',[pred])
            j.write(public/'manifest.json',{'files':{p.name:j.file_sha(p) for p in public.iterdir()}})
            with patch.object(cache,'PUBLIC',public),patch.object(j,'DATA',data), \
                 patch.object(j,'source_rows',return_value=[row]), \
                 patch.object(j.urllib.request,'build_opener',side_effect=AssertionError('Network prohibited')):
                _,actual,_=cache.load_cached('development');self.assertEqual(actual,[pred])
                j.write(public/'development-predictions.json',[dict(pred,model='changed')])
                with self.assertRaisesRegex(ValueError,'integrity'):cache.load_cached('development')


if __name__=='__main__':unittest.main()
