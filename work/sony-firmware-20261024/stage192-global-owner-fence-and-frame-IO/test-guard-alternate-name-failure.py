"""Real host processes exercise the append-only fence; no camera or root."""
from pathlib import Path
from hashlib import sha256
import json,os,secrets,struct,subprocess,time,traceback
HERE=Path(__file__).resolve().parent
build=json.loads((HERE/'guard-build-receipt-v2.json').read_text());HELPER=Path(build['path'])
assert HELPER.name=='guard-fixture' and sha256(HELPER.read_bytes()).hexdigest()==build['sha256']
assert 'IOKit.framework' not in build['dependencies'] and os.getuid()==os.geteuid()!=0
base=HERE/'runs'/('guard-'+secrets.token_hex(4));base.mkdir(mode=0o700)
results=[]
def run(path,mode='C',alternate=False):
 r=subprocess.run([str(HELPER),str(path),mode]+(['alternate'] if alternate else []),capture_output=True,text=True,timeout=5)
 assert 'ERROR: AddressSanitizer' not in r.stderr and 'runtime error:' not in r.stderr,r.stderr
 return r,[json.loads(line) for line in r.stdout.splitlines()]
def check_file(path):
 raw=path.read_bytes();assert len(raw)%256==0;last=bytes(256);states=[]
 for i in range(len(raw)//256):
  r=raw[i*256:(i+1)*256];assert r[:12]==b'FX3-GUARD-v1'
  assert struct.unpack_from('<I',r,24)[0]==i+1 and r[104:136]==last[224:256]
  assert sha256(r[:224]).digest()==r[224:]
  states.append(struct.unpack_from('<I',r,20)[0]);last=r
 return raw,states
def fresh(name):
 p=base/name;p.parent.mkdir(mode=0o700,exist_ok=True);return p
def put(p,data):
 fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.write(fd,data);os.close(fd)
def case(name,fn):
 try:fn();results.append({'name':name,'status':'PASS'})
 except BaseException as e:
  results.append({'name':name,'status':'FAIL','error':repr(e),'traceback':traceback.format_exc()})
  with (HERE/('guard-failure-'+str(time.time_ns())+'.json')).open('x') as f:json.dump({'results':results},f,indent=2)
  raise
def normal():
 p=fresh('normal');r,d=run(p);assert r.returncode==0 and d==[{'begin':0,'count':1,'pid':d[0]['pid']},{'finish':0,'clean':True}]
 assert check_file(p)[1]==[1,2]
 before=p.read_bytes();r,d=run(p);assert r.returncode==0 and d[0]['count']==3
 raw,states=check_file(p);assert states==[1,2,1,2] and raw.startswith(before)
def unknown():
 p=fresh('unknown');r,d=run(p,'U');assert r.returncode==0 and check_file(p)[1]==[1,3]
 before=p.read_bytes();r,d=run(p);assert d[0]['begin']==3 and p.read_bytes()==before
def cross_grant():
 p=fresh('cross-grant');assert run(p)[0].returncode==0
 before=p.read_bytes();assert run(p,alternate=True)[0].returncode==0
 raw,states=check_file(p);assert states==[1,2,1,2] and raw[:512]==before
 assert raw[72:104]!=raw[512+72:512+104]
def busy_then_clean():
 p=fresh('busy');a=subprocess.Popen([str(HELPER),str(p),'H'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 first=json.loads(a.stdout.readline());assert first['begin']==0
 try:
  before=p.read_bytes();r,d=run(p);assert d[0]['begin']==1 and p.read_bytes()==before
  a.stdin.write('C');a.stdin.flush();out,err=a.communicate(timeout=5);assert a.returncode==0 and not err,(out,err)
  r,d=run(p);assert d[0]['begin']==0 and check_file(p)[1]==[1,2,1,2]
 finally:
  if a.poll() is None:a.stdin.close();a.wait(timeout=5)
def dead_pid_not_clean():
 p=fresh('dead');a=subprocess.Popen([str(HELPER),str(p),'H'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 assert json.loads(a.stdout.readline())['begin']==0
 a.kill();a.communicate(timeout=5) # own journal-only process, no device provider
 before=p.read_bytes();r,d=run(p);assert d[0]['begin']==3 and check_file(p)[1]==[1] and p.read_bytes()==before
def corrupt(kind):
 p=fresh('corrupt-'+kind);assert run(p)[0].returncode==0;raw=bytearray(p.read_bytes())
 if kind=='payload':raw[56]^=1
 if kind=='digest':raw[255]^=1
 if kind=='chain':raw[256+104]^=1;raw[256+224:512]=sha256(raw[256:256+224]).digest()
 if kind=='sequence':struct.pack_into('<I',raw,256+24,99);raw[256+224:512]=sha256(raw[256:256+224]).digest()
 if kind=='initial-state':struct.pack_into('<I',raw,20,2);raw[224:256]=sha256(raw[:224]).digest()
 if kind=='partial':raw=raw[:-1]
 p.write_bytes(raw);r,d=run(p);assert d[0]['begin']==2 and p.read_bytes()==raw
def wrong_mode():
 p=fresh('mode');put(p,b'');os.chmod(p,0o644);r,d=run(p);assert d[0]['begin']==2 and p.stat().st_size==0
def symlink():
 target=fresh('link-target');put(target,b'original');p=fresh('symbolic');p.symlink_to(target)
 r,d=run(p);assert d[0]['begin']==2 and target.read_bytes()==b'original'
def hardlink():
 target=fresh('hard-target');put(target,b'');p=fresh('hard');os.link(target,p)
 r,d=run(p);assert d[0]['begin']==2 and target.stat().st_size==0
def fifo():
 p=fresh('fifo');os.mkfifo(p,0o600);r,d=run(p);assert d[0]['begin']==2
def directory():
 p=fresh('directory');p.mkdir();r,d=run(p);assert d[0]['begin']==2
def full():
 seed=fresh('seed');assert run(seed)[0].returncode==0;raw=seed.read_bytes();template=[raw[:256],raw[256:]]
 data=bytearray();last=bytes(32)
 for i in range(2048):
  r=bytearray(template[i%2]);struct.pack_into('<I',r,24,i+1);r[104:136]=last;r[224:]=sha256(r[:224]).digest();last=r[224:];data+=r
 p=fresh('full');put(p,data);r,d=run(p);assert d[0]['begin']==5 and p.read_bytes()==data
def too_big():
 p=fresh('too-big');put(p,bytes(256*2049));r,d=run(p);assert d[0]['begin']==2 and p.stat().st_size==256*2049
case('clean_append_history',normal)
case('unknown_blocks_next',unknown)
case('different_grant_after_clean',cross_grant)
case('simultaneous_processes_busy_then_clean',busy_then_clean)
case('dead_PID_does_not_clear_OWNED',dead_pid_not_clean)
for k in ('payload','digest','chain','sequence','initial-state','partial'):case('corrupt_'+k,lambda k=k:corrupt(k))
case('wrong_permissions',wrong_mode);case('symlink_refused',symlink);case('hardlink_refused',hardlink)
case('fifo_nonblocking_refused',fifo);case('directory_refused',directory);case('full_journal_denied',full);case('oversize_journal_denied',too_big)
report={'status':'PASS_HOST_GLOBAL_FENCE','tests_run':len(results),'results':results,
 'sanitizers':['address','undefined'],'journal_sha256_verifier':'independent Python hashlib/struct',
 'root_or_camera_operations':0,'test_source_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),
 'build_receipt_sha256':sha256((HERE/'guard-build-receipt-v2.json').read_bytes()).hexdigest(),
 'running_kernel_advisory_lock_tested':True,'physical_device_fencing_or_recovery_proven':False}
with (HERE/'guard-results.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps({k:v for k,v in report.items() if k!='results'}))
