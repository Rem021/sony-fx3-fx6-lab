"""Ordinary-user fixture process; runs own ARM64 model, never Sony/Linux."""
from pathlib import Path
from hashlib import sha256
import argparse,importlib.util,json,os,sys
H=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--shared',required=True);p.add_argument('--module',required=True);p.add_argument('--source',required=True);p.add_argument('--nonce',required=True);a=p.parse_args()
run=Path(a.run);assert not run.exists();run.mkdir(mode=0o700)
sys.argv=[sys.argv[0],str(run)];sp=importlib.util.spec_from_file_location('fixture_child_types219',H/'test_handoff.py');M=importlib.util.module_from_spec(sp);sys.modules[sp.name]=M;sp.loader.exec_module(M)
B=M.B;read=M.read_file;ROOT=M.ROOT
profiles={}
for path,size,digest in B.FILE_PROFILE:
 raw=read(ROOT/'work/sony-firmware-20261024/stage213-AP-eMMC-boot-asset-search/originals/current-p3-initrd'/path.lstrip('/'),size);assert sha256(raw).hexdigest()==digest;profiles[path]=raw
old=H.parent/'stage218-fixed-shell-process-filter';busy=read(old/'originals/busybox',423000);parent=read(old/'originals/im.elf',40920)
raw=read(Path(a.module),M.D.L.MAX_OBJECT);req=B.request('b'*32,'boot0',0)
k=M.Kernel('kernel',Path(a.source),profiles,busy,parent,Path(a.shared),req,a.nonce,pid=os.getpid());g=M.M.Guest(raw,k,0x10000000);g.init()
print(json.dumps({'ready':True,'os_pid':os.getpid()}),flush=True)
if sys.stdin.readline()!='GO\n':raise SystemExit(2)
code=g.run_worker();assert not g.errors and not k.errors and set(k.fds)==set(k.closed)
report={'os_pid':os.getpid(),'modeled_PID_equals_actual_test_PID':k.pid==os.getpid(),'guest_result':code,'source_reads':len(k.source_reads),'claims':k.claim_attempts,'module_sha256':sha256(raw).hexdigest(),
 'actual_target_root_or_Linux_process_verified':False,'Sony_or_Linux_code_executed':False}
with (run/'child-result.json').open('x') as out:json.dump(report,out,indent=2);out.write('\n');out.flush();os.fsync(out.fileno())
print(json.dumps(report),flush=True)
