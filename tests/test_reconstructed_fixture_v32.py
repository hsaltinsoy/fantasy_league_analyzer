import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from analysis.walkforward_v32 import load_snapshots

class ReconstructedFixtureTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(Path('historical_data/fixtures_reconstructed_gw5_gw9.json').read_text(encoding='utf-8'))
    def load(self, obj, allow=True):
        with TemporaryDirectory() as d:
            p = Path(d) / 'fixtures.json'
            p.write_text(json.dumps(obj), encoding='utf-8')
            return load_snapshots(p, [5,6,7,8,9], allow_reconstructed=allow)
    def test_reject_by_default(self):
        with self.assertRaisesRegex(ValueError, 'allow-reconstructed'):
            self.load(self.data, False)
    def test_all_teams_covered(self):
        maps=self.load(self.data)
        self.assertEqual(len(maps), 5)
        for week in maps:
            self.assertEqual(len(maps[week]),18)
            for club, opponent in maps[week].items():
                self.assertEqual(maps[week][opponent],club)
    def test_duplicate_fails(self):
        self.data['weeks']['5']['matches'][1]['home_club_id_candidate']=self.data['weeks']['5']['matches'][0]['home_club_id_candidate']
        with self.assertRaisesRegex(ValueError,'duplicate'):
            self.load(self.data)
    def test_missing_match_fails(self):
        self.data['weeks']['6']['matches'].pop()
        with self.assertRaisesRegex(ValueError,'expected 9'):
            self.load(self.data)

if __name__=='__main__': unittest.main()
