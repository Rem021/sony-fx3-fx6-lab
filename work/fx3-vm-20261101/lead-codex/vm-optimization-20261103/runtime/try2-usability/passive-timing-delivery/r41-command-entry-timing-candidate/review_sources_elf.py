"""File-only inverse source delta and actual ELF/stack/storage/dependency evidence."""
from pathlib import Path
import hashlib,json,os,re,struct,subprocess
from elf_review import ELF
O=Path(__file__).resolve().parent;B=json.loads((O/'BINDING.json').read_text());G=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-claude/impl/gpe-perf');H=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/runtime/helpers')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
s=(O/'src/fx3-gpe-observe-v26-perf.c').read_text();line=' int entry_errno41=*__errno_location();U entry_ns41=gpe102_now();*__errno_location()=entry_errno41;\n';assert s.count(line)==1;s=s.replace(line,'');assert s.count(',entry_ns41)')==2;s=s.replace(',entry_ns41)',')');assert s==(G/'fx3-gpe-observe-v26-perf.c').read_text()
s=(O/'src/fx3-complete104-observe-v1.h').read_text();s=s.replace('int result,U entry_ns41)','int result)').replace(' unchanged=1 entry_ns=%lu\\n',' unchanged=1\\n').replace('result,saved,entry_ns41)','result,saved)');assert s==(H/'fx3-complete104-observe-v1.h').read_text()
actual,base,cand=(ELF(p) for p in (Path(B['actual_helper']),O/'build/gpe-r41-baseline.so',O/'build/gpe-r41-candidate.so'))
alloc=[n for n,s in actual.sections.items() if s['flags']&2]
assert all(actual.sections[n]['data']==base.sections[n]['data'] and actual.sections[n]['address']==base.sections[n]['address'] and actual.sections[n]['size']==base.sections[n]['size'] for n in alloc)
assert actual.needed==base.needed==cand.needed and actual.soname==base.soname==cand.soname
for n in ('.bss','.tbss','.data'):assert base.sections[n]['size']==cand.sections[n]['size'],n
# Data/TLS/global identities, not just aggregate byte counts.
def data_symbols(e):return {n:(x['size'],x['info']) for n,entries in e.symbols.items() for x in entries if (x['info']&15) in (1,6) and x['section']}
assert data_symbols(base)==data_symbols(cand)
def dyn(e):return {n:(x['info'],bool(x['section'])) for n,entries in e.symbols.items() for x in entries if x['table']==11}
assert dyn(base)==dyn(cand)
# Program segment layout must match actual to unmodified rebuild as well.
def phdr(e):
 d=e.data;off=struct.unpack_from('<Q',d,32)[0];size,n=struct.unpack_from('<HH',d,54);return [struct.unpack_from('<IIQQQQQQ',d,off+i*size) for i in range(n)]
assert phdr(actual)==phdr(base)
objdump=Path('/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/objdump')
for name in ('baseline','candidate'):
 argv=[str(objdump),'--disassemble','--no-show-raw-insn','--disassemble-symbols=command',str(O/'build'/('gpe-r41-'+name+'.so'))];p=subprocess.run(argv,capture_output=True);assert not p.returncode,p.stderr;(O/'build'/('command-'+name+'.S')).write_bytes(p.stdout)
a=(O/'build/command-baseline.S').read_text();b=(O/'build/command-candidate.S').read_text();pre=b[:b.index('<pread@plt>')];assert pre.count('<clock_gettime@plt>')==1 and '__errno_location@plt' in pre
assert re.search(r'str\s+w19, \[x0\]',pre) and re.search(r'str\s+x8, \[sp, #0xf0\]',pre)
def frame(s):
 pre=s[s.index('<command>:'):];return re.findall(r'(?:stp\s+x29, x30, \[sp, #-(0x[0-9a-f]+)\]!|sub\s+sp, sp, #(0x[0-9a-f]+)(?:, lsl #(\d+))?)',pre[:1200])
result={'passed':True,'source_inverse_exact_to_original':True,'only_original_command_function_and_existing_return_helper_changed':True,'no_new_global_TLS_storage':True,'baseline_raw_sha256_matches_actual':sha(Path(B['actual_helper']))==sha(O/'build/gpe-r41-baseline.so'),'actual_to_rebuild_ALLOC_sections_identical':alloc,'actual_to_rebuild_program_headers_identical':True,'baseline_raw_delta_explanation':'Only non-ALLOC debug_info/debug_str/debug_line and static symtab differ; compilation directory is visible in debug_str. Raw byte identity is not claimed. A cwd-only rebuild reused cached object debug directory and did not restore raw hash.','old_helper':actual.describe(),'rebuilt_baseline':base.describe(),'candidate':cand.describe(),'unchanged_data_TLS_symbols':len(data_symbols(base)),'dynamic_symbol_identity_equal':True,'stack_preamble_baseline':frame(a),'stack_preamble_candidate':frame(b),'added_clock_before_first_pread_in_target_disassembly':1,'entry_held_on_stack_offset':'sp+0xf0 in this build','raw_slot_capacity':B['actual_member']['size'],'candidate_raw_bytes':len(cand.data),'raw_excess_bytes':len(cand.data)-B['actual_member']['size'],'slot_ready':False,'strip_attempt':{'tool':'accepted recipe zig objcopy --strip-debug','exit':1,'stderr':'error: unimplemented','fallback_attempted':False},'slot_gap':'candidate raw ELF exceeds unchanged slot by 720B; no fixed-slot artifact or CPIO produced; future separately reviewed strip/package step required'}
assert result['raw_excess_bytes']==720
(O/'SOURCE-ELF-REVIEW.json').write_text(json.dumps(result,indent=2)+'\n')
# Actual preprocessing dependency resolution, no linking/target execution.
recipe=B['original_recipe'];zig=recipe[0];incs=[]
for i,x in enumerate(recipe):
 if x=='-I':incs.extend(recipe[i:i+2])
env={**os.environ,'ZIG_LOCAL_CACHE_DIR':str(O/'build/zig-local'),'ZIG_GLOBAL_CACHE_DIR':str(O/'build/zig-global'),'TMPDIR':str(O/'build/tmp')};deps={};commands=[]
for label,path in [('candidate',O/'src/fx3-gpe-observe-v26-perf.c'),('backend',G/'fx3-gpe-backend-v9.c')]:
 argv=[zig,'cc','-target','aarch64-linux-gnu.2.25','-mcpu=generic','-I',str(O/'src'),*incs,'-M',str(path)];p=subprocess.run(argv,capture_output=True,env=env);(O/'receipts'/('deps-'+label+'.stdout')).write_bytes(p.stdout);(O/'receipts'/('deps-'+label+'.stderr')).write_bytes(p.stderr);assert not p.returncode,p.stderr;commands.append({'argv':argv,'exit':p.returncode})
 # Paths here contain no spaces; retain escaped make continuation only.
 text=p.stdout.decode().replace('\\\n',' ');paths=text.split(':',1)[1].split()
 for name in paths:
  q=Path(name)
  if not q.is_absolute():q=(O/q).resolve()
  assert q.is_file(),q
  deps[str(q)]={'sha256':sha(q),'bytes':q.stat().st_size,'local_candidate':q.is_relative_to(O)}
assert str(O/'src/fx3-complete104-observe-v1.h') in deps and str(H/'fx3-complete104-observe-v1.h') not in deps
extras={str(objdump):{'sha256':sha(objdump),'bytes':objdump.stat().st_size},str(Path('/usr/bin/clang').resolve()):{'sha256':sha(Path('/usr/bin/clang')),'bytes':Path('/usr/bin/clang').stat().st_size}}
extras.update({name:v for name,v in deps.items() if not v['local_candidate']})
(O/'DEPENDENCY-BINDING.json').write_text(json.dumps({'commands':commands,'resolved_compile_files':deps,'additional_observed_technical_inputs':extras,'scope':'compiler dependency resolution observed during review; original 33 input snapshot remains separate'},indent=2)+'\n');print('source inverse + 21 ALLOC + ABI/storage/stack review PASS; raw slot gap 720B remains; actual dependency files',len(deps))
