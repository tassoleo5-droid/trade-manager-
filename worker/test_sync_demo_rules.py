import unittest
from types import SimpleNamespace
from sync_demo_rules import fetch_rules


class Terminal:
    ACCOUNT_TRADE_MODE_DEMO = 0
    def __init__(self, mode=0, connected=True):
        self.mode, self.connected, self.stopped = mode, connected, False
    def initialize(self, **kwargs):
        return True
    def account_info(self):
        return SimpleNamespace(login=12345, server="FusionMarkets-Demo", trade_mode=self.mode)
    def terminal_info(self):
        return SimpleNamespace(connected=self.connected)
    def shutdown(self):
        self.stopped = True


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.rules = {"enabled": False, "beThreshold": 1, "tpCount": 2,
                      "tpPercents": [50, 50], "tpTargetsR": [1, 2]}
    def request(self, *args):
        return {"login": "12345", "server": "FusionMarkets-Demo",
                "executionEnabled": False, "rules": self.rules}
    def run_fetch(self, terminal, request=None):
        return fetch_rules(terminal, r"C:\MT5\terminal64.exe", request or self.request,
                           "https://example.test", "secret", "worker")
    def test_demo_reads_settings(self):
        terminal = Terminal()
        self.assertEqual(self.run_fetch(terminal), self.rules)
        self.assertTrue(terminal.stopped)
    def test_reject_live_and_disconnected(self):
        for terminal in (Terminal(mode=2), Terminal(connected=False)):
            with self.assertRaises(RuntimeError):
                self.run_fetch(terminal)
            self.assertTrue(terminal.stopped)
    def test_reject_wrong_identity_and_invalid_rules(self):
        def wrong(*args):
            return {"login": "999", "server": "FusionMarkets-Demo",
                    "executionEnabled": False, "rules": self.rules}
        with self.assertRaises(RuntimeError):
            self.run_fetch(Terminal(), wrong)
        self.rules["tpPercents"] = [50, 60]
        with self.assertRaises(RuntimeError):
            self.run_fetch(Terminal())

if __name__ == "__main__":
    unittest.main()
