import tempfile
import unittest
import time
from pathlib import Path
from types import SimpleNamespace as NS
from direct_demo_manager import manage

RULES = {"enabled": False, "beThreshold": 1, "tpCount": 2,
         "tpPercents": [50, 50], "tpTargetsR": [1, 2]}
IDENTITY = {"login": "12345", "server": "Broker-Demo"}

class FakeMT5:
    ACCOUNT_TRADE_MODE_DEMO=0
    POSITION_TYPE_BUY=0
    POSITION_TYPE_SELL=1
    TRADE_ACTION_SLTP=6
    TRADE_ACTION_DEAL=1
    ORDER_TYPE_SELL=1
    ORDER_TYPE_BUY=0
    ORDER_FILLING_IOC=1
    TRADE_RETCODE_DONE=10009
    def __init__(self, mode=0):
        self.mode=mode
        self.orders=[]
        self.price=1.101
        self.positions=[NS(type=0,price_open=1.1,sl=1.099,volume=1.,tp=0.,ticket=10,symbol="EURUSD")]
    def account_info(self):
        return NS(login=12345,server="Broker-Demo",trade_mode=self.mode)
    def terminal_info(self):
        return NS(connected=True)
    def positions_get(self, ticket=None):
        return [p for p in self.positions if ticket is None or p.ticket==ticket]
    def symbol_info_tick(self,symbol):
        return NS(bid=self.price,ask=self.price,time=time.time())
    def symbol_info(self,symbol):
        return NS(volume_step=.01,volume_min=.01)
    def order_send(self, req):
        self.orders.append(req)
        p=self.positions[0]
        if req["action"]==self.TRADE_ACTION_SLTP:
            p.sl=req["sl"]
        else:
            p.volume=round(p.volume-req["volume"],8)
            if not p.volume:
                self.positions=[]
        return NS(retcode=self.TRADE_RETCODE_DONE)

class ManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.state=Path(self.temp.name)/"state.json"
    def tearDown(self):
        self.temp.cleanup()
    def run_cycle(self, mt5, **kwargs):
        return manage(mt5,IDENTITY,RULES,self.state,**kwargs)
    def test_demo_partial_tp_and_break_even_then_final(self):
        m=FakeMT5()
        # Floating point edge is avoided by moving slightly past thresholds.
        m.price=1.10101
        self.run_cycle(m,auto_be=True,auto_tp=True)
        self.assertEqual(m.positions[0].sl,1.1)
        self.assertEqual(m.positions[0].volume,.5)
        self.run_cycle(m,auto_be=True,auto_tp=True)
        self.assertEqual(len(m.orders),2)
        m.price=1.10201
        self.run_cycle(m,auto_be=True,auto_tp=True)
        self.assertEqual(len(m.orders),3)
        self.assertEqual(m.positions,[])
    def test_reject_live_before_actions(self):
        m=FakeMT5(mode=2)
        with self.assertRaises(RuntimeError):
            self.run_cycle(m,auto_be=True,auto_tp=True)
        self.assertEqual(m.orders,[])
    def test_disabled_actions_and_foreign_account(self):
        m=FakeMT5()
        self.run_cycle(m)
        self.assertEqual(m.orders,[])
        with self.assertRaises(RuntimeError):
            manage(m,{"login":"999","server":"Broker-Demo"},RULES,self.state,auto_tp=True)
        self.assertEqual(m.orders,[])
    def test_refused_close_is_not_resent(self):
        m=FakeMT5()
        m.price=1.1011
        def reject(req):
            m.orders.append(req)
            return NS(retcode=10027)
        m.order_send=reject
        self.run_cycle(m,auto_tp=True)
        self.run_cycle(m,auto_tp=True)
        self.assertEqual(len(m.orders),1)
        self.assertEqual(m.positions[0].volume,1.)
    def test_two_positions_have_independent_state(self):
        m=FakeMT5()
        m.price=1.1011
        m.positions.append(NS(type=0,price_open=1.1,sl=1.099,volume=1.,tp=0.,ticket=11,symbol="EURUSD"))
        def close(req):
            m.orders.append(req)
            position=next(p for p in m.positions if p.ticket==req["position"])
            position.volume=round(position.volume-req["volume"],8)
            return NS(retcode=m.TRADE_RETCODE_DONE)
        m.order_send=close
        self.run_cycle(m,auto_tp=True)
        self.assertEqual([p.volume for p in m.positions],[.5,.5])
        self.run_cycle(m,auto_tp=True)
        self.assertEqual(len(m.orders),2)
    def test_changed_tp_settings_after_partial_close_pause_future_closes(self):
        m=FakeMT5()
        m.price=1.1011
        self.run_cycle(m,auto_tp=True)
        altered={**RULES,"tpTargetsR":[1,1.5]}
        m.price=1.1021
        result=manage(m,IDENTITY,altered,self.state,auto_tp=True)
        self.assertEqual(len(m.orders),1)
        self.assertEqual(m.positions[0].volume,.5)
        self.assertIn("Réglages TP modifiés après clôture : vérification nécessaire",result)

if __name__=="__main__":
    unittest.main()
