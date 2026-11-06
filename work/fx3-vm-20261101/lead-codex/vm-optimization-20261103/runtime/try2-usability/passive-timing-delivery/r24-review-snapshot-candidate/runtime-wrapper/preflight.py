"""Pinned all-145/fixed-platform and helper parser audit; no fixture/browser/VM."""
from common import *
import ast,plistlib,importlib.util,re

def verify(name):
 disk=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']));assert disk['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
 root=Path('/Volumes/KAFU2T/AI/Projects/Mac');groups={}
 def group(label,pairs):
  groups[label]=[{'path':str(p),'expected':h,'actual':sha(p),'match':sha(p)==h} for p,h in pairs];assert all(r['match'] for r in groups[label])
 group('pins',[(FROZEN/'SHA256SUMS','dcbbb11fc1942a480b8624e53d769e29b93fec3c884401811cc0599fea3b02ef'),(FROZEN/'SOURCE-FREEZE.json','31ee6b1d00fecfc5ac53e874b144230d2430208277c295d74c4a804fbe1135ec')])
 group('source40',[(FROZEN/f,h) for f,h in json.loads((FROZEN/'SOURCE-FREEZE.json').read_text()).items()])
 group('delivery145',[(FROZEN/f,h) for h,f in (line.split('  ',1) for line in (FROZEN/'SHA256SUMS').read_text().splitlines())])
 group('fixed14',[(root/x['path'],x['expected_sha256']) for x in json.loads((FROZEN/'FIXED-INPUT-14.json').read_text())['files']])
 group('qemu',[(root/'work/fx3-vm-20261101/menu-repair-01/runtime/qemu-display-build/bin/qemu-gpio5-bf4d46481998b8fb','bf4d46481998b8fb0644da3e17a333d5fc8a7b6aeb0035f1b4e03aa25c98c70d')])
 write(name,{'groups':groups,'counts':{k:len(v) for k,v in groups.items()},'volume_uuid':disk['VolumeUUID'],'candidate_directory_files':sorted(p.name for p in FROZEN.iterdir()),**stamp()})
 return groups

def main():
 verify('INPUTS-BEFORE.json')
 # r24 runner checkpoints/preflight output go into FX3_NAV_RUN_DIR; original runtime has no output exception.
 write('OUTPUT-BOUNDARY-BEFORE.json',{'original_runtime_writes_allowed':[],'candidate_run_outputs':['preflight-*.json','STATE-v25-r3.json','STATE-v24.json.tmp']})
 for p in SOURCE.glob('*.py'):ast.parse(p.read_text())
 for f in ('recovery_tools.py','deadline_cli.py','review_snapshot_cli.py'):
  run('parser-'+f,['python3','-B',str(CANDIDATE_OPS/f),'--help'])
 run('parser-planned-navigation',['python3','-B',str(CANDIDATE_OPS/'planned_navigation_click.py'),'--help'])
 write('PREFLIGHT-RESULT.json',{'passed':True,'scope':'pinned input and CLI parser preparation only; no browser or guest',**stamp()})
 print(json.dumps({'passed':True}))
if __name__=='__main__':main()
