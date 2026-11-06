#!/usr/bin/env python3
"""No QEMU: state, gate, source-order and browser fixture checks."""
from pathlib import Path
import hashlib
import json
import sys
import unittest

HERE = Path(__file__).resolve().parent
USABILITY = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(1, str(USABILITY))
from pending_visual_v20 import classify, late_change
from trial_web_v20_passive_timing import TrialState, PAGE
from gate_input_usability import valid_command

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

class OfflineFixtures(unittest.TestCase):
    def setUp(self):
        self.before = {'sequence': 17, 'PNG_sha256': 'old'}
        self.same = {'sequence': 18, 'PNG_sha256': 'old'}
        self.changed = {'sequence': 18, 'PNG_sha256': 'new'}
        self.cmd = {'sent_monotonic': 100, 'key': 0x30,
                    'before_command_sequence': 17, 'before_command_png_sha256': 'old'}

    def test_missing_ack_fails_only_after_native_deadline(self):
        self.assertEqual(classify(self.cmd, 1, {}, False, self.before, 111.9).state, 'input_pending')
        self.assertEqual(classify(self.cmd, 1, {}, False, self.before, 112.1).state, 'unknown_ack')
        self.assertEqual(classify(self.cmd, 1, {1: (101, 0x30)}, False, self.before, 112.1).state, 'unknown_ack')

    def test_native_received_does_not_prove_visual_completion(self):
        d = classify(self.cmd, 1, {1: (101, 0x30)}, True, self.before, 104)
        self.assertEqual((d.state, d.input_received, d.visual_change_observed), ('visual_pending', True, False))

    def test_valid_changed_frame_requires_new_sequence_and_pixels(self):
        self.assertEqual(classify(self.cmd, 1, {1: (101, 0x30)}, True, self.changed, 103).state, 'visual_changed')
        self.assertEqual(classify(self.cmd, 1, {1: (101, 0x30)}, True, {'sequence': 17, 'PNG_sha256': 'new'}, 103).state, 'visual_pending')
        self.assertEqual(classify(self.cmd, 1, {1: (101, 0x30)}, True, self.same, 103).state, 'visual_pending')

    def test_bounded_no_change_and_menu_window(self):
        self.assertEqual(classify(self.cmd, 1, {1: (101, 0x30)}, True, self.same, 107).state, 'no_change_observed')
        menu = dict(self.cmd, key=0x1ab)
        self.assertEqual(classify(menu, 1, {1: (101, 0x1ab)}, True, self.same, 130).state, 'visual_pending')
        self.assertEqual(classify(menu, 1, {1: (101, 0x1ab)}, True, self.same, 131).state, 'no_change_observed')

    def test_late_frame_distinct_and_no_auto_key(self):
        self.assertTrue(late_change(self.same, {'sequence': 19, 'PNG_sha256': 'new'}))
        self.assertFalse(late_change(self.same, {'sequence': 19, 'PNG_sha256': 'old'}))
        source = (HERE / 'run_trial_v20_passive_timing.py').read_text()
        self.assertNotIn('keepalive', source.lower())
        self.assertNotIn('auto_retry', source.lower())
        self.assertIn('unknown_due_to_prior_no_change', source)
        self.assertIn('menu_visual_pending_after_bounded_no_change', source)
        self.assertIn("'status': 'stale_no_guest_write'", source)

    def test_native_shutdown_preempts_input(self):
        d = classify(self.cmd, 1, {1: (101, 0x30)}, True, self.changed, 103, native_shutdown=True)
        self.assertEqual((d.state, d.terminal, d.visual_change_observed), ('native_shutdown', True, False))

    def test_web_one_pending_and_visual_identity(self):
        state = TrialState(HERE, 3600, 4096)
        state.publish(b'PNG', {'sequence': 18, 'PNG_sha256': 'new', 'all_zero_pixels': False})
        state.update(ready=True, phase='ready')
        code, _ = state.submit({'key': 0x30, 'observed_sequence': 18})
        self.assertEqual(code, 202)
        self.assertEqual(state.submit({'key': 0x30, 'observed_sequence': 18})[0], 409)
        self.assertEqual(state.snapshot()['visual_state'], 'idle')
        state.take(); state.update(busy=False)
        state.publish(b'PNG2', {'sequence': 19, 'PNG_sha256': 'new2', 'all_zero_pixels': False})
        self.assertEqual(state.submit({'key': 0x30, 'observed_sequence': 18})[0], 409)

    def test_browser_image_and_status_requests_bounded(self):
        self.assertIn("fetch('/frame.png',{cache:'no-store',signal:controller.signal})", PAGE)
        self.assertIn("fetch('/api/status',{cache:'no-store',signal:controller.signal})", PAGE)
        self.assertIn('image.onerror=', PAGE)
        self.assertIn("setTimeout(()=>controller.abort(),8000)", PAGE)

    def test_gate_31_32_and_configured_max(self):
        self.assertTrue(valid_command(31, 0x30, 100, 30, 0, 4096))
        self.assertTrue(valid_command(32, 0x30, 100, 31, 0, 4096))
        self.assertTrue(valid_command(4096, 0x30, 100, 4095, 0, 4096))
        self.assertFalse(valid_command(4097, 0x30, 100, 4096, 0, 4096))

    def test_rm_source_receive_order_and_guards(self):
        src = USABILITY / 'mss-all-key-contrast/passive-timing-next/src/fx3-rm-empty-provider-v8-long-use-timing.c'
        self.assertEqual(sha(src), '7467449b4230f2636d10550a4727791689b897061db6f53216d7dcac62a98bc6')
        text = src.read_text()
        fn = text[text.index('int osal_rcv_msg_tmo('):]
        order = ['int saved=*__errno_location()', 'U wait_enter_ns=dst==0x807a0020U?now():0',
                 'W wait_enter_step=', '*__errno_location()=saved;int rc=fn(dst,p,tmo),after=*__errno_location()',
                 'U wait_return_ns=dst==0x807a0020U?now():0',
                 '*__errno_location()=after;if(!rc', 'FX3_KEY_INPUT_RECV',
                 '*__errno_location()=after;return rc;']
        offsets = [fn.index(part) for part in order]
        self.assertEqual(offsets, sorted(offsets))
        self.assertNotIn('if(key_step)wait_enter_ns', fn)
        self.assertIn('wait_enter_step=%u wait_return_step=%u', fn)
        self.assertIn('downstream_processing_unproven=1', fn)

    def test_candidate_only_three_members_and_seed(self):
        receipt = json.loads((HERE / 'vmopt-20261103-try2-passive-timing-v4/build-receipt.json').read_text())
        self.assertEqual(len(receipt['changed_members']), 3)
        self.assertTrue(receipt['other_member_payloads_and_modes_unchanged'])
        self.assertTrue(receipt['dtb_only_initrd_end_changed'])
        self.assertFalse(receipt['guest_validated'])
        audit = json.loads((HERE / 'vmopt-20261103-try2-passive-timing-v4/cpio-audit.json').read_text())
        self.assertTrue(audit['safe_to_unpack'])

if __name__ == '__main__':
    unittest.main(verbosity=2)
