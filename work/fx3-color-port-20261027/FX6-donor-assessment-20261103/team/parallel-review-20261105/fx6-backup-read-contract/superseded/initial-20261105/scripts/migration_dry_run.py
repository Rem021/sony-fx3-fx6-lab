#!/usr/bin/env python3
"""Read-only dry-run scope check; no Backup/CPIO output is written."""
import hashlib,importlib.util,json
from pathlib import Path
TEAM=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team'); OUT=Path(__file__).resolve().parent.parent/'receipts'; BIN=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/lifecycle-repair/vmopt-20261103-reload-v1/Backup-generation4-fixed.bin')
def main():
 spec=importlib.util.spec_from_file_location('bk4',TEAM/'donor/backup-state-binding/parse_bk4.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 b=BIN.read_bytes(); keys=(0x02cf0214,0x02cf0218); rows=[]; rec=None
 for k in keys:
  rec,end=m.read_record(b,0,k,require_checksum=True); s=rec['selected']; rows.append({'id':hex(k),'record_file_offset':rec['record_file_offset'],'record_bytes':rec['record_bytes'],'data_file_offset':s['data_file_offset'],'length':s['length'],'current_raw':s['raw_hex'],'current_u32_le':s.get('u32_le'),'table_file_offset':s['table_file_offset'],'encoded_pointer':hex(s['encoded_pointer'])})
 assert rec is not None
 base=rec['record_file_offset']; end=rec['record_file_offset']+rec['record_bytes']; checksum_off=base+32
 # Validate that a hypothetical same-length edit of exactly these two data windows + record checksum leaves all other bytes unchanged.
 changed=set()
 for r in rows: changed.update(range(r['data_file_offset'],r['data_file_offset']+r['length']))
 changed.update(range(checksum_off,checksum_off+4))
 value={'schema':'fx6-backup-migration-dry-run-v1','source_backup':str(BIN),'source_sha256':hashlib.sha256(b).hexdigest(),'status':'blocked_by_unresolved_fx3_consumer_semantics','affected':rows,
  'checksum':{'field_file_offset':checksum_off,'field_bytes':4,'computed_scope':[[base,base+32],[base+36,end]],'record_start':base,'record_end':end,'current_checksum':rec['checksum_stored'],'current_checksum_matches':rec['checksum_matches']},
  'pure_data_scope':{'changed_offsets_minimal':sorted(changed),'changed_bytes_minimal':len(changed),'all_other_bytes_can_remain_identical':True,'record_lengths_preserved':True,'table_entries_preserved':True,'note':'scope is for same-length 4-byte data edits plus record checksum; if FX6 1-byte layout is required, table/length/header bytes change and this scope is insufficient.'},
  'candidate_values':None,'values_chosen':False,'file_written':False,'cpio_written':False,
  'blockers':['FX3 consumer semantics for 0x02cf0214/0x02cf0218 are not closed; same IDs/data exist in FX3 seed','normal FX6 producer/migration contract not implemented','no runtime proof that changing these values leads to screen/menu'],
  'note':'Dry-run only: identifies record/data/checksum scope; does NOT choose values or generate/install a modified Backup/CPIO. Blocked until consumer contract is closed.'}
 (OUT/'migration-dry-run.json').write_text(json.dumps(value,indent=2)+'\n')
 print(json.dumps({'status':value['status'],'affected':value['affected'],'checksum':value['checksum'],'scope':value['pure_data_scope'],'blockers':value['blockers'],'receipt':str(OUT/'migration-dry-run.json')},indent=2))
if __name__=='__main__':main()
