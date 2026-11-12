import os
import unittest
from unittest.mock import patch
from run_direct_demo_management import validate_config

class ConfigTests(unittest.TestCase):
    @patch.dict(os.environ,{"MYFLOWFX_DEMO_AUTO_EXIT":"1"},clear=True)
    def test_distinct_terminal_and_demo_login_are_required(self):
        base=("https://example.test","x"*40,"demo-worker",r"C:\one\terminal64.exe")
        validate_config(*base,r"C:\two\terminal64.exe","12345")
        with self.assertRaises(ValueError):
            validate_config(*base,r"c:\ONE\terminal64.exe","12345")
        with self.assertRaises(ValueError):
            validate_config(*base,r"C:\two\terminal64.exe","")
    @patch.dict(os.environ,{},clear=True)
    def test_requires_local_opt_in(self):
        with self.assertRaises(ValueError):
            validate_config("https://example.test","x"*40,"demo-worker",
                r"C:\one\terminal64.exe",r"C:\two\terminal64.exe","12345")

if __name__=="__main__":
    unittest.main()
