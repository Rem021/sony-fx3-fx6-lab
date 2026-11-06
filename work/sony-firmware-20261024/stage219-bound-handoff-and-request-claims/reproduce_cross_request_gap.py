"""Negative safety evidence: distinct requests can overlap in current model.

This intentionally confirms an OPEN blocker; it is not a readiness pass.
"""
from pathlib import Path
from hashlib import sha256
import importlib.util,json,sys,threading
H=Path(__file__).resolve().parent;RUN=Path(sys.argv[1]);sys.argv=[sys.argv[0],str(RUN)]
s=importlib.util.spec_from_file_location('cross_request_model219',H/'test_handoff.py');M=importlib.util.module_from_spec(s);sys.modules[s.name]=M;s.loader.exec_module(M)
M.Tests.setUpClass();case=M.Tests();shared=RUN/'shared';req1=M.B.request('8'*32,'boot0',0);req2=M.B.request('9'*32,'boot0',0)
k1,g1=case.make('first-pending',shared=shared,req=req1,nonce='7'*64,fault='block',pid=5678)
returned=[];errors=[]
def first():
    try:returned.append(g1.run_worker())
    except BaseException as e:errors.append(repr(e))
thread=threading.Thread(target=first);thread.start()
try:
    assert k1.entered.wait(timeout=5) and thread.is_alive() and returned==[]
    k2,g2=case.make('second-while-pending',shared=shared,req=req2,nonce='8'*64,pid=5679)
    second=g2.run_worker()
    evidence=dict(first_still_live=thread.is_alive(),first_has_not_returned=returned==[],first_source_reads=len(k1.source_reads),second_result=second,second_source_reads=len(k2.source_reads))
    assert evidence['first_still_live'] and evidence['first_has_not_returned'] and second==0 and evidence['second_source_reads']==2
finally:k1.release.set();thread.join(timeout=10)
assert not thread.is_alive() and not errors and returned and returned[0]!=0
assert not g1.errors and not g2.errors and set(k1.fds)==set(k1.closed) and set(k2.fds)==set(k2.closed)
report=dict(status='CONFIRMED_OPEN_CROSS_REQUEST_EXCLUSION_GAP_IN_FAKE_KERNEL_MODEL',evidence=evidence,first_return_after_cooperative_release=returned[0],
    module_sha256=sha256(M.Tests.raw).hexdigest(),module_source_sha256=sha256((H/'boot_module.c').read_bytes()).hexdigest(),
    handoff_implementation_sha256=sha256((H/'handoff_impl.inc').read_bytes()).hexdigest(),
    reproduction_source_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
    ordinary_association_tests_do_not_prove_global_exclusion=True,readiness_pass=False,camera_deployment_released=False,
    own_ARM64_code_executed=True,Sony_or_Linux_kernel_executed=False,new_camera_operations=0)
M.new_directory(RUN/'receipt',{'gap.json':M.encode(report)})
print(json.dumps(report))
