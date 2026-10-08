from copy import deepcopy
import unittest

from qwenlab.financial_contract_revision import check_proposals


class ReviewPacketTests(unittest.TestCase):
    def fixtures(self):
        annotation = dict(action='answer', tool_name=None, tool_arguments={}, retrieval_collection=None,
                          missing_slots=[], reason='这是一个完整的能力说明', evidence_paths=['input.message'], policy_version='old')
        queue = [dict(id='train-A', source_row_sha256='source-hash', original_annotation=annotation,
                      input=dict(state={'authenticated': True}, capabilities={'knowledge_collections': []}, available_tools=[]))]
        target = deepcopy(annotation); target['policy_version'] = 'financial-support-contract-draft-v2'
        proposals = [dict(id='train-A', source_row_sha256='source-hash', decision='retain', proposed_annotation=target,
                          reason='明确保留原有能力问答的判断', evidence_paths=['input.message'], reviewer_type='ai_author',
                          human_reviewed=False, training_eligible=False)]
        return queue, proposals

    def test_rejects_missing_or_duplicate_rows(self):
        q, p = self.fixtures()
        check_proposals(q, p)
        for bad in ([], p + p):
            with self.assertRaises(ValueError): check_proposals(q, bad)

    def test_rejects_changed_source_and_false_eligibility(self):
        q, p = self.fixtures()
        for change in [dict(source_row_sha256='changed'), dict(training_eligible=True), dict(human_reviewed=True)]:
            bad = deepcopy(p); bad[0].update(change)
            with self.assertRaises(ValueError): check_proposals(q, bad)

    def test_retain_cannot_hide_changed_target(self):
        q, p = self.fixtures(); p[0]['proposed_annotation']['action'] = 'human'
        with self.assertRaises(ValueError): check_proposals(q, p)
        p[0]['decision'] = 'revise'; check_proposals(q, p)

    def test_quarantine_cannot_publish_a_label(self):
        q, p = self.fixtures(); p[0]['decision'] = 'quarantine'
        with self.assertRaises(ValueError): check_proposals(q, p)
        p[0]['proposed_annotation']['action'] = None
        check_proposals(q, p)


if __name__ == '__main__': unittest.main()
