"""Actual O_RDONLY file capture and injected faults; no camera/USB tests."""
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
import json
import os
import selectors
import subprocess
import sys
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
from fx3_recovery import capture as C
from fx3_recovery import engine as E
from fx3_recovery.files import ROOT, allocate_test_run_dir, check_volume, new_directory, read_file, encode

RUN = allocate_test_run_dir('work/sony-firmware-20261024/stage186-fx3-bounded-capture-engine/runs', 'capture-tests', __name__, sys.argv)


class FaultSource(C.RegularFileSource):
    def __init__(self, path, expected, fault=None, at=1):
        super().__init__(path, expected)
        self.fault = fault; self.at = at; self.calls = []; self.closes = 0; self.identifications = 0

    def identify(self):
        item = super().identify()
        if hasattr(self, 'calls'):
            self.identifications += 1
            if self.fault == 'identity' and self.calls:
                item = {**item, 'descriptor_identity_sha256': '9'*64}
        return item

    def read_at(self, request, deadline):
        self.calls.append(request.index)
        row = super().read_at(request, deadline)
        if request.index != self.at:
            return row
        if self.fault == 'short': return replace(row, actual=C.BLOCK-1, data=row.data[:-1])
        if self.fault == 'oversized': return replace(row, actual=C.BLOCK+1, data=row.data+b'x')
        if self.fault == 'wrong-offset':
            return replace(row, request=replace(request, index=2, offset=C.BLOCK*2))
        if self.fault == 'wrong-capture': return replace(row, request=replace(request, capture_id='8'*32))
        if self.fault == 'wrong-nonce': return replace(row, request=replace(request, nonce='8'*32))
        if self.fault == 'failed-status': return replace(row, status=-5)
        if self.fault == 'bool-status': return replace(row, status=False)
        if self.fault == 'corrupt': return replace(row, data=bytes([row.data[0]^1])+row.data[1:])
        if self.fault == 'exception': raise TimeoutError('completion is not known')
        if self.fault == 'interrupt': raise KeyboardInterrupt()
        return row

    def close(self):
        self.closes += 1
        if self.fault == 'close': raise OSError('close status unknown')
        return super().close()


class CaptureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        check_volume(); RUN.mkdir(mode=0o700)
        reference = ROOT/'work/fx3-color-port-20261027/input-20261028/original-update-engine/2.05/nflasha1'
        cls.original_path = reference
        cls.original = read_file(reference, C.MAX_P1)
        cls.original_sha = C.digest(cls.original)
        # Explicit synthetic full-length fixture. This is NOT current7.02 data.
        cls.full = cls.original+b'\xff'*(C.MAX_P1-len(cls.original))
        cls.expected = C.digest(cls.full)
        new_directory(RUN/'synthetic-fixture', {'synthetic.p1': cls.full})
        cls.input = RUN/'synthetic-fixture/synthetic.p1'
        cls.complete = RUN/'complete'
        C.capture_local(cls.input, cls.complete, cls.expected, '1'*64)

    def fault(self, name, fault, at=1, **kwargs):
        objects = []
        def factory():
            obj = FaultSource(self.input, self.expected, fault, at); objects.append(obj); return obj
        out = RUN/name
        with self.assertRaises(C.CaptureFailure):
            C._capture(factory, out, self.expected, '1'*64, **kwargs)
        failure = json.loads((out/'failure.json').read_text())
        self.assertFalse((out/'complete.json').exists()); self.assertFalse((out/'source.p1').exists())
        self.assertFalse(failure['automatic_retry'])
        if objects:
            obj = objects[0]
            self.assertEqual(len(obj.calls), len(set(obj.calls)), 'no second read at a failed offset')
            if failure['pending_provider_retained']:
                self.assertIs(C.UNKNOWN_SOURCES.pop(failure['capture_id']), obj)
                # Fixture-only disposal after the test knows no real operation
                # is pending. The product exposes no UNKNOWN cleanup/retry API.
                os.close(obj.fd)
        return failure, objects, out

    def test_full_capture_readback_and_adapter_inverse(self):
        receipt = C.verify_capture(self.complete, self.expected)
        self.assertEqual(receipt['chunks'], 383); self.assertEqual(receipt['windows'], 3)
        self.assertFalse(receipt['camera_identity_verified']); self.assertFalse(receipt['independent_recovery_proven'])
        self.assertEqual(read_file(self.complete/'source.p1', C.MAX_P1), self.full)
        inspection = E.inspect_image(self.full)
        self.assertTrue(inspection['component_profile_match']); self.assertIsNone(inspection['recognized_reference'])
        E.create_bundle(self.complete/'source.p1', RUN/'capture-bundle', 'unverified-snapshot', '1'*64)
        E.rollback(RUN/'capture-bundle', RUN/'capture-bundle/candidate.p1', RUN/'capture-restored')
        self.assertEqual(read_file(RUN/'capture-restored/restored.p1', C.MAX_P1), self.full)
        journal = [json.loads(line) for line in (self.complete/'journal.jsonl').read_text().splitlines()]
        self.assertEqual(sum(row['event']=='read-in-flight' for row in journal), 383)
        self.assertEqual(sum(row['event']=='local-source-closed' for row in journal), 1)

    def test_reply_faults_stop_without_retry_and_preserve_prior_chunk(self):
        for fault in ('short','oversized','wrong-offset','wrong-capture','wrong-nonce','failed-status','bool-status'):
            with self.subTest(fault=fault):
                result, objects, out = self.fault('fault-'+fault, fault)
                self.assertEqual(result['state'], 'INCOMPLETE'); self.assertEqual(objects[0].closes, 1)
                self.assertEqual(objects[0].calls, [0,1])
                self.assertEqual(read_file(out/'chunk-000.bin', C.BLOCK), self.full[:C.BLOCK])
                self.assertFalse((out/'chunk-001.bin').exists())

    def test_source_identity_drift_denies_next_read(self):
        result, objects, out = self.fault('identity-drift', 'identity')
        self.assertEqual(objects[0].calls, [0]); self.assertEqual(objects[0].closes, 1)
        self.assertFalse((out/'chunk-000.bin').exists())

    def test_wrong_bytes_fail_external_hash_before_image_publish(self):
        result, objects, out = self.fault('corrupt-content', 'corrupt')
        self.assertEqual(len(objects[0].calls), 383)
        self.assertEqual(objects[0].closes, 1); self.assertTrue((out/'source-closed.json').is_file())
        self.assertEqual(result['state'], 'INCOMPLETE')

    def test_uncertain_read_or_interrupt_retains_provider_without_close(self):
        for fault in ('exception','interrupt'):
            result, objects, out = self.fault('pending-'+fault, fault)
            self.assertEqual(result['state'], 'UNKNOWN_IN_FLIGHT')
            self.assertEqual(objects[0].closes, 0); self.assertEqual(objects[0].calls, [0,1])

    def test_close_error_denies_backup_and_never_retries_close(self):
        result, objects, out = self.fault('close-failed', 'close')
        self.assertEqual(result['state'], 'UNKNOWN_CLOSE'); self.assertEqual(objects[0].closes, 1)
        self.assertFalse((out/'source-closed.json').exists())

    def test_late_return_is_dropped_without_second_call(self):
        class TimeSource(FaultSource):
            def read_at(inner, request, deadline):
                row = super().read_at(request, deadline); counter[0] = 6.0; return row
        counter = [0.0]; objects = []
        def factory():
            source = TimeSource(self.input, self.expected); objects.append(source); return source
        out = RUN/'late-return'
        with self.assertRaises(C.CaptureFailure):
            C._capture(factory, out, self.expected, '1'*64, clock=lambda:counter[0])
        self.assertEqual(objects[0].calls, [0]); self.assertEqual(objects[0].closes, 1)
        self.assertFalse((out/'chunk-000.bin').exists()); self.assertFalse((out/'complete.json').exists())

    def test_existing_source_paths_links_and_device_nodes_denied(self):
        with self.assertRaises(C.CaptureFailure): C.capture_local(self.original_path, RUN/'short-input', self.original_sha, '1'*64)
        with self.assertRaises(C.CaptureFailure): C.capture_local(self.input, RUN/'bad-source-pin', '2'*64, '1'*64)
        symlink = RUN/'input-symlink'; symlink.symlink_to(self.input)
        with self.assertRaises(C.CaptureFailure): C.capture_local(symlink, RUN/'symlink-output', self.expected, '1'*64)
        with self.assertRaises(FileExistsError): C.capture_local(self.input, self.complete, self.expected, '1'*64)
        with self.assertRaises(FileExistsError): C.capture_local(self.input, self.input, self.expected, '1'*64)
        with self.assertRaises(ValueError): C.RegularFileSource('/dev/null', self.expected)
        new_directory(RUN/'hardlink-fixture', {'input.p1': self.full})
        hard_source = RUN/'hardlink-fixture/input.p1'
        os.link(hard_source, RUN/'input-hardlink')
        with self.assertRaises(C.CaptureFailure): C.capture_local(hard_source, RUN/'hardlinked-input', self.expected, '1'*64)

    def test_actual_descriptor_source_detects_change_and_symlink_parent(self):
        new_directory(RUN/'mutable', {'input.p1': self.full})
        source = C.RegularFileSource(RUN/'mutable/input.p1', self.expected)
        try:
            with (RUN/'mutable/input.p1').open('r+b') as f:
                f.seek(C.BLOCK); f.write(b'\x01'); f.flush(); os.fsync(f.fileno())
            with self.assertRaises(ValueError): source.identify()
        finally: source.close()
        (RUN/'linked-parent').symlink_to(RUN/'mutable', target_is_directory=True)
        with self.assertRaises(ValueError): C.RegularFileSource(RUN/'linked-parent/input.p1', self.expected)

    def test_incomplete_and_manipulated_capture_rejected(self):
        with self.assertRaises(ValueError): C.verify_capture(self.complete, '3'*64)
        # Modify one small receipt at a time, restoring its exact bytes afterwards.
        p = self.complete/'complete.json'; original = p.read_bytes()
        try:
            value = json.loads(original); value['hardware_validated'] = True; p.write_bytes(encode(value))
            with self.assertRaises(ValueError): C.verify_capture(self.complete, self.expected)
            p.write_bytes(original[:-2]+b',"status":"COMPLETE_LOCAL_FILE_ONLY"}\n')
            with self.assertRaises(ValueError): C.verify_capture(self.complete, self.expected)
        finally: p.write_bytes(original)
        chunk = self.complete/'chunk-382.bin'; original = chunk.read_bytes()
        try:
            chunk.write_bytes(original[:-1]+bytes([original[-1]^1]))
            with self.assertRaises(ValueError): C.verify_capture(self.complete, self.expected)
        finally: chunk.write_bytes(original)
        window = self.complete/'window-2.json'; original = window.read_bytes()
        try:
            row = json.loads(original); row['previous_manifest_sha256'] = '4'*64; window.write_bytes(encode(row))
            with self.assertRaises(ValueError): C.verify_capture(self.complete, self.expected)
        finally: window.write_bytes(original)
        with self.assertRaises(FileNotFoundError): C.verify_capture(RUN/'synthetic-fixture', self.expected)

    def test_fixed_range_and_finite_budgets_cannot_be_widened(self):
        for index,offset,count in ((383,C.MAX_P1,C.BLOCK),(-1,0,C.BLOCK),(0,0,C.BLOCK+1),(True,0,C.BLOCK),(0,1,C.BLOCK)):
            with self.assertRaises(ValueError): C.Request('1'*32,'2'*32,index,offset,count)
        for total in (float('inf'),float('nan'),601.0,0.0):
            with self.assertRaises(ValueError): C._capture(lambda:None, RUN/'invalid-budget', self.expected, '1'*64,total_seconds=total)
        self.assertFalse((RUN/'invalid-budget').exists())

    def test_cli_actual_local_provider_and_verified_output(self):
        new_directory(RUN/'cli-input', {'input.p1': self.full})
        base = [sys.executable,'-B','-m','fx3_recovery']
        for args in (['capture-local','--input',str(RUN/'cli-input/input.p1'),'--sha256',self.expected,'--body-tag','1'*64,'--out',str(RUN/'cli-capture')],
                     ['verify-capture','--capture',str(RUN/'cli-capture'),'--sha256',self.expected]):
            completed = subprocess.run(base+args, cwd=HERE, text=True, capture_output=True)
            self.assertEqual(completed.returncode,0,completed.stdout+completed.stderr)
            self.assertFalse(json.loads(completed.stdout)['flashable'])
        completed = subprocess.run(base+['capture-local','--flash'],cwd=HERE,text=True,capture_output=True)
        self.assertEqual(completed.returncode,2)

    def test_actual_process_block_does_not_start_close_or_retry(self):
        script = '''
import sys
from fx3_recovery import capture as C
clock = [0.0]
class Blocked(C.RegularFileSource):
    def read_at(self, request, deadline):
        print('IN_FLIGHT',flush=True)
        assert sys.stdin.buffer.read(1) == b'R'
        clock[0] = 6.0
        return super().read_at(request,deadline)
    def close(self):
        print('CLOSE_AFTER_RETURN',flush=True)
        return super().close()
try:
    C._capture(lambda:Blocked(sys.argv[1],sys.argv[3]),sys.argv[2],sys.argv[3],'1'*64,clock=lambda:clock[0])
except C.CaptureFailure as error:
    print(error.state,flush=True)
'''
        out = RUN/'blocked-process'
        child = subprocess.Popen([sys.executable,'-B','-c',script,str(self.input),str(out),self.expected],
                                 cwd=HERE,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        selector = selectors.DefaultSelector(); selector.register(child.stdout,selectors.EVENT_READ)
        try:
            self.assertTrue(selector.select(timeout=5),'fixture did not reach the in-flight barrier')
            self.assertEqual(child.stdout.readline(),b'IN_FLIGHT\n')
            self.assertIsNone(child.poll())
            rows = [json.loads(line) for line in (out/'journal.jsonl').read_text().splitlines()]
            self.assertEqual(rows[-1]['event'],'read-in-flight')
            self.assertEqual(sum(row['event']=='read-in-flight' for row in rows),1)
            self.assertFalse((out/'source-closed.json').exists()); self.assertFalse((out/'complete.json').exists())
            self.assertFalse(selector.select(timeout=0.05),'no close or retry while the call is blocked')
        finally:
            # Cooperatively return the fixture call, including on assertion
            # failure. No process kill, reset, or provider retry.
            stdout,stderr = child.communicate(input=b'R',timeout=10)
            selector.close()
        self.assertEqual(child.returncode,0,stderr)
        self.assertEqual(stdout,b'CLOSE_AFTER_RETURN\nINCOMPLETE\n')
        self.assertFalse((out/'source.p1').exists())

    def test_evidence_write_failure_keeps_partial_data_and_stops(self):
        original = C.PrivateDirectory.put; objects = []; out = RUN/'evidence-write-failed'
        def fail(directory,name,data):
            if name == 'chunk-001.bin': raise OSError('fixture disk full')
            return original(directory,name,data)
        def factory():
            obj = FaultSource(self.input,self.expected); objects.append(obj); return obj
        with patch.object(C.PrivateDirectory,'put',fail):
            with self.assertRaises(C.CaptureFailure): C._capture(factory,out,self.expected,'1'*64)
        self.assertEqual(objects[0].calls,[0,1]); self.assertEqual(objects[0].closes,1)
        self.assertTrue((out/'chunk-000.bin').is_file()); self.assertTrue((out/'failure.json').is_file())
        self.assertFalse((out/'complete.json').exists()); self.assertFalse((out/'source.p1').exists())
        with self.assertRaises(ValueError): C.verify_capture(out,self.expected)

    @classmethod
    def tearDownClass(cls):
        if read_file(cls.original_path,C.MAX_P1) != cls.original: raise AssertionError('Sony original changed')


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(CaptureTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = {'status':'PASS_LOCAL_BOUNDED_CAPTURE' if result.wasSuccessful() else 'FAIL',
              'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
              'synthetic_fixture_sha256':CaptureTests.expected,'original_reference_sha256':CaptureTests.original_sha,
              'source_sha256':{str(p.relative_to(HERE)):sha256(p.read_bytes()).hexdigest() for p in sorted((HERE/'fx3_recovery').glob('*.py'))},
              'test_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),
              'new_camera_or_USB_operations':0,'actual7_02_camera_source_tested':False,'hardware_validated':False}
    new_directory(RUN/'test-receipt',{'results.json':encode(report)})
    raise SystemExit(0 if result.wasSuccessful() else 1)
