#!/usr/bin/env python3
"""Derive only the 43 frozen r39 runtime members; never copy historical fixtures."""
from pathlib import Path
import datetime,difflib,hashlib,json,plistlib,subprocess
O=Path(__file__).resolve().parent;D=O.parent;S=D/'r39-cleanup-evidence-candidate';P=D/'r42-command-timing-package'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def js(n,x):(O/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def replace(s,a,b):
 assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def main():
 assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
 source=json.loads((S/'SOURCE-FREEZE.json').read_text());core=json.loads((S/'CORE-SOURCE-FREEZE.json').read_text())
 assert sha(S/'SOURCE-FREEZE.json')=='3f4d9894d2bfdd1bf15f2c01132006c78f8331220f8e8da1bcee4adcbd37ff43'
 assert sha(S/'CORE-SOURCE-FREEZE.json')=='642149dac737315d19dc6910804538eec6df79a43261527c06fcaf23d374bd50'
 for n,h in source.items():
  assert sha(S/n)==h
  if n=='CORE-SOURCE-FREEZE.json':continue
  t=O/n;t.parent.mkdir(exist_ok=True)
  with t.open('xb') as f:f.write((S/n).read_bytes())
 n='r35_package_selection.py';s=(O/n).read_text()
 s=replace(s,'Fixed r36 selector/identity checks only.','Fixed r42 command-entry-timing selector/identity checks only.')
 s=replace(s,str(S),str(O));s=replace(s,"PACKAGE=DEL/'r36-fixed-slot-package'","PACKAGE=DEL/'r42-command-timing-package'")
 s=replace(s,"CANDIDATE_SHA='0bf214178ab8e60d1ac7755e1d1b2fcc0d2c325ff8473abd50402f09ab81fab4'","CANDIDATE_SHA='"+sha(P/'candidate.json')+"'")
 s=replace(s,"CPIO_SHA='49c1e110475fa15b692a3bf79fdf15189b82929cc7d643e27cd5f2d383d77fff'","CPIO_SHA='"+sha(P/'guest.cpio')+"'")
 s=replace(s,"PROFILE='r35-diagnostic-r36-n64-r39'","PROFILE='r41-entry-timing-r42'")
 s=replace(s,"LABEL='v35diag-n64-r36-r39'","LABEL='v41timing-n64-r42'")
 for a,b in [('r39 regular exact path required','r42 regular exact path required'),('r39 exclusive run-inputs boundary required','r42 exclusive run-inputs boundary required'),('r39 frozen input identity changed','r42 frozen input identity changed'),('r36 manifest identity changed','r42 manifest identity changed'),('r36 CPIO path/size/hash changed','r42 CPIO path/size/hash changed')]:s=replace(s,a,b)
 pins={str(p.relative_to(D)):sha(p) for p in [S/'SHA256SUMS',S/'SOURCE-FREEZE.json',S/'CORE-SOURCE-FREEZE.json',D/'r41-command-entry-timing-candidate/SHA256SUMS',D/'r41-command-entry-timing-candidate/SOURCE-FREEZE.json',P/'ARCHIVE-DIFF.json',P/'source-index.json']}
 s=replace(s,'def sha(p):','PINS.update('+repr(pins)+')\ndef sha(p):')
 (O/n).write_text(s)
 # Update misleading selector help only; all parse/selection/control-flow expressions stay original.
 n='run_trial_r24_review_snapshot.py';s=(O/n).read_text();s=replace(s,'仅另行授权时选择固定r36包；须snapshot-tail/N64','仅另行授权时选择固定r42 command入口计时包；须snapshot-tail/N64');(O/n).write_text(s)
 n='runtime-wrapper/preflight.py';s=(O/n).read_text();s=replace(s,"group('r39_local_core'","group('r42_local_core'");s=replace(s,"run_name='r39_import_only'","run_name='r42_import_only'");s=replace(s,"run('r39-import-only'","run('r42-import-only'");(O/n).write_text(s)
 js('CORE-SOURCE-FREEZE.json',{n:sha(O/n) for n in core})
 n='return-tools/return_adapter.py';s=(O/n).read_text();s=replace(s,"CORE_FREEZE_SHA='642149dac737315d19dc6910804538eec6df79a43261527c06fcaf23d374bd50'","CORE_FREEZE_SHA='"+sha(O/'CORE-SOURCE-FREEZE.json')+"'");(O/n).write_text(s)
 js('SOURCE-FREEZE.json',{n:sha(O/n) for n in source})
 lineage={};diff=[]
 for n in source:
  a=(S/n).read_bytes();b=(O/n).read_bytes();lineage[n]=dict(original_sha256=sha(S/n),candidate_sha256=sha(O/n),byte_equal=a==b)
  if a!=b:diff+=difflib.unified_diff(a.decode().splitlines(True),b.decode().splitlines(True),fromfile='r39/'+n,tofile='r42/'+n)
 (O/'r39-to-r42.diff').write_text(''.join(diff));js('SOURCE-LINEAGE.json',lineage)
 print(json.dumps({'source_count':len(source),'core_count':len(core),'source_sha256':sha(O/'SOURCE-FREEZE.json'),'core_sha256':sha(O/'CORE-SOURCE-FREEZE.json'),'changed':[n for n,r in lineage.items() if not r['byte_equal']]}))
if __name__=='__main__':main()
