import json
import tempfile
import unittest
from pathlib import Path
from analysis.audit_v33 import paired_ablation, verify_mapping

class TestAuditV33(unittest.TestCase):
    def test_paired(self):
        r={'classification':'RETROSPECTIVE','weeks':[{'week':6,'result':{'actual':68},'all_models':{
            'baseline_5w__f000':{'actual':67,'absolute_error':2},
            'baseline_5w__f050':{'actual':68,'absolute_error':1}}}]}
        a=paired_ablation(r)
        self.assertEqual(a['by_model']['baseline_5w']['total_fixture_gain'],1)
        self.assertEqual(a['selected_total'],68)
    def test_unverified_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            c=Path(d)/'c.json';o=Path(d)/'o.json'
            c.write_text(json.dumps({'clubs':[]}));o.write_text(json.dumps({'source_type':'INFERRED','clubs':[]}))
            with self.assertRaises(ValueError):verify_mapping(c,o)
    def test_mismatch_detected(self):
        with tempfile.TemporaryDirectory() as d:
            c=Path(d)/'c.json';o=Path(d)/'o.json'
            c.write_text(json.dumps({'clubs':[{'club_id':i,'team_name':f'T{i}'} for i in range(1,19)]}))
            o.write_text(json.dumps({'source_type':'OFFICIAL_FANTASY_API','source_url':'https://example.org/api',
            'captured_utc':'2026-10-28T12:00:00Z','clubs':[{'club_id':i,'team_name':f'X{i}' if i==2 else f'T{i}'} for i in range(1,19)]}))
            self.assertEqual(verify_mapping(c,o)['status'],'MISMATCH')
if __name__=='__main__':unittest.main()
