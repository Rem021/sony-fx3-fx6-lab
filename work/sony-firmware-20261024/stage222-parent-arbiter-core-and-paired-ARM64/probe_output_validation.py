"""Same corrupt-output probe against two pinned OWN parent binaries only."""
from pathlib import Path
from hashlib import sha256
import argparse,importlib.util,json,sys
H=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--module',required=True);a=p.parse_args()
module=Path(a.module);raw=module.read_bytes();digest=sha256(raw).hexdigest()
expected={'eda3c4bbd8b3917d5e873b1b57664662d7fdac324ebe81d61214b02898818538':0,
          '5a9ab04e92e06dd5fbddbff0c95e1736ac4c0850a8ad9a346a01669104e0eb39':2}
assert digest in expected,'only the two reviewed own parent images are permitted'
sys.argv=[sys.argv[0],a.run];sys.path.insert(0,str(H));s=importlib.util.spec_from_file_location('output_boundary222',H/'test_paired_arbiter.py');M=importlib.util.module_from_spec(s);sys.modules[s.name]=M;s.loader.exec_module(M)
M.check_volume();M.RUN.mkdir(mode=0o700);C=M.Tests;C.parent_raw=raw
C.child_raw=M.read_file(M.OLD/'runs-final-v2/built/boot-module.so',M.D.L.MAX_OBJECT)
assert sha256(C.child_raw).hexdigest()=='23327fd5c43ecf44858f0705edc30db1ed795d1bc2272bf75bbeaf1ae8e8b3a3'
C.source=M.OLD.parent/'stage219-bound-handoff-and-request-claims/runs-final-v2/fixture/synthetic.boot';C.profiles={}
for path,size,check in M.B.FILE_PROFILE:
    data=M.read_file(M.R/'work/sony-firmware-20261024/stage213-AP-eMMC-boot-asset-search/originals/current-p3-initrd'/path.lstrip('/'),size)
    assert sha256(data).hexdigest()==check;C.profiles[path]=data
old=M.OLD.parent/'stage218-fixed-shell-process-filter';C.busy=M.read_file(old/'originals/busybox',423000);C.im=M.read_file(old/'originals/im.elf',40920)
C.pairs=[];C.parents=[];C.cases=[];C.pid=1234
case=C();q=case.pair('same-corrupt-probe',mode='hold-exit');assert case.start(q)==1;case.drive(q,lambda state:q['link'].returned.is_set())
chunk=next(q['child'].output.glob('chunk-*.bin'));data=bytearray(chunk.read_bytes());data[-1]^=1;chunk.write_bytes(data)
q['link'].exit_release.set();state=case.drive(q);case.finish(q);assert state==expected[digest] and q['link'].exit_status==0
rejected=False
try:M.B.decode_window(q['child'].output,0)
except ValueError as e:rejected=True;error=str(e)
assert rejected
report=dict(schema='fx3-own-parent-output-validation-differential-v1',parent_module_sha256=digest,
    parent_state=state,old_unsafe_release_confirmed=state==0,new_held_regression_confirmed=state==2,
    child_return=q['link'].child_return,exit_status=q['link'].exit_status,independent_decoder_rejected=True,decoder_error=error,
    probe_source_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),model_source_sha256=sha256((H/'paired_model.py').read_bytes()).hexdigest(),
    all_fixture_threads_terminal=not q['link'].thread.is_alive(),readiness_pass=False,hardware_validated=False,new_camera_operations=0)
M.new_directory(M.RUN/'receipt',{'probe.json':M.encode(report)});print(json.dumps(report))
