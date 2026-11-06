#!/usr/bin/env python3

import plistlib, subprocess
assert plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
from pathlib import Path
import subprocess,json,hashlib
HERE=Path(__file__).resolve().parent
# Exact argv already recorded during audit; accepts only llvm-objdump read-only argv.
def main():
 receipt=json.loads((HERE/'DISASSEMBLY-RECEIPT.json').read_text());out=[]
 for r in receipt:
  a=r['argv'];assert a[:2]==['/usr/bin/xcrun','llvm-objdump'];assert Path(r['output']).name==r['output']
  v=subprocess.run(a,capture_output=True);p=HERE/r['output'];p.write_bytes(v.stdout);p.with_suffix('.stderr').write_bytes(v.stderr);assert v.returncode==0
  out.append(dict(argv=a,exit=v.returncode,output=r['output'],sha256=hashlib.sha256(v.stdout).hexdigest()))
 (HERE/'DISASSEMBLY-RECEIPT.json').write_text(json.dumps(out,indent=2)+'\n');print('disassembled',len(out),'read-only ranges; guest code not executed')
if __name__=='__main__':main()
