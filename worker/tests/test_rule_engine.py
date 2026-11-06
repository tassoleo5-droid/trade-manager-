import unittest
from rule_engine import Position, plan_break_even

class BreakEvenPlannerTests(unittest.TestCase):
    def setUp(self):
        self.buy = Position("a", 123, True, 1.1000, 1.0950, 1.0950, 1.1060)

    def test_buy_after_one_r(self):
        action = plan_break_even(self.buy, 1.0)
        self.assertEqual(action.kind, "MOVE_SL_TO_ENTRY")
        self.assertEqual(action.stop_loss, 1.1)

    def test_before_threshold_no_action(self):
        p = Position("a", 123, True, 1.1, 1.095, 1.095, 1.102)
        self.assertIsNone(plan_break_even(p, 1.0))

    def test_existing_better_stop_never_worsened(self):
        p = Position("a", 123, True, 1.1, 1.095, 1.101, 1.106)
        self.assertIsNone(plan_break_even(p, 1.0))

    def test_sell_at_threshold(self):
        p = Position("a", 9, False, 1.2, 1.205, 1.205, 1.194)
        self.assertEqual(plan_break_even(p, 1.0).stop_loss, 1.2)

    def test_completed_action_is_not_replanned(self):
        self.assertIsNone(plan_break_even(self.buy, 1.0, frozenset({"a:123:BE"})))

    def test_invalid_initial_stop(self):
        p = Position("a", 123, True, 1.1, 1.105, 1.105, 1.11)
        self.assertIsNone(plan_break_even(p, 1.0))

if __name__ == "__main__":
    unittest.main()
