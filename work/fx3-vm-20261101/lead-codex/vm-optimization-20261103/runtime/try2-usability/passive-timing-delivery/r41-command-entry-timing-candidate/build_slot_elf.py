"""r36-verified linker strip-debug method only; no archive parsing/writing or VM."""
from pathlib import Path
import hashlib,json,os,struct,subprocess
from elf_review import ELF
O=Path(__file__).resolve().parent;ref=O.parent/'r36-fixed-slot-package/package_r36.py';B=json.loads((O/'BINDING.json').read_text());source_pin={'path':str(ref),'sha256':hashlib.sha256(ref.read_bytes()).hexdigest(),'bytes':ref.stat().st_size,'scope':'first observed reference pin after reading source; not claimed pre-read snapshot'}
commands=json.loads((O/'BUILD-COMMANDS.json').read_text());original=next(r['argv'] for r in commands if r['name']=='cross-candidate');argv=list(original);out=O/'build/gpe-r41-fixed-slot.so';assert not out.exists();argv[argv.index('-o')+1]=str(out);argv.insert(2,'-Wl,--strip-debug')
env={**os.environ,'ZIG_GLOBAL_CACHE_DIR':str(O/'build/zig-global'),'ZIG_LOCAL_CACHE_DIR':str(O/'build/zig-local'),'XDG_CACHE_HOME':str(O/'build/zig-global'),'TMPDIR':str(O/'build/tmp'),'PYTHONDONTWRITEBYTECODE':'1'}
p=subprocess.run(argv,capture_output=True,env=env,timeout=180);(O/'receipts/link-strip.stdout').write_bytes(p.stdout);(O/'receipts/link-strip.stderr').write_bytes(p.stderr);assert p.returncode==0,p.stderr
raw=ELF(O/'build/gpe-r41-candidate.so');slot=ELF(out)
# Reproduce the r36 proof boundary without importing its packaging entrypoint.
def headers(e):
 d=e.data;off=struct.unpack_from('<Q',d,32)[0];size,n=struct.unpack_from('<HH',d,54);return [struct.unpack_from('<IIQQQQQQ',d,off+i*size) for i in range(n)]
a=headers(raw);b=headers(slot);assert a==b
allowed=set(range(40,48))|set(range(60,64));segments=[]
for index,ph in enumerate(a):
 off,size=ph[2],ph[5];x=raw.data[off:off+size];y=slot.data[off:off+size];assert len(x)==len(y)
 diffs=[off+i for i,(left,right) in enumerate(zip(x,y)) if left!=right];assert set(diffs)<=allowed,(index,diffs)
 segments.append({'index':index,'type':ph[0],'offset':off,'filesz':size,'changed_offsets':diffs})
alloc=[]
for name,s in raw.sections.items():
 if not s['flags']&2:continue
 t=slot.sections[name];assert all(s[k]==t[k] for k in ('type','flags','address','offset','size','entry_size','data'))
 for link in ('link',):
  def linked(e,index):return e.raw[index][0] and next(n for n,x in e.sections.items() if x['offset']==e.raw[index][4] and x['size']==e.raw[index][5]) if index else None
  assert linked(raw,s['link'])==linked(slot,t['link'])
 alloc.append(name)
assert raw.needed==slot.needed and raw.soname==slot.soname and raw.sections['.dynamic']['data']==slot.sections['.dynamic']['data']
def dyn(e):return {n:(v['info'],v['address'],v['size'],v['section']) for n,entries in e.symbols.items() for v in entries if v['table']==11}
assert dyn(raw)==dyn(slot)
header_diffs=[i for i,(x,y) in enumerate(zip(raw.data[:64],slot.data[:64])) if x!=y];assert set(header_diffs)<=allowed
assert len(slot.data)<=B['actual_member']['size']
value={'passed':True,'reference':source_pin,'command':argv,'original_unstripped_command':original,'only_additional_changes':['insert -Wl,--strip-debug','output path'],'exit':p.returncode,'raw':raw.describe(),'fixed_slot_body':slot.describe(),'all_PHDR_equal':True,'all_ALLOC_bytes_layout_link_identity_equal':alloc,'all_program_segments_equal_except_exact_section_table_metadata':segments,'ELF_header_changed_offsets':header_diffs,'permitted_header_fields':['e_shoff','e_shnum','e_shstrndx'],'dynamic_dependencies_and_exports_identical':True,'slot_capacity_bytes':B['actual_member']['size'],'body_bytes':len(slot.data),'available_tail_bytes':B['actual_member']['size']-len(slot.data),'CPIO_padded_or_modified':False,'guest_loaded_or_executed':False,'package_or_runtime_admission':False,'old_objcopy_failure_preserved':'receipts/strip.stderr and build/strip-attempt.failed-empty-output'}
(O/'SLOT-ELF-REVIEW.json').write_text(json.dumps(value,indent=2)+'\n');print('link-time strip-debug PASS',len(raw.data),'->',len(slot.data),'slot',B['actual_member']['size'],'all ALLOC/PHDR equivalent')
