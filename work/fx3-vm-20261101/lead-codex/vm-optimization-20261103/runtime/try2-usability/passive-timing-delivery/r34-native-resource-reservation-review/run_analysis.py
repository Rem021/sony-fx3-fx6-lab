#!/usr/bin/env python3
"""Run only this review's read-only parsers/disassemblers; no guest/helper execution."""
from pathlib import Path
import json,hashlib,subprocess,plistlib,datetime,ast
assert plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
HERE=Path(__file__).resolve().parent;ROOT=next(p for p in HERE.parents if p.name=='Mac')
def main():
 for p in HERE.glob('*.py'):ast.parse(p.read_text())
 log=HERE/'receipts';log.mkdir(exist_ok=True)
 venv=ROOT/'work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python'
 tasks=[('extract_inputs.py','python3'),('analyze_native.py','python3'),('reproduce_disassembly.py','python3'),('select_gpl.py','python3'),('decode_kernel.py',str(venv)),('decode_admission.py','python3'),('verify_inputs.py','python3')];receipts=[]
 for name,py in tasks:
  args=[py,'-B',str(HERE/name)];v=subprocess.run(args,cwd=HERE,capture_output=True)
  out=log/(name+'.stdout');err=log/(name+'.stderr');out.write_bytes(v.stdout);err.write_bytes(v.stderr)
  receipts.append(dict(argv=args,source_sha256=hashlib.sha256((HERE/name).read_bytes()).hexdigest(),exit=v.returncode,stdout=str(out.relative_to(HERE)),stderr=str(err.relative_to(HERE)),stdout_sha256=hashlib.sha256(v.stdout).hexdigest(),stderr_sha256=hashlib.sha256(v.stderr).hexdigest()))
  print(name,'exit',v.returncode,'stdout_bytes',len(v.stdout),'stderr_bytes',len(v.stderr),flush=True)
  if v.returncode:break
 (HERE/'REPRODUCTION.json').write_text(json.dumps(dict(captured_UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope='Only offline bytes/ELF/GPL parsers and llvm-objdump; no VM, helper execution/compilation, browser, service, QMP or devices',commands=receipts),indent=2)+'\n')
 assert len(receipts)==len(tasks) and all(x['exit']==0 for x in receipts)
if __name__=='__main__':main()
