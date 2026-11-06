from pathlib import Path
import json,hashlib,difflib
O=Path(__file__).resolve().parent;S=O.parent/'r37-diagnostic-runner-candidate'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
core=json.loads((S/'CORE-SOURCE-FREEZE.json').read_text());core['runtime-wrapper/cleanup_evidence.py']=''
core={n:sha(O/n) for n in core};(O/'CORE-SOURCE-FREEZE.json').write_text(json.dumps(core,indent=2)+'\n')
n='return-tools/return_adapter.py';s=(S/n).read_text().replace("OPERATE_SHA='97e41bc5687fd6c9397fcca639355624c70e368761e1e24ad4329a85d9408741'","OPERATE_SHA='"+sha(O/'runtime-wrapper/operate.py')+"'").replace("CORE_FREEZE_SHA='7752a6fd7cdb74def7a3cfa9659ed6a1a4f6ab23708a5aaaed5f345e7c46f303'","CORE_FREEZE_SHA='"+sha(O/'CORE-SOURCE-FREEZE.json')+"'");s=s.replace("from r35_package_selection import output_root,PROFILE","from r35_package_selection import output_root,PROFILE\nsys.path.insert(0,str(FROZEN/'runtime-wrapper'))\nfrom cleanup_evidence import failure_status")
s=s.replace("if p.returncode!=0:raise ValueError('original_child_nonzero_End_required_no_image')","if p.returncode!=0:\n   result['cleanup']=failure_status(run_dir,call_id)\n   raise ValueError('original_child_nonzero_End_required_no_image')")
s=s.replace("put(out/'invocation.json',","env={**env,'FX3_RETURN_CALL_ID':call_id}\n put(out/'invocation.json',")
(O/n).write_text(s)
source=json.loads((S/'SOURCE-FREEZE.json').read_text());source['runtime-wrapper/cleanup_evidence.py']='';source={n:sha(O/n) for n in source};(O/'SOURCE-FREEZE.json').write_text(json.dumps(source,indent=2)+'\n')
diffs=[];lineage={}
for n in source:
 if n=='CORE-SOURCE-FREEZE.json':continue
 old=(S/n).read_bytes() if (S/n).exists() else b'';new=(O/n).read_bytes();lineage[n]={'before':hashlib.sha256(old).hexdigest() if old else None,'after':sha(O/n),'changed':old!=new}
 if old!=new:diffs.extend(difflib.unified_diff(old.decode().splitlines(True),new.decode().splitlines(True),fromfile='r37/'+n if old else '/dev/null',tofile='r39/'+n))
(O/'r37-to-r39.diff').write_text(''.join(diffs));(O/'SOURCE-LINEAGE.json').write_text(json.dumps(lineage,indent=2)+'\n');print('SOURCE',len(source),sha(O/'SOURCE-FREEZE.json'),'CORE',len(core),sha(O/'CORE-SOURCE-FREEZE.json'))
