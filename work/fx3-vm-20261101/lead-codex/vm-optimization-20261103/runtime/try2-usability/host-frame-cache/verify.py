"""Offline production-poll differential tests. Writes only fresh local result dirs."""
import sys
sys.dont_write_bytecode = True
from pathlib import Path
import hashlib, importlib.util, struct, json, shlex, time, statistics, tempfile, difflib
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
RUN=ROOT/'runs/try2passivetiming-internal-v21-2383af57'
sys.path.insert(0,str(RUN/'observer-source'))
import osd_ring93_v4 as ring

def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
base=load('baseline',HERE/'baseline.py');cand=load('candidate',HERE/'trial_ring_cached.py')
sha=lambda b:hashlib.sha256(b).hexdigest()
inputs=[ROOT/'trial_ring_usability.py',RUN/'osd-ring-final.bin',RUN/'osd-ring-readback.json',RUN/'trial-final.png',RUN/'observer-source/osd_ring93_v4.py']
before={str(p):sha(p.read_bytes()) for p in inputs}
assert (HERE/'baseline.py').read_bytes()==inputs[0].read_bytes()
result=Path(tempfile.mkdtemp(prefix='verification-',dir=HERE))
blob=inputs[1].read_bytes();head=blob[:256]
slots=sorted([blob[ring.HEADER+i*ring.STRIDE:ring.HEADER+(i+1)*ring.STRIDE] for i in range(8)],key=lambda b:struct.unpack_from('<Q',b)[0])
# Exact original slots; only global sequence selects each previously committed slot.
def pair(slot):
 v=struct.unpack_from('<36Q',slot);g=list(struct.unpack_from('<16Q',head));g[3]=v[1];g[4]=v[0]
 return struct.pack('<16Q',*g)+head[128:],slot
real=[pair(s) for s in slots]
(result/'fixed-slots.bin').write_bytes(b''.join(slots))
class FakeQMP:
 def __init__(self,folder): self.folder=folder;self.calls=[]
 def __call__(self,cmd,args):
  assert cmd=='human-monitor-command'
  op,addr,n,path=shlex.split(args['command-line']);addr=int(addr,0);n=int(n,0)
  assert op=='pmemsave' and Path(path).parent==self.folder
  seq=struct.unpack_from('<16Q',self.frame[0])[4]
  expected=ring.BASE if n==256 else ring.BASE+ring.HEADER+((seq-1)%8)*ring.STRIDE
  assert addr==expected
  data=self.frame[0] if n==256 else self.frame[1];assert len(data)==n
  Path(path).write_bytes(data);self.calls.append((addr,n));return {'return':''}
class State:
 def __init__(self):self.published=[]
 def publish(self,png,record):self.published.append((png,record.copy()))
def exercise(mod,label,frames):
 folder=result/label;folder.mkdir();q=FakeQMP(folder);state=State();r=mod.TrialRingReader(folder,q,state)
 counts={k:0 for k in ['validate_slot','fnv','rgba','png']};orig={k:getattr(mod,k) for k in counts}
 for k in counts:
  def wrap(*a,_k=k,**kw): counts[_k]+=1;return orig[_k](*a,**kw)
  setattr(mod,k,wrap)
 elapsed=[];snapshots=[]
 try:
  for f in frames:
   q.frame=f;t=time.perf_counter();r.poll();elapsed.append((time.perf_counter()-t)*1000)
   snapshots.append((r.current_png,dict(r.current_record) if r.current_record else None))
   if r.current_record:
    assert json.loads((folder/'trial-frame.json').read_text())==r.current_record
    assert (folder/'trial-frame.png').read_bytes()==r.current_png
    assert (folder/'trial-frame.raw').read_bytes()==r.current_raw
    assert not list(folder.glob('*.tmp'))
 finally:
  for k,v in orig.items():setattr(mod,k,v)
 return r,state,counts,elapsed,snapshots

def compare(a,b):
 assert len(a)==len(b)
 for (pa,ra),(pb,rb) in zip(a,b):
  assert pa==pb
  if ra:ra={k:v for k,v in ra.items() if k!='host_monotonic'};rb={k:v for k,v in rb.items() if k!='host_monotonic'}
  assert ra==rb
b,bs,bc,bt,bshots=exercise(base,'real-baseline',real)
c,cs,cc,ct,cshots=exercise(cand,'real-candidate',real)
compare(bshots,cshots)
assert cc=={'validate_slot':8,'fnv':8,'rgba':1,'png':1} and c.cache_hits==7
assert c.current_png==(RUN/'trial-final.png').read_bytes()
assert [x[1]['sequence'] for x in cs.published]==list(range(4267,4275))
# Synthetic mutations are explicitly distinct from the exact real fragment.
def changed(seq,changes=None,pixel=False):
 s=bytearray(slots[-1]);v=list(struct.unpack_from('<36Q',s));v[0]=v[2]=seq
 for k,val in (changes or {}).items():v[k]=val
 if pixel:s[512]^=1;v[12]=ring.fnv(s[512:512+v[11]])
 struct.pack_into('<36Q',s,0,*v);return pair(bytes(s))
v=struct.unpack_from('<36Q',slots[-1])
frames=[changed(5000),changed(5001,{1:2,3:9999,4:9998,5:v[5]+1,33:v[5]+1,13:v[13]+1,29:v[29]+1,30:v[30]+1}),changed(5002,pixel=True),changed(5003),changed(5004,{7:1,8:320,10:320}),changed(5005),changed(5006,{8:639}),changed(5007),changed(5008,{9:479}),changed(5009),changed(5010,{9:479,10:641}),changed(5011),changed(5012,{26:0}),changed(5013,{12:v[12]^1}),changed(5014)]
b2,sb2,bc2,_,bs2=exercise(base,'mutations-baseline',frames)
c2,sc2,cc2,_,cs2=exercise(cand,'mutations-candidate',frames)
compare(bs2,cs2)
assert len(sc2.published)==13 and len(c2.rejects)==2 and c2.cache_hits==2 and c2.cache_misses==11
assert cc2=={'validate_slot':15,'fnv':14,'rgba':11,'png':11}
assert c2.rejects[0]['reason']=='invalid registered frame target tuple'
assert c2.rejects[1]['reason']=='concurrent overwrite checksum mismatch'
assert cs2[1][1]['epoch']==2 and cs2[1][1]['token']!=cs2[0][1]['token'] and cs2[1][1]['native_identity']!=cs2[0][1]['native_identity'] and cs2[1][1]['registered_target']!=cs2[0][1]['registered_target']
# Same seq does not re-publish; current entry remains a single immutable tuple.
q=c2.qmp;q.frame=frames[-1];c2.poll();assert len(sc2.published)==13
assert isinstance(c2._pixel_cache,tuple) and len(c2._pixel_cache)==5
c2.evidence('preserved');saved={p.name:sha(p.read_bytes()) for p in c2.run.glob('trial-preserved.*')}
try:c2.evidence('preserved');raise AssertionError('overwrote evidence')
except RuntimeError:pass
assert saved=={p.name:sha(p.read_bytes()) for p in c2.run.glob('trial-preserved.*')}
bench={}
for mod,label in [(base,'baseline'),(cand,'candidate')]:
 samples=[]
 for i in range(3):
  r,s,cnt,t,shots=exercise(mod,f'bench-{label}-{i}',real);samples.append(sum(t))
 bench[label]={'eight_polls_ms':samples,'median_ms':statistics.median(samples),'counts_per_run':cnt}
assert before=={str(p):sha(p.read_bytes()) for p in inputs}
receipt={'result':'PASS','python':sys.version,'fixed_input_sha256':before,'fragment_sha256':sha(b''.join(slots)),'fragment_sequences':[4267,4274],'real_counts':{'baseline':bc,'candidate':cc,'hits':c.cache_hits,'misses':c.cache_misses},'mutation_counts':cc2,'mutation_hits':c2.cache_hits,'mutation_misses':c2.cache_misses,'tests':['exact real fragment PNG and metadata equality','original final PNG byte equality','new seq and changed epoch/token/native identity/target publish','raw mutation misses','fmt/width/height/stride misses','illegal target rejected','torn FNV rejected','same seq skipped as baseline','atomic outputs verified on every accepted poll','evidence overwrite refused','source evidence hashes unchanged'],'benchmark':bench,'candidate_sha256':sha((HERE/'trial_ring_cached.py').read_bytes()),'cache_retained_payload_bytes':len(c2._pixel_cache[1])+len(c2._pixel_cache[2]),'scope':'offline fake QMP production poll; no QEMU or menu latency claim'}
(result/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'report':str(result/'receipt.json'),**receipt},indent=2))
