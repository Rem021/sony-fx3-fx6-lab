"""Pure host source, parser and actual exception guard checks; no fixture/browser/VM."""
from common import *
import ast,plistlib,importlib.util,re

def verify(name):
 disk=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']));assert disk['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
 root=Path('/Volumes/KAFU2T/AI/Projects/Mac');groups={}
 def group(label,pairs):
  groups[label]=[{'path':str(p),'expected':h,'actual':sha(p),'match':sha(p)==h} for p,h in pairs];assert all(r['match'] for r in groups[label])
 group('pins',[(FROZEN/'SHA256SUMS','dcbbb11fc1942a480b8624e53d769e29b93fec3c884401811cc0599fea3b02ef'),(FROZEN/'SOURCE-FREEZE.json','31ee6b1d00fecfc5ac53e874b144230d2430208277c295d74c4a804fbe1135ec')])
 group('source40',[(FROZEN/f,h) for f,h in json.loads((FROZEN/'SOURCE-FREEZE.json').read_text()).items()])
 group('delivery145',[(FROZEN/f,h) for f,h in json.loads((FROZEN/'DELIVERY-MANIFEST.json').read_text())['files'].items()])
 group('fixed14',[(root/x['path'],x['expected_sha256']) for x in json.loads((FROZEN/'FIXED-INPUT-14.json').read_text())['files']])
 group('qemu',[(root/'work/fx3-vm-20261101/menu-repair-01/runtime/qemu-display-build/bin/qemu-gpio5-bf4d46481998b8fb','bf4d46481998b8fb0644da3e17a333d5fc8a7b6aeb0035f1b4e03aa25c98c70d')])
 write(name,{'groups':groups,'counts':{k:len(v) for k,v in groups.items()},'volume_uuid':disk['VolumeUUID'],'candidate_directory_files':sorted(p.name for p in FROZEN.iterdir()),**stamp()})
 return groups

def main():
 verify('INPUTS-BEFORE.json')
 writes=[];out=HERE/'authorized-outputs-before';out.mkdir()
 for f in ('preflight-aaf006610b0d2b6e.json','STATE-v24.json.tmp','STATE-v25-r3.json'):
  p=FROZEN/f;assert not p.is_symlink();assert not any(f==line.split(maxsplit=1)[1] for line in (FROZEN/'SHA256SUMS').read_text().splitlines());row={'path':str(p),'exists':p.exists(),'symlink':False,'in_frozen_sums':False}
  if p.exists():
   import shutil
   shutil.copyfile(p,out/f);row.update(sha256=sha(p),bytes=p.stat().st_size,copied_to=str(out/f))
  writes.append(row)
 write('OUTPUT-BOUNDARY-BEFORE.json',{'coordinator_message':'msg_82796ff62714','allowed_outputs':writes})
 for p in HERE.glob('*.py'):ast.parse(p.read_text())
 from later_capture import current_guard
 code=current_guard({'url':'http://127.0.0.1:1/','launch_id':'host-only','nonce':'host-only','step':2,'attempt_id':'host-only'})
 p=subprocess.run(['node','--check'],input=code,text=True,capture_output=True);assert p.returncode==0,p.stderr
 for f in ('capture_review.js','capture_after.js'):
  p=subprocess.run(['node','--check'],input=(HERE/f).read_text()+'({})',text=True,capture_output=True);assert p.returncode==0,p.stderr
 for f in ('operator_click.py','recovery_tools.py','explicit_confirm_cli.py','bounded_capture_cli.py','deadline_cli.py'):
  run('parser-'+f,['python3','-B',str(OPS/f),'--help'])
 run('actual-cli-host-tests',['python3','-B',str(HERE/'host_cli_checks.py')],timeout=30)
 assert read('HOST-CLI-RESULT.json')['passed']
 write('LOCAL-SOURCE-FREEZE.json',{p.name:sha(p) for p in HERE.iterdir() if p.suffix in ('.py','.js')})
 write('PREFLIGHT-RESULT.json',{'passed':True,'scope':'host parameters, source identities, actual __main__ CLI dispatch, cleanup branches; no timed fixture','browser_calls':0,'guest_starts':0,**stamp()});print(json.dumps({'passed':True}))
if __name__=='__main__':main()
