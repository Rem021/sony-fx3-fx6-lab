#!/usr/bin/env python3
"""Only bounded host preparation, AST construction and file audits; never launch."""
from pathlib import Path
import json,subprocess,sys,hashlib,plistlib
O=Path(__file__).resolve().parent
assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
steps=[('help-source-audit',[sys.executable,'-B',str(O/'tests/check_help_sources.py')]),('actual-prepare-preflight-import',[sys.executable,'-B',str(O/'tests/check_binding.py')]),('selector-and-argv',[sys.executable,'-B',str(O/'tests/test_selection.py')]),('source-equivalence',[sys.executable,'-B',str(O/'tests/check_equivalence.py')]),('actual-negative-boundaries',[sys.executable,'-B',str(O/'tests/test_boundaries.py')]),('original-CPIO-admission',[sys.executable,'-B',str(O/'tests/audit_original_cpio.py')]),('Node-import-binding',['node',str(O/'tests/check_node.mjs')])];receipt=[]
for name,args in steps:
 p=subprocess.run(args,capture_output=True)
 for k,b in [('stdout',p.stdout),('stderr',p.stderr)]:(O/'receipts'/('final-'+name+'.'+k)).write_bytes(b)
 receipt.append({'case':name,'argv':args,'exit':p.returncode,'source_sha256':hashlib.sha256(Path(args[-1]).read_bytes()).hexdigest(),'stdout':'receipts/final-'+name+'.stdout','stderr':'receipts/final-'+name+'.stderr'});(O/'OFFLINE-CHECKS.json').write_text(json.dumps(receipt,indent=2)+'\n')
 if p.returncode:print('FAIL',name,'see stderr receipt',flush=True);raise SystemExit(p.returncode)
 print('PASS',name,flush=True)
