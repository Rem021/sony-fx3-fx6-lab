"""Additional integration checks; does not rerun the eight-window suite."""
from pathlib import Path
from hashlib import sha256
import importlib.util,json,sys,unittest
from live_arbiter import H,LiveArbiter,Denied
RUN=Path(sys.argv[1]);sys.argv=[sys.argv[0],str(RUN)]
sp=importlib.util.spec_from_file_location('arbiter_test_helpers220',H/'test_live_arbiter.py');M=importlib.util.module_from_spec(sp);sys.modules[sp.name]=M;sp.loader.exec_module(M)

class Boundaries(M.Tests):
    # Load only the following two tests; inherited helper methods are reused.
    def test_11_repeated_window_private_nonzero_result_does_not_release(self):
        o=self.owner('repeat');shared=RUN/'repeat-claims';req=self.request()
        o.start(req,RUN/'first',shared);self.finish(o);self.assertEqual(o.state,'IDLE')
        o.start(req,RUN/'repeat',shared);self.finish(o);self.assertEqual(o.state,'HELD_UNKNOWN')
        d=o.history[-1]['done'];self.assertEqual(d['result'],51);self.assertEqual(d['source_reads'],0)
        with self.assertRaises(Denied):self.start(o,'after-repeat',request=self.request('c'))

    def test_12_success_packet_with_modified_chunk_is_not_clean(self):
        o=self.owner('chunk');self.start(o,'chunk-first',mode='post-done-wait')
        M.wait(o,lambda v:v.get('done_received',False));d=o.current['done'];self.assertEqual(d['result'],0)
        output=Path(d['output']);chunk=next(output.glob('chunk-*.bin'))
        raw=bytearray(chunk.read_bytes());raw[-1]^=1;chunk.write_bytes(raw)
        o.release_cooperative_fixture();self.finish(o);self.assertEqual(o.state,'HELD_UNKNOWN')
        self.assertTrue(any('CRC' in reason for reason in o.history[-1]['reasons']))
        with self.assertRaises(Denied):self.start(o,'chunk-second')

if __name__=='__main__':
    suite=unittest.TestSuite([Boundaries(name) for name in (
        'test_11_repeated_window_private_nonzero_result_does_not_release',
        'test_12_success_packet_with_modified_chunk_is_not_clean')])
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    report=dict(schema='fx3-live-arbiter-result-boundary-tests-v1',status='PASS' if result.wasSuccessful() else 'FAIL',
        tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),
        owners=[dict(state=o.state,history=o.history,children=len(o.children),all_children_terminal=all(j['process'].poll() is not None for j in o.children)) for o in Boundaries.owners],
        source_hashes={p.name:sha256(p.read_bytes()).hexdigest() for p in (H/'live_arbiter.py',H/'model_worker.py',H/'test_result_boundaries.py')},
        new_camera_operations=0,target_ARM64_entry_global_fence_integrated=False,hardware_or_recovery_verified=False)
    M.new_directory(RUN/'receipt',{'results.json':M.encode(report)})
    raise SystemExit(0 if result.wasSuccessful() else 1)
