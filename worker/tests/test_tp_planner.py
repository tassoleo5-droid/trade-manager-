import unittest
from rule_engine import Position
from tp_planner import TakeProfitStage, plan_take_profit


class TakeProfitTests(unittest.TestCase):
    def setUp(self):
        self.buy = Position("acct1", 42, True, 1.1000, 1.0950, 1.0950, 1.1060)
        self.stages = [
            TakeProfitStage(1.1050, 50),
            TakeProfitStage(1.1100, 25),
            TakeProfitStage(1.1150, 25),
        ]

    def plan(self, **overrides):
        kw = {
            "initial_volume": 1.0,
            "current_volume": 1.0,
            "stages": self.stages,
            "minimum_volume": 0.01,
            "volume_step": 0.01,
        }
        kw.update(overrides)
        return plan_take_profit(self.buy, **kw)

    def test_first_stage_only_is_planned(self):
        action = self.plan()
        self.assertEqual(action.kind, "PARTIAL_CLOSE")
        self.assertEqual(action.volume, 0.5)
        self.assertEqual(action.key, "acct1:42:TP1")

    def test_does_not_repeat_pending_stage(self):
        self.assertIsNone(self.plan(pending=frozenset({"acct1:42:TP1"})))

    def test_does_not_skip_stage(self):
        self.assertIsNone(self.plan(completed=frozenset({"acct1:42:TP2"})))

    def test_second_stage_requires_confirmation(self):
        p = Position("acct1", 42, True, 1.1000, 1.0950, 1.0950, 1.1120)
        result = plan_take_profit(p, initial_volume=1, current_volume=.5,
                                 stages=self.stages, minimum_volume=.01, volume_step=.01,
                                 completed=frozenset({"acct1:42:TP1"}))
        self.assertEqual(result.kind, "PARTIAL_CLOSE")
        self.assertEqual(result.volume, 0.25)

    def test_last_stage_closes_only_after_prior_confirmed(self):
        p = Position("acct1", 42, True, 1.1, 1.095, 1.095, 1.116)
        result = plan_take_profit(p, initial_volume=1, current_volume=.25,
                                 stages=self.stages, minimum_volume=.01, volume_step=.01,
                                 completed=frozenset({"acct1:42:TP1","acct1:42:TP2"}))
        self.assertEqual(result.kind, "CLOSE_POSITION")

    def test_broker_minimum_lot_blocks_unsafe_partial(self):
        self.assertIsNone(self.plan(initial_volume=.01, current_volume=.01,
                                    minimum_volume=.01, volume_step=.01))

    def test_rejects_targets_on_wrong_side_of_entry(self):
        self.assertIsNone(self.plan(stages=[TakeProfitStage(1.09,50),TakeProfitStage(1.11,25),TakeProfitStage(1.12,25)]))

    def test_sell_first_stage(self):
        p = Position("acct1", 42, False, 1.200, 1.205, 1.205, 1.195)
        result = plan_take_profit(p, initial_volume=2, current_volume=2,
                                 stages=[TakeProfitStage(1.196,50), TakeProfitStage(1.19,50)],
                                 minimum_volume=.01, volume_step=.01)
        self.assertEqual(result.volume, 1)

if __name__ == "__main__":
    unittest.main()
