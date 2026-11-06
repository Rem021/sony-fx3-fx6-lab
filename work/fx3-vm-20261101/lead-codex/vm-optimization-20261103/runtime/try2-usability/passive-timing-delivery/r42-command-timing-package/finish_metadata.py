#!/usr/bin/env python3
"""Pure CPIO/ELF metadata provenance; no target load or archive modification."""
from pathlib import Path,PurePosixPath
import hashlib,json
O=Path(__file__).resolve().parent;D=O.parent
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
 rows=json.loads((O/'source-index.json').read_text());by={r['name']:r for r in rows}
 compare={r['name']:r for r in json.loads((O/'member-comparison.json').read_text())}
 elf=json.loads((O/'ELF-AUDIT.json').read_text());deps=[]
 with (O/'guest.cpio').open('rb') as f:
  for name in elf['dynamic']['needed']:
   path='lib/'+name;chain=[]
   for _ in range(8):
    r=by[path];assert compare[path]['equal'];chain.append({**r,'body_sha256':compare[path]['output_sha256']})
    if r['mode']&0o170000!=0o120000:break
    f.seek(r['payload_offset']);target=f.read(r['size']).decode();assert '/' not in target and target not in ('.','..')
    chain[-1]['symlink_target']=target;path=str(PurePosixPath(path).parent/target)
   else:raise AssertionError('unresolved dependency chain')
   assert chain[-1]['mode']&0o170000==0o100000
   deps.append(dict(needed=name,archive_chain=chain,all_bytes_unchanged_from_r36=True))
 c=json.loads((O/'candidate.json').read_text());x=c['r42_command_entry_timing_contract']
 index=dict(schema='r42-package-source-binding-v1',base_candidate=x['base_candidate'],base_archive=dict(path=str(D/'r36-fixed-slot-package/guest.cpio'),sha256=x['base_initrd_sha256']),output_candidate=dict(path=str(O/'candidate.json'),sha256=sha(O/'candidate.json')),output_archive=c['initrd'],GPE=dict(member=x['member'],original_slot_sha256=x['old_slot_sha256'],new_ELF_body=x['body'],slot_bytes=x['slot_bytes'],padded_slot_sha256=x['padded_slot_sha256'],zero_tail_bytes=x['zero_tail_bytes'],payload_offset=x['payload_offset'],source_files=x['source_files'],source_freeze=x['source_freeze'],backend=x['backend']),archive_index=dict(path=str(O/'source-index.json'),sha256=sha(O/'source-index.json')),dependencies=deps,DTB=c['dtb'],ELF_dynamic=elf['dynamic'],prior_acceptance={'r41':str(D/'r41-coordinator-final-review.json'),'r39':str(D/'r39-coordinator-final-review.json')},no_compilation=True,no_target_execution=True)
 (O/'SOURCE-BINDING.json').write_text(json.dumps(index,indent=2)+'\n')
 print(json.dumps({'dependency_chains':len(deps),'source_binding':'SOURCE-BINDING.json'}))
if __name__=='__main__':main()
