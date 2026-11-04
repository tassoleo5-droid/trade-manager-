import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from mt5_adapter import AccountConfig, inspect_connection


class TestAccountConfig(unittest.TestCase):
    def test_environment_input(self):
        with patch.dict("os.environ", {"MT5_LOGIN": "123456", "MT5_SERVER": "Demo-01", "MT5_PASSWORD": "secret"}):
            config = AccountConfig.from_environment()
            self.assertEqual(config.login, 123456)

    def test_invalid_login(self):
        with patch.dict("os.environ", {"MT5_LOGIN": "abc", "MT5_SERVER": "Demo-01", "MT5_PASSWORD": "secret"}):
            with self.assertRaises(ValueError):
                AccountConfig.from_environment()

    def test_diagnostic_is_read_only_and_closes_terminal(self):
        mt5 = Mock()
        mt5.initialize.return_value = True
        mt5.account_info.return_value = SimpleNamespace(login=123456, server="Demo-01", currency="USD")
        mt5.positions_get.return_value = [object()]
        result = inspect_connection(AccountConfig(123456, "Demo-01", "secret"), mt5)
        self.assertEqual(result["positions_count"], 1)
        self.assertFalse(result["trading_actions_enabled"])
        mt5.shutdown.assert_called_once()
        mt5.order_send.assert_not_called()
        mt5.initialize.assert_called_once_with(login=123456, password="secret", server="Demo-01", timeout=30000)

    def test_wrong_account_rejected(self):
        mt5 = Mock()
        mt5.initialize.return_value = True
        mt5.account_info.return_value = SimpleNamespace(login=999, server="Demo-01", currency="USD")
        with self.assertRaises(RuntimeError):
            inspect_connection(AccountConfig(123456, "Demo-01", "secret"), mt5)
        mt5.shutdown.assert_called_once()


if __name__ == "__main__":
    unittest.main()
