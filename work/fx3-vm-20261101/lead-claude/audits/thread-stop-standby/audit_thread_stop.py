#!/usr/bin/env python3
"""Offline AP96 signal-stop audit; only writes sibling thread-stop-proof.json.

Uses existing capstone/pyelftools venv; never runs target code, QEMU or runner.
The coordinator narrowed this audit to assert -> kernel exception stop.
"""
import sys
sys.dont_write_bytecode = True
from pathlib import Path
from io import BytesIO
from hashlib import sha256
import importlib.util
import json
import plistlib
import re
import struct
import subprocess
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
from elftools.elf.elffile import ELFFile

ROOT = Path('/Volumes/KAFU2T/AI/Projects/Mac')
OUT = Path(__file__).resolve().parent
assert OUT == ROOT/'work/fx3-vm-20261101/lead-claude/audits/thread-stop-standby'
v = plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
assert v['VolumeUUID'] == 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
VM = ROOT/'work/fx3-vm-20261101/menu-repair-01'
RT = VM/'runtime'
AP = VM/'original-uipc/ap-projection/regular-files'
RUN = RT/'runs/ap96v1replaydiag-0f72a1e0'
CS = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
inputs = {}

def read(p):
    b = p.read_bytes()
    inputs[str(p.relative_to(ROOT))] = dict(bytes=len(b), sha256=sha256(b).hexdigest())
    return b

class Elf:
    def __init__(self,p):
        self.p=p; self.b=read(p); self.e=ELFFile(BytesIO(self.b))
        s=self.e.get_section_by_name('.dynsym')
        self.syms={x.name:x for x in s.iter_symbols()} if s else {}
        self.plt={}
        rel=self.e.get_section_by_name('.rela.plt'); pl=self.e.get_section_by_name('.plt')
        if rel and pl:
            self.plt={pl['sh_addr']+32+16*i:s.get_symbol(r['r_info_sym']).name
                      for i,r in enumerate(rel.iter_relocations())}
    def at(self,a,n):
        for s in self.e.iter_segments():
            if s['p_type']=='PT_LOAD' and s['p_vaddr']<=a and a+n<=s['p_vaddr']+s['p_filesz']:
                o=s['p_offset']+a-s['p_vaddr'];return self.b[o:o+n]
        raise ValueError((str(self.p),hex(a),n))
    def dis(self,a,n): return dis(self.at(a,n),a)
    def string(self,a):return self.at(a,256).split(b'\0')[0].decode()

def dis(b,a):
    return [dict(va=hex(v),bytes=b[v-a:v-a+n].hex(),instruction=m+' '+o)
            for v,n,m,o in CS.disasm_lite(b,a)]

def contains(block,a,instruction):
    assert any(x['va']==hex(a) and x['instruction']==instruction for x in block),(hex(a),instruction)

read(Path(__file__).resolve())
serial_b=read(RUN/'serial.log')
# Physical LF numbering, never splitlines(): binary log includes other control bytes.
lines=serial_b.decode(errors='replace').split('\n')
def hits(pattern):
    rx=re.compile(pattern)
    return [dict(LF_line=i+1,text=l.rstrip('\r')) for i,l in enumerate(lines) if rx.search(l.rstrip('\r'))]
assertions=hits(r'FX3_SIGNAL_OBSERVE api=assert|FX3_ASSERT_OBSERVE|assert at infra_wrapper_bb|Assertion `false')
assert assertions and all('248' in str(x['LF_line']) for x in assertions)
stop_hits=hits(r'do_signal_stop')
first_stop=stop_hits[0]['LF_line']
fatal_line=next(x['LF_line'] for x in assertions if 'Assertion `false' in x['text'])
assert fatal_line < first_stop
warning_stats={}
for n in [1021,1022]:
    h=hits(r'warning ret = -'+str(n)+r'$')
    warning_stats[str(-n)]={'total':len(h),'before_fatal':sum(x['LF_line']<fatal_line for x in h),
        'after_fatal':sum(x['LF_line']>fatal_line for x in h),'first':h[:1],
        'around_fatal':[x for x in h if fatal_line-60<=x['LF_line']<=first_stop+2][:60]}
assert warning_stats['-1021']['after_fatal'] > 0
assert warning_stats['-1021']['before_fatal'] == 0
live= json.loads(read(RT/'ap96v1replaydiag-0f72a1e0-thread-live-readonly.json'))
stopped=next(i for i,x in enumerate(live['blocks']) if 'T (stopped)' in ''.join(x['states']))
timeline={'line_convention':'1-based physical LF, CR stripped, interleaving retained',
    'serial_bytes':len(serial_b),'serial_LF_count':len(lines)-1,'assertions':assertions,
    'first_stop':stop_hits[:2],'thread_last_before':live['blocks'][stopped-1],
    'first_stop_window':[dict(LF_line=i+1,text=lines[i].rstrip('\r')) for i in range(first_stop-13,first_stop+8)],
    'thread_first_stopped':live['blocks'][stopped],
    'warnings':warning_stats,
    'second_0119':hits(r'FX3_BOOT_TAIL_REQUEST.*destination=0x92840747.*raw=0d2019011c000180')[-2:],
    'keyworker_identity':hits(r'FX3_KEY96_POLL tid=327')[:1],
    'native_infra_receiver':hits(r'FX3_UIPC_RECV_BEGIN tid=258 name=THREAD_INFRA1'),
    'exception_init':hits(r'calling.*em_module_init|initcall.*em_module_init')}

app=Elf(AP/'usr/lib/appFw.so');libc=Elf(AP/'lib/libc-2.25.so');im=Elf(AP/'usr/bin/im.elf')
blocks={
    'app_lib_assert':app.dis(0x2ebf3b0,0x9c),
    'app_send_and_wait_cmp_send_error':app.dis(0x2de723c,0x160),
    'libc_assert_fail':libc.dis(0x2a930,0x4c),
    'libc_assert_to_abort':libc.dis(0x2a8b8,0x6c),
    'libc_abort':libc.dis(0x32350,0x2ac),
    'libc_raise':libc.dis(0x30fe0,0xcc)}
contains(blocks['app_lib_assert'],0x2ebf420,'bl #0x1594060')
assert app.plt[0x1594060]=='__assert_fail'
assert app.plt[0x1592f10]=='osal_snd_msg'
contains(blocks['app_send_and_wait_cmp_send_error'],0x2de7260,'bl #0x1592f10')
contains(blocks['app_send_and_wait_cmp_send_error'],0x2de7264,'cbz w0, #0x2de72f4')
contains(blocks['libc_assert_to_abort'],0x2a8e0,'bl #0x32350')
contains(blocks['libc_abort'],0x32470,'bl #0x30fe0')
contains(blocks['libc_raise'],0x31044,'mov x8, #0x83')
contains(blocks['libc_raise'],0x31054,'svc #0')

kp=ROOT/'work/sony-firmware-20261024/stage146-original-kernel-symbol-and-vendor-route/kernel_symbols.py'
read(kp);spec=importlib.util.spec_from_file_location('thread_stop_kernel_symbols',kp)
km=importlib.util.module_from_spec(spec);spec.loader.exec_module(km);kernel=km.KernelSymbols();read(km.KERNEL)
knames=['get_signal','do_signal_stop','do_coredump','stop_all_threads_timeout','start_all_threads','__boottime_em_module_init','em_exception_monitor']
kb={}
for name in knames:
    a,z=kernel.span(name)
    kb[name]={'va':hex(km.K+a),'next_symbol_span_bytes':z-a,
        'instructions':dis(kernel.raw[a:z],km.K+a)}
contains(kb['stop_all_threads_timeout']['instructions'],0xffffff80080c5ae4,'mov w0, #0x13')
contains(kb['stop_all_threads_timeout']['instructions'],0xffffff80080c5af8,'bl #0xffffff80080adb68')
assert kernel.unique('send_sig')['address']==0xffffff80080adb68
contains(kb['do_coredump']['instructions'],0xffffff80081dcb04,'bl #0xffffff80080c5a50')
contains(kb['__boottime_em_module_init']['instructions'],0xffffff800863cd48,'str x1, [x2, #0x6e8]')
exception_mode=struct.unpack_from('<I',kernel.raw,kernel.unique('exception_check_mode')['file_offset'])[0]
assert exception_mode==3

# ET_REL instruction addresses below are .text offsets, not loaded kernel VAs.
ko_p=VM/'original-uipc/original-modules/osal_uipc.ko';ko_b=read(ko_p);ko_e=ELFFile(BytesIO(ko_b));kt=ko_e.get_section_by_name('.text')
ko_blocks={hex(a):dis(kt.data()[a:a+n],a) for a,n in [(0x41a0,0x2c0),(0x44c0,0x168)]}
ko_reloc=[]
rel=ko_e.get_section_by_name('.rela.text');ss=ko_e.get_section(rel['sh_link'])
for r in rel.iter_relocations():
    if 0x41a0<=r['r_offset']<0x4628:
        ko_reloc.append({'text_offset':hex(r['r_offset']),'symbol':ss.get_symbol(r['r_info_sym']).name,'addend':r['r_addend']})
contains(ko_blocks['0x41a0'],0x43d8,'mov w21, #-0x3fd')
contains(ko_blocks['0x41a0'],0x436c,'mov w21, #-0x3fe')

# Inventory all projected AP ELF DSOs, flag those observed in maps, and scan
# direct B/BL to signal PLT entries. Indirect/direct-syscall completeness is NOT claimed.
loaded=set(re.findall(r'/(?:usr/lib|lib)/([^\s/]+)',serial_b.decode(errors='replace')))
signal_names={'kill','tgkill','tkill','raise','pthread_kill','ptrace','abort','__assert_fail','syscall'}
inventory=[]
for p in sorted((AP/'usr/lib').iterdir())+sorted((AP/'lib').iterdir())+[AP/'usr/bin/im.elf']:
    if not p.is_file() or p.read_bytes()[:4]!=b'\x7fELF':continue
    ob=app if p==app.p else libc if p==libc.p else im if p==im.p else Elf(p)
    imports=sorted(n for n in signal_names if n in ob.syms and ob.syms[n]['st_shndx']=='SHN_UNDEF')
    row={'path':str(p.relative_to(ROOT)),'seen_name_in_serial':p.name in loaded,'signal_imports':imports}
    if imports:
        target={a:n for a,n in ob.plt.items() if n in signal_names-{'__assert_fail','abort','syscall'}}
        calls=[];sec=ob.e.get_section_by_name('.text')
        if sec and target:
            b=sec.data();base=sec['sh_addr']
            for j,(word,) in enumerate(struct.iter_unpack('<I',b[:len(b)//4*4])):
                if word&0x7c000000!=0x14000000:continue
                imm=word&0x3ffffff
                if imm&(1<<25):imm-=1<<26
                a=base+j*4;t=a+imm*4
                if t in target:
                    calls.append({'va':hex(a),'target':hex(t),'api':target[t],
                        'context':ob.dis(max(base,a-32),min(40,base+len(b)-max(base,a-32)))})
        row['direct_signal_PLT_calls']=calls
    inventory.append(row)

source_paths=[RT/'helpers/signal-observe-v2.c',RT/'helpers/fx3-rm-empty-provider-v7-diag96.c',
    RT/'helpers/fx3-rm-key-gate-v5-diag96.inc',RT/'ap96-v1-setup-replay-input-diag/init-review.sh',
    RUN/'observer-source/run_candidate96.py',RT/'ap95-ap96-native-assert-correction.json']
sources={}
for p in source_paths:
    b=read(p); ls=b.decode(errors='replace').split('\n')
    sources[str(p.relative_to(ROOT))]=[{'line':i+1,'text':l} for i,l in enumerate(ls)
        if re.search(r'kill|SIG|signal|assert|abort|pthread_create|keyworker|qmp\(.stop|FX3_KEY96|__errno',l)]

proof={'schema':'thread-stop-standby-v1','scope':'read-only static + existing AP96 receipts; no QEMU or target execution',
 'coordinator_scope_change':'msg_2f2fb41c2314: narrow to original assert/abort -> exception monitor SIGSTOP and UIPC chronology',
 'verdict':{'sender':'Original Sony kernel stop_all_threads_timeout -> send_sig(SIGSTOP, same-mm peer, 1)',
    'trigger':'appFw lib::assert::notify_model_system_error -> libc __assert_fail/abort/raise(SIGABRT) -> kernel get_signal/do_coredump exception branch',
    'confidence':'Static path complete and serial order strongly matching; initiating fault thread kernel stack/siginfo not captured',
    'not_demonstrated':'No evidence of standby/auto-poweroff/battery/SysCon timeout as this stop cause',
    'target_identity':'tid327 is software input keyworker; THREAD_INFRA1 is inherited comm, native receiver is tid258',
    'root_trigger_correction':'infra_wrapper_bb.cpp:870 here is nonzero osal_snd_msg return, before receive wait; do not label it a proved completion timeout'},
 'timeline':timeline,'app_libc_blocks':blocks,'assert_strings':{hex(a):app.string(a) for a in [0x3799697,0x39a5a78,0x39a5a88]},
 'kernel':{'sha256':sha256(kernel.raw).hexdigest(),'exception_check_mode_initial':exception_mode,'blocks':kb},
 'osal_kernel':{'address_rule':'ET_REL .text offsets; relocation names recorded separately','blocks':ko_blocks,'relocations':ko_reloc,
    'interpretation':'-1021 (-0x3fd) follows current thread TIF_SIGPENDING check at43cc..43d8; -1022 (-0x3fe) is empty/timed wait return, not a signal number or a universally unavailable-service code'},
 'signal_inventory':inventory,'source_evidence':sources,
 'limitations':['No kernel signal_generate trace or faulting thread do_coredump stack; exact runtime SIGSTOP provenance is inferred from matching original path.',
    'No proof that all observed -1022 warnings target VDF; generic cdev warning lacks queue/TID/op.',
    'Direct B/BL/PLT inventory is not exhaustive of indirect pointers, hidden symbols or direct svc; libc raise direct tgkill is separately disassembled.',
    'No correction made to runtime; repair must preserve original assert and implement repeated VDF requests with current lease/source/generation.',
    'Original task standby sweep superseded by coordinator scope change; no speculative battery/input fabrication.'],
 'inputs':inputs}
(OUT/'thread-stop-proof.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'result':'PASS','projected_ELFs':len(inventory),'assert_LF':fatal_line,'first_stop_LF':first_stop,
    'warnings':{k:{z:v[z] for z in ['total','before_fatal','after_fatal']} for k,v in warning_stats.items()},
    'proof':str(OUT/'thread-stop-proof.json')},ensure_ascii=False))
