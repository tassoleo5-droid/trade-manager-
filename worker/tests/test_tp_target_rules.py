import unittest
from rule_engine import Position
from tp_target_rules import derive_stages

class TargetTests(unittest.TestCase):
    def test_buy_targets_from_initial_risk(self):
        p=Position('a', 44, True, 1.1, 1.095, 1.095, 1.101)
        levels=derive_stages(p,[1,2,3],[50,25,25])
        self.assertEqual([round(x.target_price,4) for x in levels],[1.105,1.11,1.115])
        self.assertEqual([x.percent_of_initial_volume for x in levels],[50,25,25])

    def test_sell_targets(self):
        p=Position('a',45,False,1.2,1.205,1.205,1.2)
        levels=derive_stages(p,[1,2],[50,50])
        self.assertEqual([round(x.target_price,4) for x in levels],[1.195,1.19])

    def test_missing_initial_risk_rejected(self):
        p=Position('a',44,True,1.1,1.1,1.1,1.105)
        with self.assertRaises(ValueError):
            derive_stages(p,[1],[100])

    def test_invalid_order_rejected(self):
        p=Position('a',44,True,1.1,1.095,1.095,1.105)
        with self.assertRaises(ValueError):
            derive_stages(p,[2,1],[50,50])

if __name__ == '__main__':
    unittest.main()
