import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from direct_demo_cycle import run_cycle
from test_direct_demo_manager import FakeMT5, RULES

class Terminal(FakeMT5):
    def initialize(self, **kwargs):
        return True
    def shutdown(self):
        return None

class CycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.state=Path(self.tmp.name)/"state.json"
    def tearDown(self):
        self.tmp.cleanup()
    def call(self, terminal, post):
        return run_cycle(terminal,r"C:\MT5\terminal64.exe",post,"https://example.test","token","worker",self.state)
    def response(self, origin, path, token, worker, identity):
        return {"login":identity["login"],"server":identity["server"],"rules":RULES,"executionEnabled":False}
    @patch.dict(os.environ,{},clear=True)
    def test_disabled_never_queries_terminal_or_api(self):
        def forbidden(*args):
            raise AssertionError("API must not be called")
        m=Terminal()
        self.assertEqual(self.call(m,forbidden),["Gestion automatique démo désactivée"])
        self.assertEqual(m.orders,[])
    @patch.dict(os.environ,{"MYFLOWFX_DEMO_AUTO_EXIT":"1","MYFLOWFX_DEMO_MANAGE_ACCOUNT":"12345"},clear=True)
    def test_verified_demo_uses_account_rules(self):
        m=Terminal()
        m.price=1.1011
        self.call(m,self.response)
        self.assertEqual(m.positions[0].volume,.5)
    @patch.dict(os.environ,{"MYFLOWFX_DEMO_AUTO_EXIT":"1","MYFLOWFX_DEMO_MANAGE_ACCOUNT":"999"},clear=True)
    def test_wrong_account_fails_before_api_or_order(self):
        m=Terminal()
        with self.assertRaises(RuntimeError):
            self.call(m,self.response)
        self.assertEqual(m.orders,[])
    @patch.dict(os.environ,{"MYFLOWFX_DEMO_AUTO_EXIT":"1","MYFLOWFX_DEMO_MANAGE_ACCOUNT":"12345"},clear=True)
    def test_no_server_rules_never_sends_order(self):
        m=Terminal()
        def unavailable(*args):
            raise RuntimeError("unavailable")
        with self.assertRaises(RuntimeError):
            self.call(m,unavailable)
        self.assertEqual(m.orders,[])

if __name__=="__main__":
    unittest.main()
