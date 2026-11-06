"""Pin exact owning inputs and derive two minimal files. No runtime imports."""
from pathlib import Path
import hashlib,json,subprocess,plistlib,re,difflib
R=Path('/Volumes/KAFU2T/AI/Projects/Mac');O=Path(__file__).resolve().parent;D=O.parent;G=R/'work/fx3-vm-20261101/lead-claude/impl/gpe-perf';H=R/'work/fx3-vm-20261101/menu-repair-01/runtime/helpers'
assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
paths=[D/'r41-command-entry-timing-task.txt',D/'r40-coordinator-final-review.json',D/'r40-deepseek-menu-timing/review-revision-1/REPORT.md',D/'r40-deepseek-menu-timing/review-revision-1/results.json',D/'r40-deepseek-menu-timing/review-revision-1/analyze_menu_timing.py',D/'r33-causal-observation-candidate/GPE-SOURCE-BINDING.json',D/'r36-fixed-slot-package/MANIFEST.json',D/'r36-fixed-slot-package/source-index.json',G/'build/cross-build.json',G/'build/provenance.json',G/'check_adapter.c',H/'fx3-gpe-observe-v26-perf-ap105.so']
recipe=json.loads((G/'build/cross-build.json').read_text())['command'];paths.extend([Path(recipe[0]),*[Path(x) for x in recipe if x.startswith('/') and Path(x).suffix in ('.c','.S','.so')]])
include_dirs=[G,H,R/'work/fx3-vm-20261101/lead-claude/impl/gpe-p3-approx',R/'work/fx3-vm-20261101/lead-claude/impl/gpe-p3-approx/compat']
queue=[G/'fx3-gpe-observe-v26-perf.c',G/'fx3-gpe-backend-v9.c'];closure=[]
while queue:
 p=queue.pop(0)
 if p in closure:continue
 closure.append(p)
 for name in re.findall(r'^\s*#\s*include\s+"([^"]+)"',p.read_text(),re.M):
  choices=[p.parent/name,*[d/name for d in include_dirs]];target=next((x for x in choices if x.is_file()),None);assert target,name;queue.append(target)
paths.extend(closure);paths.extend([H/'fx3-complete104-observe-v1.h',H/'fx3-gpe-command-wait102-v1.h'])
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
rows={str(p.resolve()):{'sha256':sha(p),'bytes':p.stat().st_size} for p in paths}
source=(G/'fx3-gpe-observe-v26-perf.c').read_text();assert sha(G/'fx3-gpe-observe-v26-perf.c')=='06f6d2968f55b2579b950df2a4954f3976fa9f624a5c6a987e27b253b475e1f9'
old='static int command(unsigned op,int g,int c,unsigned seq,unsigned src,const void *p){\n';new=old+' int entry_errno41=*__errno_location();U entry_ns41=gpe102_now();*__errno_location()=entry_errno41;\n';assert source.count(old)==1;source=source.replace(old,new)
assert source.count('gpe104_command_return(seq,op,src,5)')==1 and source.count('gpe104_command_return(seq,op,src,result)')==1
source=source.replace('gpe104_command_return(seq,op,src,5)','gpe104_command_return(seq,op,src,5,entry_ns41)').replace('gpe104_command_return(seq,op,src,result)','gpe104_command_return(seq,op,src,result,entry_ns41)');(O/'src/fx3-gpe-observe-v26-perf.c').write_text(source)
p=H/'fx3-complete104-observe-v1.h';s=p.read_text();old='static void gpe104_command_return(unsigned seq,unsigned op,unsigned source,int result)';assert s.count(old)==1;s=s.replace(old,old[:-1]+',U entry_ns41)');old='call_path=adapter_return_to_original_Main unchanged=1\\n",tid,tp,gpe102_now(),seq,op,source,result,saved)';assert s.count(old)==1;s=s.replace(old,'call_path=adapter_return_to_original_Main unchanged=1 entry_ns=%lu\\n",tid,tp,gpe102_now(),seq,op,source,result,saved,entry_ns41)');(O/'src'/p.name).write_text(s)
index=json.loads((D/'r36-fixed-slot-package/source-index.json').read_text());m=next(x for x in index if x['name']=='simulation/fx3-gpe-observe-v7.so');cpio=D/'r36-fixed-slot-package/guest.cpio'
with cpio.open('rb') as f:
 f.seek(m['header_offset']);head=f.read(110);assert head.hex()==m['header_hex'];f.seek(m['payload_offset']);member=f.read(m['size'])
hash_member=hashlib.sha256(member).hexdigest();assert hash_member==sha(H/'fx3-gpe-observe-v26-perf-ap105.so')=='30667f76ccfa3f0b9b4834b1fbce725a76683ccd775615ed66955d49200d7ba4'
rows[str(cpio)]={'sha256':sha(cpio),'bytes':cpio.stat().st_size}
(O/'INPUTS-BEFORE.json').write_text(json.dumps({'files':rows,'scope':'only actual r41 source/recipe/binding/history inputs; no inherited 1398 matrix'},indent=2)+'\n')
(O/'BINDING.json').write_text(json.dumps({'actual_member':m,'member_sha256':hash_member,'actual_helper':str(H/'fx3-gpe-observe-v26-perf-ap105.so'),'source_sha256':sha(G/'fx3-gpe-observe-v26-perf.c'),'source_include_closure':[str(p) for p in closure],'original_recipe':recipe,'candidate_files':['src/fx3-gpe-observe-v26-perf.c','src/fx3-complete104-observe-v1.h'],'fixed_hardware_and_host_policy_unchanged':True},indent=2)+'\n')
diff=''
for old,new in [(G/'fx3-gpe-observe-v26-perf.c',O/'src/fx3-gpe-observe-v26-perf.c'),(H/'fx3-complete104-observe-v1.h',O/'src/fx3-complete104-observe-v1.h')]:diff+=''.join(difflib.unified_diff(old.read_text().splitlines(True),new.read_text().splitlines(True),fromfile=str(old),tofile='r41/src/'+new.name))
(O/'source.diff').write_text(diff);print('pinned',len(rows),'inputs; quoted closure',len(closure),'member',m['size'],hash_member)
