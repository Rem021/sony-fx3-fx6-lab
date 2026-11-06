#!/usr/bin/env python3
"""Read-only recheck of this task's two deliveries and actually used technical pins."""
from pathlib import Path
import ast,hashlib,json
P=Path(__file__).resolve().parent;R=P.parent/'r42-command-timing-runner'
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
 counts={}
 for root in (P,R):
  manifest=root/'SHA256SUMS';rows=[line.split('  ',1) for line in manifest.read_text().splitlines()]
  for h,n in rows:
   p=root/n;assert p.is_relative_to(root) and '..' not in p.parts and p.is_file() and not p.is_symlink() and sha(p)==h,(n,'delivery mismatch')
  counts[root.name]=dict(files=len(rows),manifest_sha256=sha(manifest))
 inputs=json.loads((P/'INPUTS-AFTER.json').read_text())
 for n,x in inputs['files'].items():assert sha(Path(n))==x['sha256'],('input drift',n)
 for name in ('SOURCE-FREEZE.json','CORE-SOURCE-FREEZE.json'):
  for n,h in json.loads((R/name).read_text()).items():assert sha(R/n)==h
 c=json.loads((P/'candidate.json').read_text());diff=json.loads((P/'ARCHIVE-DIFF.json').read_text())
 assert sha(P/'guest.cpio')==c['initrd']['sha256']==diff['output_sha256'] and (P/'guest.cpio').stat().st_size==453213884
 x=c['r42_command_entry_timing_contract'];body=Path(x['body']['path']).read_bytes()
 with (P/'guest.cpio').open('rb') as f:f.seek(x['payload_offset']);slot=f.read(x['slot_bytes'])
 assert slot==body+bytes(x['zero_tail_bytes']) and hashlib.sha256(slot).hexdigest()==x['padded_slot_sha256']
 tree=ast.parse((R/'r35_package_selection.py').read_text());values={t.id:n.value.value for n in tree.body if isinstance(n,ast.Assign) and isinstance(n.value,ast.Constant) for t in n.targets if isinstance(t,ast.Name)}
 assert values['CANDIDATE_SHA']==sha(P/'candidate.json') and values['CPIO_SHA']==sha(P/'guest.cpio') and values['PROFILE']=='r41-entry-timing-r42' and values['LABEL']=='v41timing-n64-r42'
 assert json.loads((R/'HOST-CHECKS.json').read_text())['passed'] and json.loads((R/'EQUIVALENCE.json').read_text())['passed']
 print(json.dumps(dict(passed=True,deliveries=counts,technical_pin_count=len(inputs['files']),external_original_pin_count=inputs['external_original_pin_count'],no_execution='file reads only; no runner/helper imports, no process/socket/target operation')))
if __name__=='__main__':main()
