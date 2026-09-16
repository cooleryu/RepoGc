import unittest

from repogc.review import _headline, _what_was_found


class ReviewWordingTests(unittest.TestCase):
    def test_markdown_link_is_not_called_code_or_configuration(self):
        messages = _what_was_found([{"category": "broken_reference", "evidence_kind": "markdown_link",
                                    "evidence_strength": "strong"}])
        self.assertIn("referenced path", messages[0])
        self.assertNotIn("code or configuration", messages[0])

    def test_unchecked_task_is_not_called_old_status(self):
        findings = [{"category": "unimplemented_marker", "evidence_kind": "unchecked_task_marker",
                     "evidence_strength": "review"}]
        self.assertIn("unfinished-work", _headline(findings))
        self.assertNotIn("status statement", " ".join(_what_was_found(findings)))

    def test_mixed_status_and_tasks_keep_both_observations(self):
        findings = [{"category": "unimplemented_marker", "evidence_kind": "operational_state_marker"},
                    {"category": "unimplemented_marker", "evidence_kind": "unchecked_task_marker"}]
        messages = _what_was_found(findings)
        self.assertEqual(len(messages), 2)
        self.assertIn("1 point-in-time", messages[0])
        self.assertIn("1 unfinished-work", messages[1])
        self.assertIn("Work and status", _headline(findings))
