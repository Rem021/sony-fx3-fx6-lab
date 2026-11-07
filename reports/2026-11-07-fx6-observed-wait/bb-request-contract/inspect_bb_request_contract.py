#!/usr/bin/env python3
"""Pinned read-only 10B BB request/12B completion facts; no ELF/CP execution."""
from pathlib import Path
from io import BytesIO
import hashlib
import json
import struct
from capstone import Cs, CS_ARCH_ARM64, CS_ARCH_ARM, CS_MODE_ARM, CS_MODE_THUMB
from elftools.elf.elffile import ELFFile

REPO=Path('/Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab')
DONOR=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor')
APP=DONOR/'nflasha15-files/lib/appFw.so'
CP=DONOR/'fat-files/nflasha8/cpapp-b.bin'
CPIO=REPO/'work/fx6-worker-pool-restore-20261107/guest-worker-pool-restore295.cpio'
RUN=REPO/'work/fx6-worker-pool-restore-20261107/runs/worker-pool-restore-a3af746e3d'
CP_BASE=0x108000
PINS={APP:'a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067',
 CP:'60de0ab5544749dd50d8245f573c0994573fef349186efe20b502c42e3289668',
 CPIO:'6c698c7d1d4eac7ff54fc2bd6a54a54c3d4c9156f308aefae96b043ef22c5993'}
def sha(b):return hashlib.sha256(b).hexdigest()
def cp_insn(blob,va):
    item=next(Cs(CS_ARCH_ARM,CS_MODE_THUMB).disasm(blob[va-CP_BASE:va-CP_BASE+4],va))
    return f'{item.mnemonic} {item.op_str}'.rstrip()
def archive_app():
    with CPIO.open('rb') as f:
        while True:
            header=f.read(110);assert header[:6] in (b'070701',b'070702')
            fields=[int(header[6+i*8:14+i*8],16) for i in range(13)]
            size,namesize=fields[6],fields[11]
            name=f.read(namesize).rstrip(b'\0').decode();f.seek((-110-namesize)%4,1)
            if name=='TRAILER!!!':raise ValueError('missing appFw member')
            if name=='usr/lib/appFw.so':return f.read(size)
            f.seek(size+(-size)%4,1)
def main():
    receipts=[]
    for path,expected in PINS.items():
        with path.open('rb') as f:actual=hashlib.file_digest(f,'sha256').hexdigest()
        assert actual==expected
        receipts.append({'path':str(path),'bytes':path.stat().st_size,'sha256':actual})
    member=archive_app();assert sha(member)==PINS[APP]
    app=APP.read_bytes();cp=CP.read_bytes();elf=ELFFile(BytesIO(app))
    def appread(va,n):
        for seg in elf.iter_segments():
            if seg['p_type']=='PT_LOAD' and seg['p_vaddr']<=va and va+n<=seg['p_vaddr']+seg['p_filesz']:
                off=seg['p_offset']+va-seg['p_vaddr'];return app[off:off+n]
        raise ValueError('VA is not file-backed')
    def appone(va):
        i=next(Cs(CS_ARCH_ARM64,CS_MODE_ARM).disasm(appread(va,4),va))
        return f'{i.mnemonic} {i.op_str}'.rstrip()
    app_expected={
      0x20f15a0:'mov w1, #0x200d',0x20f15b0:'mov w1, #0x32d',
      0x20f15b8:'mov w1, #0xa',0x20f15c0:'mov w1, #-0x7fff',
      0x20f15cc:'strb w0, [x29, #0x28]',0x20f15f8:'mov w4, #0xc',
      0x20f15fc:'mov w2, #0xa',0x20f1608:'bl #0x20ef604',
      0x20f160c:'ldr w0, [x29, #0x38]',0x20f1610:'bl #0x20edd1c',
      0x20f1614:'str w0, [x19]',0x20ef784:'bl #0xb17880',
      0x20ef790:'bl #0xb17c70',0x20ef79c:'bl #0xb1a120',
      0x20ef7c4:'mov w2, #-1',0x20ef7c8:'bl #0xb19ec0',
      0x20ef7dc:'bl #0xb17880',0x20ef7e8:'bl #0xb19d40',
      0x20d00e4:'bl #0x20f158c',0x1cd80fc:'bl #0x20d00bc',
      0x1cd8100:'ldr w6, [x29, #0x38]',0x1cd8104:'cbz w6, #0x1cd81a4',
      0x1cd8184:'mov w0, #0x86a0',0x1cd8188:'movk w0, #1, lsl #16',
      0x1cd8190:'bl #0x2167780',0x2167780:'ret',
      0x1cd86a4:'bl #0x1cd80dc',0x1cd86a8:'ldr x0, [x23, #0x10]',
      0x20edd64:'cbz w0, #0x20edd94',0x20edd8c:'cmp w0, #0x580, lsl #12',
      0x20edd94:'mov w19, #0',0x20edf40:'mov w19, #0x6f',
      0x20edf44:'cmn w0, #1',0x20eddc8:'mov w19, #2',
    }
    app_checks={}
    for va,expected in app_expected.items():
        actual=appone(va);assert actual==expected,(hex(va),actual,expected);app_checks[hex(va)]=actual
    cp_expected={
      0x1a8a30:'ldr r6, [r4, #0xc]',0x1a8a38:'ldr r3, [r4]',
      0x1a8a3c:'sub.w r0, r3, #0x1e',0x1a8a46:'tbh [pc, r0, lsl #1]',
      0x1a9326:'bl #0x1af1b0',0x1a932a:'mov r5, r0',
      0x1a932e:'beq.w #0x1a90a4',0x1a9344:'bl #0x5dc82a',
      0x1af1be:'mov.w r0, #0x304',0x1af1c6:'movw r0, #0x2004',
      0x1af1ce:'movs r0, #0xc',0x1af1d8:'ldrb r3, [r4, #8]',
      0x1af1da:'cmp r3, #1',0x1af1de:'cbnz r3, #0x1af1e4',
      0x1af200:'ldrb r5, [r4, #8]',0x1af204:'strb.w r5, [sp, #0x14]',
      0x1af234:'movt r0, #0x9058',0x1af238:'movt r3, #0x9284',
      0x1af23c:'bl #0x5ec356',0x1af240:'cbz r0, #0x1af24c',
      0x1af248:'mov.w r4, #-1',0x1af24c:'mov r0, r4',
      0x1a994e:'ldr r1, [r4, #8]',0x1a9952:'movs r2, #0xbb',0x1a9954:'bl #0x5dc82a',
      0x5dc834:'mov r5, r1',0x5dc848:'movw r0, #0x132d',
      0x5dc854:'movs r0, #0xc',0x5dc85a:'movw r0, #0x200d',
      0x5dc862:'movw r0, #0x8001',0x5dc86a:'str r5, [sp, #0xc]',
      0x5dc870:'bl #0x1abecc',0x1abf06:'bl #0x4b6fa4',
      0x1abf1a:'movw r1, #0x747',0x1abf1e:'movt r1, #0x9284',
      0x1abf2c:'blx #0x5725b8',0x1abf48:'bl #0x4b68d8',
      0x1abf4e:'cbz r5, #0x1abf76',0x1abf54:'bl #0x4b70a0',
      0x1a90b6:'b.w #0x4b70a0',
    }
    cp_checks={}
    for va,expected in cp_expected.items():
        actual=cp_insn(cp,va);assert actual==expected,(hex(va),actual,expected)
        cp_checks[hex(va)]={'file_offset':hex(va-CP_BASE),'instruction':actual}
    table_base=0x1a8a4a;table_entry=table_base+2*(0xbb-0x1e)
    half=struct.unpack_from('<H',cp,table_entry-CP_BASE)[0]
    assert table_base+2*half==0x1a9324
    raw=bytes.fromhex('0d202d030a0001800000');assert struct.unpack('<5H',raw)==(0x200d,0x32d,10,0x8001,0)
    data=(RUN/'serial.log').read_bytes();lines=data.decode(errors='replace').splitlines()
    selected=[{'line':i+1,'text':s} for i,s in enumerate(lines) if
      ('destination=0x92840747' in s or 'FX6_QUEUE_OBS_ENTER seq=9 ' in s or
       'FX6_QUEUE_OBS_EXIT seq=9 ' in s or ('tid=231 ' in s and any(t in s for t in ('REG','FRAME','DETACH'))))]
    assert any('source=0x81cf610f' in x['text'] for x in selected)
    assert any('qid=0x81cf610f timeout=-1' in x['text'] for x in selected)
    assert not any('FX6_QUEUE_OBS_EXIT seq=9 ' in x['text'] for x in selected)
    mapping={0:0,1:0x6d,2:0x6e,4:0x8b,0xffffffff:0x6f,0x580000:0,
      0x58e001:0x80,0x58e002:0x81,0x58e003:0x82,0x58e004:0x83,0x58e005:0x84,
      0x58e006:0x85,0x58e007:0x86,0x58e008:0x87,0x58e009:0,0x58e00a:0x89,0x58efff:0x8a,
      0x590000:0,0x590001:0x70,0x590002:0x71,0x590003:0x72,0x590004:0x73,0x590005:0x74,
      0x590007:0x75,0x590010:0,0x591005:0x77,0x5a0000:0,0x5a0001:0x78,0x5a0002:0x79,
      0x5a0003:0x7a,0x5a0004:0x7b,0x5a0005:0x7c,0x5a0006:0x7d,0x5a0007:0x7e,0x5affff:0x7f}
    result={'status':'PASS','scope':'static bounded contract plus frozen actual worker-pool run; no original-code execution',
      'sources':receipts,'cp_mapping':{'base':'0x108000','architecture':'ARM32 flat image; selected consumers Thumb',
        'conversion':'file_offset = (VA & ~1) - 0x108000','sha256':PINS[CP]},
      'actual_cpio_app':{'member':'usr/lib/appFw.so','bytes':len(member),'sha256':sha(member)},
      'run_serial':{'path':str(RUN/'serial.log'),'bytes':len(data),'sha256':sha(data),'selected_lines':selected},
      'request':{'raw_hex':raw.hex(),'u16_header':['0x200d','0x032d',10,'0x8001'],
        'payload':'2B storage, producer writes first byte 0/1; current request 0',
        'destination':'0x92840747','source_and_waiting_queue':'0x81cf610f','request_bytes':10,'expected_reply_bytes':12},
      'ap_instruction_checks':app_checks,'cp_instruction_checks':cp_checks,
      'cp_tbh':{'index':'0xbb','subtract':'0x1e','table_base_va':hex(table_base),
        'entry_va':hex(table_entry),'entry_file_offset':hex(table_entry-CP_BASE),
        'entry_u16':hex(half),'resolved_target_va':'0x1a9324','handler_va':'0x1af1b0'},
      'original_cp_completion':{'constructor_va':'0x5dc82a','u16_header':['0x200d','0x132d',12,'0x8001'],
        'payload_u32_at_8':'incoming R1 saved in R5, never an unconditional status constant',
        'direct_callers':['0x1a9344 immediate nonzero handler error','0x1a9954 downstream event+8 status'],
        'request_forward':{'header':['0x2004','0x0304',12,1],'payload':'request+8 first byte copied',
           'destination':'0x9058003f','return_route_identifier':'0x928407b9','send_failure_result':'0xffffffff'},
        'reply_sender_va':'0x1abecc','ownership':'new reply allocation and copy; sender skips free on send result0, frees on nonzero; request dispatcher reaches free-like routine after handler',
        'primitive_name_limit':'flat-image primitive labels alloc/send/free are interface-pattern inferences; numeric call edges are asserted'},
      'ap_reply_consumer':{'behavior':'copies exactly12B without recv rc/size/header checks, frees reply using own dynamic qid; reads reply+8 u32 and maps it',
        'status_converter_va':'0x20edd1c','explicit_numeric_examples':{hex(k):hex(v) for k,v in mapping.items()},
        'mapping_limit':'numeric branch reconstruction, no private enum names recovered; no unsupported/invalid policy inferred',
        'init_hdmi':'checks mapped status nonzero, logs, sleeps100000us, calls original RET-only0x2167780, returns early; caller run() continues without inspecting an init_hdmi return status'},
      'unclosed':['external0x032d ingress lookup to internal event index0xbb',
        'child service0x9058003f real operation and completion preconditions',
        'complete route FIFO ownership/cancellation semantics and invalid/unsupported enum meanings'],
      'decision':'Do not implement or inject reply this round; original completion provenance proves variable status, not unconditional success.',
      'excluded':['VM run','message reply','shim/shared-source mutation','firmware or binary output','Git/sync']}
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
