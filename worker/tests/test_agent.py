import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from agent import validate_agent_config, verify_job


class AgentTests(unittest.TestCase):
    def test_only_https_origin_accepted(self):
        validate_agent_config("https://myflowfx.example", "x" * 40, "worker-1")
        for address in ("http://myflowfx.example", "https://attacker@myflowfx.example",
                        "https://myflowfx.example/something", "https://myflowfx.example?x=y"):
            with self.assertRaises(ValueError):
                validate_agent_config(address, "x" * 40, "worker-1")

    def terminal(self, trade_mode):
        terminal = Mock()
        terminal.ACCOUNT_TRADE_MODE_DEMO = 0
        terminal.initialize.return_value = True
        terminal.account_info.return_value = SimpleNamespace(
            login=1111, server="Demo", currency="USD", trade_mode=trade_mode)
        terminal.positions_get.return_value = []
        return terminal

    def test_demo_verifies_without_sending_orders(self):
        t = self.terminal(0)
        result = verify_job({"jobId": "abc", "login": "1111", "server": "Demo", "password": "demo"}, t)
        self.assertEqual(result["result"], "verified_demo")
        t.order_send.assert_not_called()

    def test_live_is_rejected_without_sending_orders(self):
        t = self.terminal(2)
        result = verify_job({"jobId": "abc", "login": "1111", "server": "Demo", "password": "live"}, t)
        self.assertEqual(result["result"], "rejected_live")
        t.order_send.assert_not_called()


if __name__ == "__main__":
    unittest.main()
