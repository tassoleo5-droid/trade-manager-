import json
import unittest
from unittest.mock import Mock

import report_demo_heartbeat as heartbeat

class HeartbeatTests(unittest.TestCase):
    def test_payload_is_minimal_and_demo_only(self):
        result = heartbeat.build_payload(lambda: {"status": "demo_verified", "positions_count": 2})
        self.assertEqual(result, {"demo": True, "positionsCount": 2})

    def test_non_demo_status_is_not_sent(self):
        with self.assertRaises(RuntimeError):
            heartbeat.build_payload(lambda: {"status": "not_demo"})

    def test_http_request_contains_no_mt5_details(self):
        response = Mock(status=202)
        response.__enter__ = lambda _: response
        response.__exit__ = lambda *_: None
        opener = Mock(return_value=response)
        env = {"MYFLOWFX_STAGING_URL": "https://staging.example", "MYFLOWFX_WORKER_TOKEN": "x" * 32}
        self.assertEqual(heartbeat.report(opener, env, lambda: {"status": "demo_verified", "positions_count": 0}), "accepted")
        request = opener.call_args.args[0]
        self.assertEqual(json.loads(request.data), {"demo": True, "positionsCount": 0})

if __name__ == "__main__":
    unittest.main()
