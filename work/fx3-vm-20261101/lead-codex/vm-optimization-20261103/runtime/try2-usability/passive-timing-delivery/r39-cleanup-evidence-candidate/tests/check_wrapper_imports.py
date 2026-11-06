"""Actual new wrapper/common/cleanup/operate/adapter imports only, no process/socket/write."""
from pathlib import Path
import json,os,subprocess,sys,hashlib
O=Path(__file__).resolve().parents[1];out=Path(json.loads((O/'PREPARE-PREFLIGHT.json').read_text())['run_dir'])
code='''import sys,runpy,json,hashlib
from pathlib import Path
r=Path(sys.argv[1]);sys.path.insert(0,str(r/'runtime-wrapper'))
def audit(event,args):
 if event in ('subprocess.Popen','socket.__new__','os.system','os.fork','os.posix_spawn','os.mkdir'):raise RuntimeError('forbidden import:'+event)
 if event=='open' and isinstance(args[0],(str,bytes)) and ((args[1] and any(c in args[1] for c in 'wax+')) or args[2]&0x603):raise RuntimeError('import write')
sys.addaudithook(audit)
import common,cleanup,operate,audit_after,cleanup_evidence
runpy.run_path(str(r/'return-tools/return_adapter.py'),run_name='r39_adapter_import_only')
mods={n:{'path':str(Path(m.__file__).resolve()),'sha256':hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest()} for n,m in sys.modules.items() if getattr(m,'__file__',None) and Path(m.__file__).is_file() and '/Volumes/KAFU2T/AI/Projects/Mac/' in str(m.__file__)}
for n in ('common','cleanup','operate','audit_after','cleanup_evidence'):assert Path(mods[n]['path']).parent==r/'runtime-wrapper'
print(json.dumps(mods))
'''
p=subprocess.run([sys.executable,'-B','-c',code,str(O)],env={**os.environ,'FX3_NAV_RUN_DIR':str(out),'PYTHONDONTWRITEBYTECODE':'1'},capture_output=True);(O/'receipts/wrapper-import.stdout').write_bytes(p.stdout);(O/'receipts/wrapper-import.stderr').write_bytes(p.stderr);assert p.returncode==0,p.stderr
mods=json.loads(p.stdout);allowed={str(O/n):h for n,h in json.loads((O/'SOURCE-FREEZE.json').read_text()).items()};frozen=O.parent/'v25-r21-recovery-integration';allowed.update({str(frozen/n):h for n,h in json.loads((frozen/'SOURCE-FREEZE.json').read_text()).items()})
for n,v in mods.items():assert allowed.get(v['path'])==v['sha256'],(n,v)
(O/'WRAPPER-IMPORT-BINDING.json').write_text(json.dumps({'passed':True,'mode':'actual imports only; all action mains not called','modules':mods,'run_dir':str(out)},indent=2)+'\n');print('actual new common/cleanup/operate/audit/adapter import bindings PASS')
