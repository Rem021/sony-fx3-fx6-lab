import copy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('runner_v2', Path(__file__).with_name('run_observer_once.py'))
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class ArgvChecks(unittest.TestCase):
    def setUp(self):
        self.argv = ['qemu', '-machine', 'virt', '-serial', 'file:old.log', '-chardev',
            'socket,path=g,server=on,wait=off,id=keygate93', '-gdb', 'chardev:keygate93',
            '-S', '-kernel', '/frozen/kernel', '-s']

    def test_only_terminal_duplicate_s_and_serial_change(self):
        saved = {'candidate_argv_before_observer_serial_retarget': self.argv}
        before = copy.deepcopy(saved)
        actual = runner.runtime_argv(saved, Path('/new/run'))
        expected = self.argv[:-1]
        expected[expected.index('-serial')+1] = 'file:/new/run/serial.log'
        self.assertEqual(actual, expected)
        self.assertEqual(saved, before)
        self.assertEqual(actual[actual.index('-gdb')+1], 'chardev:keygate93')
        self.assertNotIn('-s', actual)

    def test_new_candidate_can_already_omit_duplicate(self):
        self.assertEqual(runner.normalize_gdb_argv(self.argv[:-1]), self.argv[:-1])

    def test_reject_unexpected_gdb_or_nonterminal_s(self):
        for argv in [self.argv[:-1]+['-s','-S'], self.argv+['-s'],
                     ['qemu','-gdb','tcp::1234'], ['qemu','-s']]:
            with self.subTest(argv=argv):
                with self.assertRaises(RuntimeError):
                    runner.normalize_gdb_argv(argv)


if __name__ == '__main__':
    unittest.main()
