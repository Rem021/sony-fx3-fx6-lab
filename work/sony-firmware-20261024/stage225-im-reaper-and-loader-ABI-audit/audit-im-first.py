"""Static original-byte and ABI audit. No firmware or Linux code execution."""
from pathlib import Path
from hashlib import sha256
import io,json,struct
from elftools.elf.elffile import ELFFile
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_ARM
H=Path(__file__).resolve().parent;R=H.parents[2];B=H.parent
IM=B/'stage218-fixed-shell-process-filter/originals/im.elf';raw=IM.read_bytes()
assert len(raw)==40920 and sha256(raw).hexdigest()=='5171f576d8b76cfbf15581389183b390c445bd6ff9dd97fd6668c5f64e77dc91'
assert raw==(B/'stage183-request-consumer-and-early-entry/evidence/usb-main-dependency/originals/bin/im.elf').read_bytes()
e=ELFFile(io.BytesIO(raw));segs=[s for s in e.iter_segments() if s['p_type']=='PT_LOAD'];md=Cs(CS_ARCH_ARM64,CS_MODE_ARM)
def read(va,n):
 s=next(s for s in segs if s['p_vaddr']<=va and va+n<=s['p_vaddr']+s['p_filesz']);return raw[s['p_offset']+va-s['p_vaddr']:s['p_offset']+va-s['p_vaddr']+n]
def word(va):return struct.unpack('<I',read(va,4))[0]
def bl(va):
 w=word(va);assert w&0xfc000000==0x94000000;imm=w&0x3ffffff
 if imm&(1<<25):imm-=1<<26
 return va+imm*4
syms=e.get_section_by_name('.dynsym');pltbase=e.get_section_by_name('.plt')['sh_addr']
plt={pltbase+32+i*16:syms.get_symbol(rel['r_info_sym']).name for i,rel in enumerate(e.get_section_by_name('.rela.plt').iter_relocations())}
checks=[]
for pc,expect in [(0x4024d8,'signal'),(0x402f60,'waitpid'),(0x405eac,'dlopen'),(0x405f0c,'dlsym'),(0x405f28,'dlclose'),(0x405f9c,'dlopen'),(0x406004,'dlsym'),(0x406038,'dlclose')]:
 target=bl(pc);ins=list(md.disasm(read(pc,4),pc));assert len(ins)==1 and ins[0].mnemonic=='bl' and int(ins[0].op_str[1:],16)==target and plt[target]==expect
 checks.append(dict(pc=pc,raw_hex=read(pc,4).hex(),manual_branch_target=target,PLT=expect))
# Independent ADRP/ADD decoding establishes callback address, not just a string.
w=word(0x4024cc);assert w&0x9f00001f==0x90000001;imm=((w>>5)&0x7ffff)*4+((w>>29)&3)
if imm&(1<<20):imm-=1<<21
page=(0x4024cc&~4095)+(imm<<12);w=word(0x4024d4);assert w&0xffc003ff==0x91000021
handler=page+((w>>10)&4095);assert handler==0x402f4c
assert word(0x4024d0)==0x52800220 # mov w0,#17 SIGCHLD
assert word(0x402f58)==0x52800022 and word(0x402f5c)==0x12800000 # WNOHANG1, PID-1
assert word(0x402f64)==0x7100001f # cmp w0,#0
w=word(0x402f68);assert w&0xff00001f==0x5400000c;imm=(w>>5)&0x7ffff
if imm&(1<<18):imm-=1<<19
assert 0x402f68+imm*4==0x402f54
# Current module loader prepares one selected descriptor field in x0, not the
# four typed arguments required by the own submit API.
assert word(0x405f44)&0xfffffc1f==0xd63f0000 and (word(0x405f44)>>5)&31==20
assert word(0x40602c)&0xfffffc1f==0xd63f0000 and (word(0x40602c)>>5)&31==20
slices=[]
for name,va,n in [('main-registers-SIGCHLD',0x4024cc,16),('SIGCHLD-waitpid-loop',0x402f4c,40),('loader-dlopen-and-one-selected-argument',0x405e98,0xc4),('loader-flagged-file-and-untyped-symbol-call',0x405f5c,0xe4),('module-type-loader-selector',0x40625c,0x30),('lifecycle-symbol-helper',0x4055f8,0xc4)]:
 data=read(va,n);instructions=[dict(pc=i.address,bytes=i.bytes.hex(),asm=i.mnemonic+' '+i.op_str) for i in md.disasm(data,va)];assert len(instructions)*4==n
 slices.append(dict(name=name,VA=va,bytes=n,sha256=sha256(data).hexdigest(),original_hex=data.hex(),instructions=instructions))
text=e.get_section_by_name('.text');calls=[]
for i in md.disasm(text.data(),text['sh_addr']):
 if i.mnemonic=='bl' and int(i.op_str[1:],16) in plt and plt[int(i.op_str[1:],16)]=='waitpid':calls.append(i.address)
assert calls==[0x402f60]
# Pin exact reference-kernel lines; these are inspected data, not executed C.
ranges=[]
for name,start,end,need in [('exit.c',976,1000,['if (ptrace || (wo->wo_flags & __WALL))','if ((p->exit_signal != SIGCHLD) ^ !!(wo->wo_flags & __WCLONE))']),('exec.c',1167,1174,['no_thread_group:','tsk->exit_signal = SIGCHLD;']),('wait.h',1,16,['#define __WCLONE','#define __WALL'])]:
 p=H/'source-reference'/name;lines=p.read_text().splitlines(keepends=True);piece=''.join(lines[start-1:end]);assert all(x in piece for x in need)
 ranges.append(dict(path=str(p.relative_to(R)),source_sha256=sha256(p.read_bytes()).hexdigest(),first_line=start,last_line=end,range_sha256=sha256(piece.encode()).hexdigest(),required_tokens=need))
report=dict(schema='fx3-current-im-loader-and-reaper-static-audit-v1',status='REFERENCE_IM_REAPS_NORMAL_CHILDREN_AND_LOADER_ABI_NEEDS_BRIDGE',source=dict(path=str(IM.relative_to(R)),bytes=len(raw),sha256=sha256(raw).hexdigest(),origin='saved official7.02 nflasha15 inode80972; not live body readback'),source_capture_record=str((B/'stage218-fixed-shell-process-filter/executable-source-capture.json').relative_to(R)),source_capture_sha256=sha256((B/'stage218-fixed-shell-process-filter/executable-source-capture.json').read_bytes()).hexdigest(),slices=slices,manual_encoding_and_PLT_checks=checks,SIGCHLD_number=17,SIGCHLD_handler=handler,handler_waitpid_pid=-1,handler_waitpid_options=1,handler_loops_while_return_positive=True,all_direct_waitpid_calls_in_this_ELF=calls,
 native_loader_establishes_own_four_argument_submit_contract=False,native_loader_request_parameter_bridge_implemented=False,constructor_only_memory_cannot_submit_or_poll=True,
 kernel_reference_ranges=ranges,clone_signal_zero_survives_exec=False,CLONE_zero_plus_WCLONE_not_a_fix=True,
 inference='Reference im handler can reap the own ordinary child before target wait4. Reaper may or may not win each schedule; no live frequency or actual handler installation observed.',
 candidate_architecture='Use a separate own keeper with explicit child-local signal policy, validated loader ABI bridge and private control/completion channel; do not modify original im signal disposition or infer trusted parent from inode alone.',
 isolated_keeper_or_loader_bridge_implemented=False,original_Sony_or_Linux_kernel_executed=False,new_camera_operations=0,hardware_validated=False,independent_recovery_proven=False,flashable=False)
(H/'im-loader-and-reaper-audit.json').open('x').write(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(status=report['status'],original_slices=len(slices),PLT_and_raw_call_checks=len(checks),waitpid_sites=calls,handler=hex(handler),four_arg_entry_proven=False,original_code_executed=False)))
