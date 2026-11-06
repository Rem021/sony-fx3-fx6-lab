#!/usr/bin/env python3
"""Two fixed-slot, offline-only packager. Does not import a runner or load target ELF."""
import argparse, copy, datetime, hashlib, importlib.util, json, os
from pathlib import Path
import re, stat, struct, subprocess, sys
sys.dont_write_bytecode=True
O=Path(__file__).absolute().parent
DEL=O.parent
R35=DEL/'r35-existing-log-observation-candidate'
BASE=DEL/'r16-fixed-slot-guests/guest-N64'
UUID='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
TOOL=DEL/'r15-fixed-layout-packaging/fixed_layout.py'
TOOL_SHA='b5b9bf75763b193575a007074e6701d1a1541ba9d3658ae32a164fc350eca8bc'
BASE_SHA='96666a719b1a4cf576e4d2d7ec461e10f5ce1143650450719e5273d75d970672'
CPIO_SHA='aaf006610b0d2b6ecf2148666b9810ece611770f25697fc5d2f09f0dadd14ba9'
DTB_SHA='5aa2beacb0b0e1f5b83f4589f9bba8b148cd73f87b6058e0f648e05c5347855b'
PINS={
 'ui':dict(member='simulation/fx3-ui-gate-v1.so',offset=451339648,size=58856,raw_size=72656,
           raw_sha='8fbad11e585a88ba55fc657785b6bc132bd12ee20ac3a31f23c603b1b1b322d1',
           body_sha='6673b9beaf8a2adfbc2c68dc7337df369e484bd58ede10edff3519dcf8d258df'),
 'osd':dict(member='simulation/fx3-osd-headless-v5.so',offset=452021916,size=109000,raw_size=119544,
            raw_sha='1a0761b8c73fb04502406686499ff01f3683bcc767ce1503fae3e6bbb996bf21',
            body_sha='67155b38fbbe23c3b6273c64ce8fc4676e59ad98da4a30a238508c26d9b5fba8')}
def sha(b):return hashlib.sha256(b).hexdigest()
assert sha(TOOL.read_bytes())==TOOL_SHA
spec=importlib.util.spec_from_file_location('r15_readonly',TOOL)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
req=m.require
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def outpath(p):
 p=m.safe_path(p)
 req(p.is_relative_to(O) and p!=O,'write outside authorized output')
 return p
def write(p,b):
 p=outpath(p);req(p.parent.is_dir(),'missing output parent')
 with p.open('xb') as f:f.write(b);f.flush();os.fsync(f.fileno())
def js(p,value):write(p,(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode())
def pin(path,expected):
 actual=m.sha_file(path);req(actual==expected,'pinned hash mismatch: '+str(path))
 return actual
def source_binaries():
 rows={}
 for tag,p in PINS.items():
  f=R35/'build'/('fx3-'+tag+'-r35.so')
  pin(f,p['raw_sha']);req(f.stat().st_size==p['raw_size'],'binary size drift')
  rows[tag]=dict(path=str(f),sha256=p['raw_sha'],bytes=p['raw_size'])
 return rows
def slots(rows):
 found={}
 for tag,p in PINS.items():
  matches=[r for r in rows if r['name']==p['member']]
  req(len(matches)==1,'wrong/missing slot member: '+p['member'])
  r=matches[0]
  req(r['payload_offset']==p['offset'] and r['size']==p['size'] and
      r['mode']==0o100755 and r['nlink']==1,'slot header/offset/size/mode mismatch')
  found[tag]=r
 req(len(rows)==1141 and rows[-1]['name']=='TRAILER!!!','wrong archive member count')
 return found
def release_fits(tag,data):
 req(len(data)<=PINS[tag]['size'],'release exceeds '+tag+' fixed slot')
 req(data.startswith(b'\x7fELF'),'release is not ELF')
def source_manifest(cmd):
 include=[Path(a[2:]) for a in cmd if a.startswith('-I')]
 pending=[Path(a) for a in cmd[2:] if Path(a).is_file()]
 seen={}
 while pending:
  p=pending.pop();p=m.safe_path(p)
  if str(p) in seen:continue
  b=m.read_file(p);seen[str(p)]=sha(b)
  if p.suffix.lower() in ('.c','.h','.inc','.s'):
   for name in re.findall(rb'^\s*#include\s*"([^"]+)"',b,re.M):
    candidates=[p.parent/name.decode(),*[d/name.decode() for d in include]]
    f=next((f for f in candidates if f.is_file()),None)
    req(f is not None,'missing local include '+str(name));pending.append(f)
 return seen
def section_link(e,s):
 i=s['link'];req(i<len(e.sections),'bad section link')
 return e.sections[i]['name'] if i else None
def semantic(raw,release):
 audit=m.audit_elf(raw,release)
 a,b=m.ELF(raw),m.ELF(release)
 # The reused auditor checks all PHDR bytes, full ALLOC bytes/layout, dynsym,
 # dependencies, and every PT_LOAD byte (except three exact section-table fields).
 for name,x in a.by_name.items():
  if not x['flags']&2:continue
  y=b.by_name[name]
  req(section_link(a,x)==section_link(b,y),'ALLOC linked-section identity changed')
  if x['flags']&0x40:
   req(a.sections[x['info']]['name']==b.sections[y['info']]['name'],'ALLOC info link changed')
  else:req(x['info']==y['info'],'ALLOC section info changed')
 allowed=set(range(40,48))|set(range(60,64))
 segments=[]
 for i,p in enumerate(a.ph):
  x=a.span(p[2],p[5]);y=b.span(p[2],p[5])
  diffs=[p[2]+j for j,(v,w) in enumerate(zip(x,y)) if v!=w]
  req(set(diffs)<=allowed,'segment data changed outside section metadata')
  segments.append(dict(index=i,type=p[0],flags=p[1],file_offset=p[2],vaddr=p[3],
     paddr=p[4],filesz=p[5],memsz=p[6],align=p[7],raw_sha256=sha(x),
     release_sha256=sha(y),changed_file_offsets=diffs,
     zero_initialized_tail_bytes=p[6]-p[5] if p[0]==1 else None))
 hdrdiff=[dict(offset=i,before=x,after=y) for i,(x,y) in enumerate(zip(raw[:64],release[:64])) if x!=y]
 req(all(x['offset'] in allowed for x in hdrdiff),'forbidden ELF header byte changed')
 constructors=[]
 for name,s in a.by_name.items():
  if s['type'] in (14,15,16): # INIT_ARRAY, FINI_ARRAY, PREINIT_ARRAY
   constructors.append(dict(name=name,addr=s['addr'],bytes=s['size'],sha256=sha(s['data']),
       entries=list(struct.unpack('<'+'Q'*(len(s['data'])//8),s['data']))))
 audit.update(all_program_segment_comparisons=segments,actual_elf_header_byte_changes=hdrdiff,
   permitted_header_fields_only=['e_shoff','e_shnum','e_shstrndx'],
   alloc_section_link_identity_equal=True,constructors=constructors,
   entry_equal=a.h[4]==b.h[4],entry=a.h[4],
   dynamic_section_bytes_equal=a.by_name['.dynamic']['data']==b.by_name['.dynamic']['data'],
   target_loaded_or_executed=False)
 return audit
def preflight():
 m.volume_check();source_binaries()
 pin(BASE/'candidate.json',BASE_SHA)
 c=json.loads(m.read_file(BASE/'candidate.json'))
 req(c['memory_mib']==5120 and c['initrd_load_address']=='0x440000000','platform mismatch')
 req(c['initrd']==dict(path=str(BASE/'guest.cpio'),sha256=CPIO_SHA),'wrong base initrd')
 req(c['dtb']['sha256']==DTB_SHA,'DTB manifest mismatch');pin(c['dtb']['path'],DTB_SHA)
 pin(BASE/'guest.cpio',CPIO_SHA)
 with m.open_read(BASE/'guest.cpio') as f:rows=m.index_archive(f)
 found=slots(rows)
 with m.open_read(BASE/'guest.cpio') as f:
  for tag,r in found.items():
   f.seek(r['payload_offset']);req(sha(f.read(r['size']))==PINS[tag]['body_sha'],'old slot body hash mismatch')
 req((BASE/'guest.cpio').stat().st_size==453213884,'archive length mismatch')
 build_bytes=m.read_file(R35/'BUILD.json');build=json.loads(build_bytes)
 for tag,p in PINS.items():req(build[tag]['sha256']==p['raw_sha'] and build[tag]['exit']==0,'build receipt drift')
 # Coordinator explicitly accepted the final source/test/build gate in msg_a9774da2cd5d.
 pin(R35/'SOURCE-FREEZE.json','dd4f8a2045220a045c32b8a0a686227f08e4e8c2edc7adca8964a12ddedc66e4')
 pin(R35/'SHA256SUMS','c7aee1bf7a35320e3c8d08eec03214957832008197741feb971433f19c524a71')
 js(O/'INPUTS.json',dict(time=now(),volume_uuid=UUID,binaries=source_binaries(),candidate_sha256=BASE_SHA,
  cpio_sha256=CPIO_SHA,cpio_bytes=453213884,dtb=c['dtb'],slots=found,
  reference_tool=dict(path=str(TOOL),sha256=TOOL_SHA),
  r35_final_input_gate=dict(status='coordinator_verified',message='msg_a9774da2cd5d',
   source_freeze_sha256='dd4f8a2045220a045c32b8a0a686227f08e4e8c2edc7adca8964a12ddedc66e4',
   delivery_sha_manifest='c7aee1bf7a35320e3c8d08eec03214957832008197741feb971433f19c524a71')))
 write(O/'receipts/r35-BUILD-input.json',build_bytes)
 js(O/'source-index.json',rows)
 return build
def release_build(build):
 env=dict(os.environ,ZIG_GLOBAL_CACHE_DIR=str(O/'zig-global-cache'),
          ZIG_LOCAL_CACHE_DIR=str(O/'zig-local-cache'),TMPDIR=str(O/'tmp'),
          XDG_CACHE_HOME=str(O/'zig-global-cache'),PYTHONDONTWRITEBYTECODE='1')
 zig=build['osd']['argv'][0]
 version=subprocess.run([zig,'version'],capture_output=True,text=True,env=env,timeout=10)
 req(version.returncode==0,'tool version query failed')
 js(O/'TOOL.json',dict(path=zig,sha256=m.sha_file(zig),version=version.stdout,
  version_stderr=version.stderr,method='exact original command plus linker --strip-debug',
  reference='r16-fixed-slot-guests/prepare_r15_samples.py',
  coordinator_confirmation='msg_d0073edba2ce',env_overrides={k:env[k] for k in
   ['ZIG_GLOBAL_CACHE_DIR','ZIG_LOCAL_CACHE_DIR','TMPDIR','XDG_CACHE_HOME','PYTHONDONTWRITEBYTECODE']},
  unavailable={'xcrun llvm-strip':'utility not found','xcrun llvm-objcopy':'utility not found',
   'zig objcopy --strip-debug':'prior r15 OBJCOPY-FAILED.json: ELF unimplemented; not retried'}))
 results={}
 for tag in ('ui','osd'):
  p=PINS[tag];raw=m.read_file(R35/'build'/('fx3-'+tag+'-r35.so'));req(sha(raw)==p['raw_sha'],'binary drift')
  write(O/'raw'/('fx3-'+tag+'-r35.so'),raw)
  original=build[tag]['argv'];before=source_manifest(original)
  command=list(original);target=O/'release'/('fx3-'+tag+'-r35.so')
  command[command.index('-o')+1]=str(target);command.insert(2,'-Wl,--strip-debug')
  js(O/'receipts'/(tag+'-release.INCOMPLETE.json'),dict(state='incomplete',time=now(),command=command))
  m.volume_check();outpath(target);req(not target.exists(),'release exists')
  r=subprocess.run(command,capture_output=True,env=env,timeout=180)
  write(O/'receipts'/(tag+'-release.stdout'),r.stdout);write(O/'receipts'/(tag+'-release.stderr'),r.stderr)
  after=source_manifest(original);req(before==after,'source input changed during release build')
  receipt=dict(command=command,original_command=original,exit=r.returncode,
    only_command_changes=['insert -Wl,--strip-debug','output path'],source_hashes_before=before,
    source_hashes_after=after,tool_sha256=m.sha_file(zig),env_write_roots=[str(O)],
    no_target_execution=True)
  js(O/'receipts'/(tag+'-release-command.json'),receipt)
  req(r.returncode==0,'release build failed')
  data=m.read_file(target);audit=semantic(raw,data)
  js(O/(tag+'-ELF-AUDIT.json'),audit)
  release_fits(tag,data)
  results[tag]=dict(raw_path=str(O/'raw'/('fx3-'+tag+'-r35.so')),raw_sha256=sha(raw),raw_bytes=len(raw),
    release_path=str(target),release_sha256=sha(data),release_bytes=len(data),
    slot_bytes=p['size'],zero_tail_bytes=p['size']-len(data),audit_path=str(O/(tag+'-ELF-AUDIT.json')),
    removed_debug_sections=audit['removed_debug_sections'],removed_static_sections=audit['removed_static_symbol_sections'])
 source_binaries();js(O/'RELEASES.json',results)
 return results
def negative_tests(releases):
 rows=json.loads(m.read_file(O/'source-index.json'));tests=[]
 def reject(name,fn):
  try:fn()
  except (ValueError,AssertionError,FileNotFoundError) as e:tests.append(dict(name=name,rejected=True,reason=str(e)))
  else:raise AssertionError('negative accepted: '+name)
 reject('oversized_ui_slot',lambda:release_fits('ui',b'\x7fELF'+b'X'*PINS['ui']['size']))
 reject('wrong_original_hash',lambda:pin(O/'raw/fx3-ui-r35.so','0'*64))
 reject('write_outside_authorized_output',lambda:outpath(R35/'build/r36-forbidden.so'))
 reject('path_traversal',lambda:outpath(O/'..'/'r36-forbidden'))
 altered=copy.deepcopy(rows);next(r for r in altered if r['name']==PINS['ui']['member'])['name']='simulation/wrong.so'
 reject('wrong_archive_member',lambda:slots(altered))
 altered=copy.deepcopy(rows);next(r for r in altered if r['name']==PINS['osd']['member'])['payload_offset']+=4
 reject('out_of_bounds_or_shifted_slot',lambda:slots(altered))
 raw=m.read_file(O/'raw/fx3-ui-r35.so');data=m.read_file(releases['ui']['release_path']);e=m.ELF(data)
 bad=bytearray(data);bad[e.by_name['.text']['offset']]^=1
 reject('machine_instruction_change',lambda:semantic(raw,bytes(bad)))
 bad=bytearray(data);bad[e.h[5]+16]^=1
 reject('program_header_change',lambda:semantic(raw,bytes(bad)))
 bad=bytearray(data);bad[24]^=1
 reject('entry_change',lambda:semantic(raw,bytes(bad)))
 js(O/'TESTS.json',dict(scope='host validators only; no target load/execute',count=len(tests),tests=tests))
def package(releases):
 m.volume_check();source_binaries();pin(BASE/'candidate.json',BASE_SHA)
 source_before=pin(BASE/'guest.cpio',CPIO_SHA)
 with m.open_read(BASE/'guest.cpio') as f:rows=m.index_archive(f)
 slots(rows)
 padded={}
 for tag,p in PINS.items():
  data=m.read_file(releases[tag]['release_path']);req(sha(data)==releases[tag]['release_sha256'],'release drift')
  release_fits(tag,data);semantic(m.read_file(O/'raw'/('fx3-'+tag+'-r35.so')),data)
  padded[tag]=data+bytes(p['size']-len(data))
 target=O/'guest.cpio';outpath(target)
 js(O/'PACKAGE.INCOMPLETE.json',dict(state='incomplete',time=now(),target=str(target),
   base_sha256=source_before,allowed_spans=[dict(tag=t,offset=p['offset'],bytes=p['size']) for t,p in PINS.items()]))
 with m.open_read(BASE/'guest.cpio') as src, target.open('xb') as dst:
  st=os.fstat(src.fileno());position=0
  for tag,p in sorted(PINS.items(),key=lambda item:item[1]['offset']):
   left=p['offset']-position
   while left:
    b=src.read(min(left,1<<20));req(bool(b),'source short read');dst.write(b);left-=len(b)
   old=src.read(p['size']);req(len(old)==p['size'] and sha(old)==p['body_sha'],'old slot drift')
   dst.write(padded[tag]);position=p['offset']+p['size']
  while b:=src.read(1<<20):dst.write(b)
  dst.flush();os.fsync(dst.fileno());st2=os.fstat(src.fileno())
  req((st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns)==(st2.st_dev,st2.st_ino,st2.st_size,st2.st_mtime_ns),'source file identity changed')
 req(target.stat().st_size==453213884,'output archive length changed')
 verification=verify_archive(target,releases)
 source_after=pin(BASE/'guest.cpio',CPIO_SHA);source_binaries();pin(BASE/'candidate.json',BASE_SHA)
 c=json.loads(m.read_file(BASE/'candidate.json'));old=copy.deepcopy(c)
 c['initrd']=dict(path=str(target),sha256=verification['output_sha256'])
 c['r36_fixed_slot_diagnostic_contract']=dict(
   base_candidate=dict(path=str(BASE/'candidate.json'),sha256=BASE_SHA),
   base_initrd_sha256=CPIO_SHA,member_releases=releases,
   supersedes_current_payload_references_only_in=['v25_diagnostic_contract','fixed_layout_diagnostic_contract'],
   prior_contracts_are_baseline_provenance=True,slot_headers_offsets_total_length_unchanged=True,
   original_init_other_members_and_DTB_unchanged=True,only_two_member_bodies_changed=True,
   r35_final_source_test_build_gate='coordinator_verified_msg_a9774da2cd5d',
   runtime_validated=False,runner_bound=False,VM_authorized=False,
   next_gate='separately bind new candidate to host runner; preserve original ready/180s/20s/cleanup policy')
 changed=sorted(k for k in set(old)|set(c) if old.get(k)!=c.get(k))
 req(changed==['initrd','r36_fixed_slot_diagnostic_contract'],'unexpected candidate field changes')
 req(c['dtb']==old['dtb'] and c['memory_mib']==5120 and c['initrd_load_address']=='0x440000000','platform drift')
 pin(c['dtb']['path'],DTB_SHA)
 js(O/'candidate.json',c)
 js(O/'PACKAGE-COMPLETE.json',dict(state='offline_package_complete',time=now(),
   source_before_sha256=source_before,source_after_sha256=source_after,
   output_sha256=verification['output_sha256'],candidate_sha256=m.sha_file(O/'candidate.json'),
   candidate_changed_fields=changed,source_binaries_after=source_binaries(),
   historical_incomplete_marker_superseded=True,VM_started=False,runner_modified=False,deployed=False))
 return verification
def verify_archive(target,releases):
 req(target==O/'guest.cpio','unexpected archive target')
 with m.open_read(BASE/'guest.cpio') as f:old=m.index_archive(f)
 with m.open_read(target) as f:new=m.index_archive(f)
 req(old==new,'CPIO header/name/order/mode/length/offset changed');slots(new)
 comparison=[];changed=[]
 with m.open_read(BASE/'guest.cpio') as src,m.open_read(target) as dst:
  for a,b in zip(old,new):
   hs=[]
   for f,r in [(src,a),(dst,b)]:
    f.seek(r['payload_offset']);left=r['size'];h=hashlib.sha256()
    while left:
     q=f.read(min(left,1<<20));req(bool(q),'truncated body');h.update(q);left-=len(q)
    hs.append(h.hexdigest())
   match=hs[0]==hs[1]
   if not match:changed.append(a['name'])
   comparison.append(dict(name=a['name'],header_offset=a['header_offset'],
    payload_offset=a['payload_offset'],size=a['size'],mode=a['mode'],
    header_equal=True,source_body_sha256=hs[0],output_body_sha256=hs[1],body_equal=match))
 req(set(changed)=={p['member'] for p in PINS.values()},'changed wrong member bodies')
 slotproof=[]
 with m.open_read(target) as f:
  for tag,p in PINS.items():
   f.seek(p['offset']);body=f.read(p['size']);data=m.read_file(releases[tag]['release_path'])
   req(body==data+bytes(p['size']-len(data)),'slot is not exact release plus zero tail')
   slotproof.append(dict(tag=tag,member=p['member'],offset=p['offset'],size=p['size'],
    release_bytes=len(data),zero_tail_bytes=p['size']-len(data),padded_slot_sha256=sha(body),
    exact_release_plus_zero_tail=True))
 # Separate complete sequential byte comparison, including all headers/names/padding.
 ranges=sorted((p['offset'],p['offset']+p['size']) for p in PINS.values())
 bytecounts={tag:0 for tag in PINS};h1=hashlib.sha256();h2=hashlib.sha256();offset=0
 with m.open_read(BASE/'guest.cpio') as src,m.open_read(target) as dst:
  while x:=src.read(1<<20):
   y=dst.read(len(x));req(len(x)==len(y),'archive size mismatch')
   h1.update(x);h2.update(y)
   if x!=y:
    for j,(u,v) in enumerate(zip(x,y)):
     if u!=v:
      absolute=offset+j
      tags=[tag for tag,p in PINS.items() if p['offset']<=absolute<p['offset']+p['size']]
      req(len(tags)==1,'byte changed outside the two authorized spans');bytecounts[tags[0]]+=1
   offset+=len(x)
  req(not dst.read(1),'extra archive bytes')
 req(h1.hexdigest()==CPIO_SHA and offset==453213884,'source archive drift/length')
 js(O/'member-comparison.json',comparison)
 result=dict(schema='r36-two-fixed-slot-archive-diff/v1',source_sha256=h1.hexdigest(),
   output_sha256=h2.hexdigest(),archive_bytes=offset,member_count_without_trailer=len(old)-1,
   trailer_end=old[-1]['next_offset'],all_headers_names_order_modes_sizes_offsets_equal=True,
   outside_two_slots_every_byte_equal=True,changed_members=changed,
   changed_byte_count_by_slot=bytecounts,slot_proofs=slotproof,
   init=next(r for r in comparison if r['name']=='init'),all_other_members_body_hash_equal=True,
   candidate_generated_count=1,N1_generated=False,target_loaded_or_executed=False)
 js(O/'ARCHIVE-DIFF.json',result)
 return result
def main():
 p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare-release','test-package'])
 a=p.parse_args();m.volume_check()
 if a.stage=='prepare-release':release_build(preflight())
 else:
  r=json.loads(m.read_file(O/'RELEASES.json'));negative_tests(r);result=package(r)
  print(json.dumps(result,indent=2))
if __name__=='__main__':
 try:main()
 except BaseException as exc:
  failure=O/'receipts'/('failure-'+str(__import__('time').time_ns())+'.json')
  js(failure,dict(time=now(),type=type(exc).__name__,message=str(exc),target_executed=False))
  raise

