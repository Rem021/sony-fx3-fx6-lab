from pathlib import Path
import json,hashlib
from elftools.elf.elffile import ELFFile
p=Path(__file__).resolve().parent/'fx3-gpe-observe-v26-perf.so'
with p.open('rb') as f:
 e=ELFFile(f);assert e['e_machine']=='EM_AARCH64' and e.elfclass==64 and e.little_endian
 dynamic=e.get_section_by_name('.dynamic');tags=list(dynamic.iter_tags())
 needed=[t.needed for t in tags if t.entry.d_tag=='DT_NEEDED'];soname=[t.soname for t in tags if t.entry.d_tag=='DT_SONAME']
 assert soname==['fx3-gpe-observe-v26-perf.so']
 assert set(needed)<={'libc.so.6','libdl.so.2','libpthread.so.0','ld-linux-aarch64.so.1'}
 names={s.name for s in e.get_section_by_name('.dynsym').iter_symbols()}
 assert {'gpe_submit','gpe_plan_blit','fx3_gpe_frame_target_acquire','fx3_gpe_snapshot_trylock','fx3_gpe_callback_cache_invalidate26'}<=names
 result={'machine':e['e_machine'],'bits':e.elfclass,'little_endian':e.little_endian,'needed':needed,'soname':soname,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'existing_guard_exports_present':True}
 (p.parent/'build/elf-verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
