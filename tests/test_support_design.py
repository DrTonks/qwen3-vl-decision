import unittest
from qwenlab.support_design import build_rows, validate


class SupportDesignTests(unittest.TestCase):
    def test_full_draft_remains_unreviewed(self):
        rows=build_rows()
        self.assertTrue(validate(rows))
        self.assertTrue(all('labels' not in r for r in rows))
        self.assertTrue(all(r['review']['final_action'] is None for r in rows))

    def test_meaningful_state_changes_are_kept_together(self):
        group=[r for r in build_rows() if r['scenario_group']=='B01']
        self.assertEqual(len({r['inputs']['message'] for r in group}),1)
        self.assertEqual([r['proposal']['action'] for r in group],['tool','answer','tool','answer'])

    def test_gateway_cases_never_request_a_tool(self):
        rows=[r for r in build_rows() if r['requirement']['handling_layer']=='gateway']
        self.assertEqual(len(rows),12)
        self.assertTrue(all(r['proposal']['tool'] is None for r in rows))

    def test_reading_a_draft_does_not_prelabel_intent_in_state(self):
        rows=build_rows()
        for row in rows:
            self.assertFalse(set(row['inputs']['state']) & {'action','route','intent','requested_operation','requested_fact','reported_issue'})
        correction=next(r for r in rows if r['id']=='M02-1')
        self.assertEqual(correction['proposal']['arguments'],{'applicationId':76002})


if __name__=='__main__': unittest.main()
