import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from diagnose_fusion_demo import diagnose


class FusionDemoDiagnosticTests(unittest.TestCase):
    @staticmethod
    def terminal(*, server="FusionMarkets-Demo", trade_mode=0, positions=()):
        m = Mock()
        m.ACCOUNT_TRADE_MODE_DEMO = 0
        m.initialize.return_value = True
        m.account_info.return_value = SimpleNamespace(server=server, trade_mode=trade_mode)
        m.positions_get.return_value = positions
        return m

    def test_verified_demo_no_trades(self):
        t = self.terminal(positions=[object()])
        result = diagnose(t)
        self.assertEqual(result["status"], "demo_verified")
        self.assertEqual(result["positions_count"], 1)
        self.assertFalse(result["order_execution_enabled"])
        t.order_send.assert_not_called()
        t.shutdown.assert_called_once()

    def test_wrong_server_rejected(self):
        t = self.terminal(server="OtherBroker-Demo")
        self.assertEqual(diagnose(t)["status"], "wrong_server")
        t.order_send.assert_not_called()
        t.shutdown.assert_called_once()

    def test_real_account_rejected(self):
        t = self.terminal(trade_mode=2)
        self.assertEqual(diagnose(t)["status"], "not_demo")
        t.order_send.assert_not_called()
        t.shutdown.assert_called_once()

    def test_unconnected_terminal_returns_no_connection(self):
        t = self.terminal()
        t.initialize.return_value = False
        self.assertEqual(diagnose(t)["status"], "terminal_unavailable")
        t.order_send.assert_not_called()

    def test_missing_demo_constant_rejected(self):
        t = self.terminal()
        t.ACCOUNT_TRADE_MODE_DEMO = None
        self.assertEqual(diagnose(t)["status"], "demo_mode_unverifiable")
        t.order_send.assert_not_called()
        t.shutdown.assert_called_once()


if __name__ == "__main__":
    unittest.main()
