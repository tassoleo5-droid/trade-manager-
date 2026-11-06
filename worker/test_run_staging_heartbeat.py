import unittest

import run_staging_heartbeat as monitor

class MonitorTests(unittest.TestCase):
    def test_one_cycle_then_stop(self):
        sent = []
        lines = []
        def stop(_seconds):
            raise KeyboardInterrupt
        monitor.run(send=lambda: sent.append(True), sleep=stop, output=lines.append, interval=60)
        self.assertEqual(sent, [True])
        self.assertIn("Surveillance arrêtée. Aucun ordre envoyé.", lines)

    def test_rejects_short_interval(self):
        with self.assertRaises(ValueError):
            monitor.run(interval=1)

if __name__ == "__main__":
    unittest.main()
