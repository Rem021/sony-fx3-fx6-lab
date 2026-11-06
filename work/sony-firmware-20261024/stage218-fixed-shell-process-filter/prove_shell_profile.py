"""Original argument/ELF-file bindings only. Never executes Sony code."""
from pathlib import Path
from hashlib import sha256
from io import BytesIO
import json,struct
from elftools.elf.elffile import ELFFile
H=Path(__file__).resolve().parent;B=H.parent
source=B/'stage184-community-recovery-and-standalone-service/evidence/standalone-commands/originals/lib/libJiritsu.so'
raw=source.read_bytes();digest=sha256(raw).hexdigest();assert digest=='bdef58b24a3b67b4d14d4f0214b89aae0fcad19f114b4188c328f9d2c092f1d9'
e=ELFFile(BytesIO(raw));st=e.get_section_by_name('.dynsym');syms={s.name:s for s in st.iter_symbols()}
plt=e.get_section_by_name('.plt');rel=e.get_section_by_name('.rela.plt');targets={plt['sh_addr']+32+16*i:st.get_symbol(x['r_info_sym']).name for i,x in enumerate(rel.iter_relocations())}
def original(va,size):
 p=next(p for p in e.iter_segments() if p['p_type']=='PT_LOAD' and p['p_vaddr']<=va and va+size<=p['p_vaddr']+p['p_filesz']);off=p['p_offset']+va-p['p_vaddr'];return raw[off:off+size],off
def string(va):return original(va,256)[0].split(b'\0',1)[0]
assert string(0x30707)==b'/bin/sh' and string(0x3070f)==b'-c'
fmt=string(0x31e6d);assert fmt==b'/bin/date -s %02d%02d%02d%02d%04d.%02d'
review=json.loads((B/'stage188-static-ELF-link-and-explicit-entry/launch-route-review.json').read_text());cuts=[]
for name in ['cmd_debug','sys_set_timeofday','_ZN13CShellExecute12ExecShellNewEPc']:
 s=syms[name];data,off=original(s['st_value'],s['st_size']);prior=next(x for x in review['functions'] if x['name']==name);assert data.hex()==prior['original_hex'] and sha256(data).hexdigest()==prior['sha256']
 dest=H/'raw'/name;dest.parent.mkdir(exist_ok=True);dest.open('xb').write(data);cuts.append(dict(name=name,source=str(source.relative_to(B.parent.parent)),source_sha256=digest,start=s['st_value'],bytes=len(data),file_offset=off,sha256=sha256(data).hexdigest(),output=str(dest.relative_to(H))))
for label,va in [('shell-path',0x30707),('shell-c-option',0x3070f),('date-format',0x31e6d)]:
 data=string(va)+b'\0';_,off=original(va,len(data));p=H/'raw'/label;p.open('xb').write(data);cuts.append(dict(name=label,source=str(source.relative_to(B.parent.parent)),source_sha256=digest,start=va,bytes=len(data),file_offset=off,sha256=sha256(data).hexdigest(),output=str(p.relative_to(H))))
checks=[]
def word(at):return struct.unpack('<I',original(at,4)[0])[0]
def expect(at,value,meaning):
 assert word(at)==value;checks.append(dict(VA=hex(at),word=hex(value),meaning=meaning))
def adrp_add(at,add_at,want):
 a,b=word(at),word(add_at);assert a&0x9f00001f==0x90000001 and b&0xffc003ff==0x91000021
 v=((a>>29)&3)|((a>>5)&0x7ffff)<<2;v=v-(1<<21) if v&(1<<20) else v
 resolved=(at&~4095)+(v<<12)+((b>>10)&4095);assert resolved==want;checks.append(dict(VA=hex(at),add_VA=hex(add_at),adrp_word=hex(a),add_word=hex(b),resolves_to=hex(want)))
adrp_add(0x6c90,0x6c94,0x30707);adrp_add(0x6ca0,0x6ca4,0x3070f)
expect(0x6c9c,0xf90013a1,'argv0=/bin/sh stored at frame+0x20')
expect(0x6cac,0xf90017a1,'argv1=-c stored at frame+0x28')
expect(0x6ca8,0xa9037fa0,'argv2=input command,argv3=null stored at frame+0x30/+0x38')
expect(0x6cc8,0xf94013a0,'execv pathname loads argv0')
expect(0x6ccc,0x910083a1,'execv argv points at frame+0x20')
for at,name in [(0x6cb0,'fork'),(0x6cc0,'_exit'),(0x6cd0,'execv'),(0x6ce0,'waitpid')]:
 w=word(at);assert w&0xfc000000==0x94000000;v=w&0x3ffffff;v=v-(1<<26) if v&(1<<25) else v;target=at+v*4;assert targets[target]==name;checks.append(dict(VA=hex(at),word=hex(w),PLT_target=hex(target),callee=name))
# Fixed debug constants were already decoded from the original mov fields.
for at,reg,value in [(0x83c4,5,26),(0x83c8,4,42),(0x83cc,3,21),(0x83dc,2,4),(0x83e0,1,7),(0x83e4,0,2017)]:
 w=word(at);assert w&0xffe00000==0x52800000 and w&31==reg and (w>>5)&0xffff==value;checks.append(dict(VA=hex(at),word=hex(w),register=reg,value=value))
command=fmt%(7,4,21,42,2017,26);expected=b'\0'.join([b'/bin/sh',b'-c',command])+b'\0'
assert command==b'/bin/date -s 070421422017.26'
# Original self/parent byte profiles are data only, not execution or body proof.
exe=json.loads((H/'executable-source-capture.json').read_text())['files']
for x in exe:assert sha256((H/x['output']).read_bytes()).hexdigest()==x['sha256']
report=dict(schema='fx3-original-shell-child-profile-v1',source_sha256=digest,original_ranges=cuts,raw_instruction_checks=checks,
 execv_path='/bin/sh',argv=['/bin/sh','-c',command.decode()],kernel_cmdline_hex=expected.hex(),kernel_cmdline_bytes=len(expected),
 direct_date_is_not_first_exec=True,reference_self_executable=exe[0],reference_parent_profile=exe[1],
 actual_camera_parent_identity_observed=False,parent_im_profile_is_fail_closed_candidate_assumption=True,
 raw_cmdline_and_backing_executable_hash_not_exclusive_origin_or_loaded_memory_attestation=True,
 original_clock_side_effect_still_possible_if_unintercepted=True,fork_failure_parent_exit_and_unbounded_wait_not_repaired=True,
 original_or_guest_Sony_execution=False,camera_operations=0)
(H/'shell-profile-proof.json').open('x').write(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(raw_ranges=len(cuts),instruction_checks=len(checks),first_exec='/bin/sh',argv=report['argv'],cmdline_bytes=len(expected))))
