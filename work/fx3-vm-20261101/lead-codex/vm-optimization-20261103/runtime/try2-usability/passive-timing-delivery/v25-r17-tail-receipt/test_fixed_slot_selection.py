"""Exercise the actual runner prefix through candidate hash validation; no VM."""
import argparse
import ast
import plistlib
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import run_trial_v25_diag_r3 as runner


class SelectionTests(unittest.TestCase):
    def select(self, args, wrong_digest=False):
        tree = ast.parse(Path(runner.__file__).read_text())
        main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
        body = []
        for node in main.body:
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'candidate' for t in node.targets):
                break
            body.append(node)
        body.append(ast.Return(ast.Tuple(elts=[ast.Name(id=n, ctx=ast.Load()) for n in
                                               ('ns', 'selected_root', 'pinned_manifest_sha')], ctx=ast.Load())))
        main.body = body
        module = ast.fix_missing_locations(ast.Module(body=[main], type_ignores=[]))
        env = vars(runner).copy()
        if wrong_digest:
            env['digest'] = lambda path: '0' * 64
        exec(compile(module, '<actual-runner-selection>', 'exec'), env)
        # Only the mount lookup is stubbed. Candidate paths and hashes are real.
        volume = plistlib.dumps({'VolumeUUID': runner.VOLUME_UUID})
        with patch.object(sys, 'argv', ['runner'] + args), patch.object(runner.subprocess, 'check_output', return_value=volume):
            return env['main']()

    def test_explicit_variants_use_distinct_real_frozen_manifests(self):
        seen = []
        for interval in (1, 64):
            ns, selected, pin = self.select(['--snapshot-tail', '--gate-publish-interval', str(interval)])
            self.assertEqual(selected, runner.HERE.parent / 'r16-fixed-slot-guests' / f'guest-N{interval}')
            self.assertEqual(ns.candidate, selected / 'candidate.json')
            self.assertEqual(runner.digest(ns.candidate), pin)
            self.assertEqual(ns.label, f'v25gate-n{interval}-r17')
            self.assertEqual((ns.smp, ns.tcg_thread, ns.icount_shift), (4, 'multi', None))
            seen.append(pin)
        self.assertNotEqual(*seen)

    def test_default_remains_original_r3(self):
        ns, selected, pin = self.select([])
        self.assertIsNone(ns.gate_publish_interval)
        self.assertFalse(ns.snapshot_tail)
        self.assertEqual(selected.name, 'vmopt-20261104-v25-menu-osd-diagnostic-r3')
        self.assertEqual(pin, 'a8fd7e81e00353f8dbd5dc579f6d440f28ecd083fc15d8e1335899c44b108518')

    def test_missing_tail_and_conflicting_candidate_rejected(self):
        for args in (['--gate-publish-interval', '1'],
                     ['--gate-publish-interval', '64', '--snapshot-tail', '--review-procdiag-r4e']):
            with self.subTest(args=args), self.assertRaises(SystemExit) as caught:
                self.select(args)
            self.assertEqual(caught.exception.code, 2)

    def test_unreviewed_interval_rejected(self):
        with self.assertRaises(SystemExit) as caught:
            self.select(['--snapshot-tail', '--gate-publish-interval', '2'])
        self.assertEqual(caught.exception.code, 2)

    def test_manifest_tamper_rejected_before_input_loading(self):
        with self.assertRaisesRegex(RuntimeError, 'manifest identity changed'):
            self.select(['--snapshot-tail', '--gate-publish-interval', '64'], wrong_digest=True)


if __name__ == '__main__':
    unittest.main()
