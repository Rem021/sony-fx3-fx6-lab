"""TRY1 safety-boundary tests. Native boot/MENU/cleanup acceptance is separate."""
import http.client
import json
from pathlib import Path
import struct
import tempfile
import unittest
from trial_web_v2 import TrialState, start_server, KEYS
from trial_log_v2 import FullLogMonitor
from trial_ring_v1 import validate_slot
from osd_ring93_v4 import HEADER, STRIDE

ROOT = Path(__file__).resolve().parent


class TrialTests(unittest.TestCase):
    def setUp(self):
        self.state = TrialState(ROOT, 60)
        self.state.publish(b'PNG test fixture', {'sequence': 10, 'PNG_sha256': 'fixture'})
        self.state.update(phase='ready', ready=True)
        self.server, self.thread = start_server(self.state, 0)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def request(self, path, body=None, token=True, origin=None, host=None):
        connection = http.client.HTTPConnection(*self.server.server_address, timeout=3)
        headers = {}
        if body is not None:
            headers['Content-Type'] = 'application/json'
            if token:
                headers['X-Trial-Token'] = self.state.token
        if origin:
            headers['Origin'] = origin
        if host:
            headers['Host'] = host
        connection.request('POST' if body is not None else 'GET', path,
                           json.dumps(body) if body is not None else None, headers)
        response = connection.getresponse()
        result = (response.status, response.read(), dict(response.getheaders()))
        connection.close()
        return result

    def test_whitelist_and_single_inflight(self):
        for key in KEYS:
            with self.subTest(key=key):
                self.assertEqual(self.request('/api/key', {'key': key, 'observed_sequence': 10})[0], 202)
                self.assertEqual(self.request('/api/key', {'key': key, 'observed_sequence': 10})[0], 409)
                self.assertEqual(self.state.take()['key'], key)
                self.state.update(busy=False)
        for invalid in [0, 2, 0xffff, '0x1ab', True, None]:
            self.assertEqual(self.request('/api/key', {'key': invalid, 'observed_sequence': 10})[0], 400)
        self.assertIsNone(self.state.take())

    def test_observed_frame_stop_and_limit(self):
        self.assertEqual(self.request('/api/key', {'key': 3, 'observed_sequence': 999})[0], 409)
        self.state.update(steps=30)
        self.assertEqual(self.request('/api/key', {'key': 3, 'observed_sequence': 10})[0], 409)
        self.state.update(steps=0)
        self.assertEqual(self.request('/api/stop', {})[0], 202)
        self.assertTrue(self.state.stop.is_set())
        self.assertEqual(self.request('/api/key', {'key': 3, 'observed_sequence': 10})[0], 409)

    def test_http_loopback_origin_and_routes(self):
        self.assertEqual(self.server.server_address[0], '127.0.0.1')
        for kwargs in [{'token': False}, {'origin': 'https://example.com'}, {'host': 'example.com'}]:
            self.assertEqual(self.request('/api/key', {'key': 3, 'observed_sequence': 10}, **kwargs)[0], 403)
        self.assertEqual(self.request('/../STATE.json')[0], 404)
        self.assertEqual(self.request('/api/anything', {})[0], 404)
        code, data, headers = self.request('/frame.png')
        self.assertEqual((code, data, headers['X-Frame-Sequence']), (200, b'PNG test fixture', '10'))

    def test_assert_boundary_and_inhibit(self):
        with tempfile.TemporaryDirectory(prefix='try1-log-check-', dir=ROOT) as folder:
            path = Path(folder)/'serial.log'
            path.write_bytes(b'normal startup\nAsser')
            monitor = FullLogMonitor(path)
            monitor.poll()
            self.assertIsNone(monitor.failure)
            with path.open('ab') as f:
                f.write(b'tion failed in native app\n')
            monitor.poll()
            self.assertIn('Assertion', monitor.failure)
            self.assertEqual(monitor.offset, path.stat().st_size)
            self.state.fail(monitor.failure)
            self.assertFalse(self.state.snapshot()['ready'])
            self.assertEqual(self.request('/api/key', {'key': 3, 'observed_sequence': 10})[0], 409)

    def test_actual_prior_ring_and_corruption(self):
        source = ROOT/'runs/ap101r4tile600-be9996d0/osd-ring-live.bin'
        ring = source.read_bytes()
        g = list(struct.unpack_from('<16Q', ring))
        slot = ring[HEADER+((g[4]-1) % 8)*STRIDE:HEADER+((g[4]-1) % 8+1)*STRIDE]
        value, reason = validate_slot(g, slot)
        self.assertIsNone(reason)
        self.assertEqual(value[0][0], g[4])
        broken = bytearray(slot)
        broken[0x200] ^= 1
        self.assertEqual(validate_slot(g, broken)[1], 'concurrent overwrite checksum mismatch')
        for word, replacement in [(2, 0), (26, 0), (35, 0), (22, 0), (11, 1)]:
            with self.subTest(word=word):
                broken = bytearray(slot)
                struct.pack_into('<Q', broken, word*8, replacement)
                self.assertIsNotNone(validate_slot(g, broken)[1])


if __name__ == '__main__':
    unittest.main(verbosity=2)
