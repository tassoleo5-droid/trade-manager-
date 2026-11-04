import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from watch_fusion_demo import snapshot, watch


class FusionDemoWatcherTests(unittest.TestCase):
    @staticmethod
    def terminal(mode=0, server="FusionMarkets-Demo", positions=()):
        t=Mock()
        t.ACCOUNT_TRADE_MODE_DEMO=0
        t.initialize.return_value=True
        t.account_info.return_value=SimpleNamespace(
            server=server, trade_mode=mode)
        t.positions_get.return_value=positions
        return t

    def test_count_demo_positions_without_orders(self):
        t=self.terminal(positions=[object(),object()])
        self.assertEqual(snapshot(t),2)
        t.order_send.assert_not_called()
        t.shutdown.assert_called_once()

    def test_reject_live_accounts_before_position_queries(self):
        t=self.terminal(mode=2)
        with self.assertRaises(RuntimeError):
            snapshot(t)
        t.order_send.assert_not_called()
        t.positions_get.assert_not_called()

    def test_stop_on_server_mismatch(self):
        t=self.terminal(server="OtherBroker-Live")
        with self.assertRaises(RuntimeError):
            snapshot(t)
        t.order_send.assert_not_called()
        t.positions_get.assert_not_called()

    def test_reports_only_when_number_of_positions_changes(self):
        output=[]
        values=iter([0,0,1,1])
        ticks=iter([0,0,1,1,2,2,3,3,4,4])
        watch(check=lambda:next(values),
              sleep=lambda _:None, clock=lambda:next(ticks),
              output=output.append,duration=4,interval=1)
        self.assertIn("Positions ouvertes détectées : 0",output)
        self.assertIn("Positions ouvertes détectées : 1",output)
        self.assertEqual(len([s for s in output if s.startswith("Positions ouvertes")]),2)


if __name__=="__main__":
    unittest.main()
