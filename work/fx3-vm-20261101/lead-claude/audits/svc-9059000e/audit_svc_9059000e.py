#!/usr/bin/env python3
"""Read-only original-image audit; output restricted to adjacent proof JSON."""
from pathlib import Path
import hashlib, io, json, re, struct, subprocess, sys, plistlib
from capstone import Cs, CS_ARCH_ARM64, CS_ARCH_ARM, CS_MODE_ARM, CS_MODE_THUMB
from elftools.elf.elffile import ELFFile

ROOT=Path('/Volumes/KAFU2T/AI/Projects/Mac')
OUT=Path(__file__).resolve().parent
BASE=ROOT/'work/fx3-vm-20261101/menu-repair-01'
LIB=BASE/'original-uipc/ap-projection/regular-files/usr/lib'
PATHS={'ap':LIB/'appFw.so','cp':ROOT/'work/sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin',
       'df':LIB/'dataflowInfraFramework.so','osal':LIB/'libosal_uipc.so',
       'ko':BASE/'original-uipc/original-modules/osal_uipc.ko',
       'pcie':BASE/'original-uipc/ap-projection/full-v4/regular-files/usr/kmod/pcie-if.ko'}
DATA={k:p.read_bytes() for k,p in PATHS.items()}
ELFS={k:ELFFile(io.BytesIO(v)) for k,v in DATA.items() if k!='cp'}
def read(k,a,n,section=None):
    if k=='cp':
        assert 0x108000<=a and a+n<=len(DATA[k])+0x108000
        return DATA[k][a-0x108000:a-0x108000+n]
    if k in ('ko','pcie'):return ELFS[k].get_section_by_name(section or '.text').data()[a:a+n]
    s=next(s for s in ELFS[k].iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=a and a+n<=s['p_vaddr']+s['p_filesz'])
    off=s['p_offset']+a-s['p_vaddr'];return DATA[k][off:off+n]
def string(k,a,n=400):
    try:return read(k,a,n).split(b'\0')[0].decode('utf8')
    except (StopIteration,UnicodeDecodeError,AssertionError):return None
SYMS={}; RELOCS={}
for k,e in ELFS.items():
    tab=e.get_section_by_name('.symtab' if k in ('ko','pcie') else '.dynsym')
    SYMS[k]={s['st_value']:s.name for s in tab.iter_symbols() if s['st_value'] and s.name}
    RELOCS[k]={}
    if k in ('ko','pcie'):
        sec=e.get_section_by_name('.rela.text')
        for r in sec.iter_relocations():
            s=tab.get_symbol(r['r_info_sym']);RELOCS[k][r['r_offset']]=f"{s.name}+{r['r_addend']:#x}"
    else:
        sec=e.get_section_by_name('.rela.plt');plt=e.get_section_by_name('.plt')
        if sec:
            for j,r in enumerate(sec.iter_relocations()):SYMS[k][plt['sh_addr']+32+j*16]=tab.get_symbol(r['r_info_sym']).name
def dis(k,a,n):
    c=Cs(CS_ARCH_ARM,CS_MODE_THUMB) if k=='cp' else Cs(CS_ARCH_ARM64,CS_MODE_ARM)
    out=[];regs={}
    for i in c.disasm(read(k,a,n),a):
        op=i.mnemonic+' '+i.op_str;r={'va':hex(i.address),'bytes':i.bytes.hex(),'instruction':op}
        m=re.fullmatch(r'adrp x(\d+), #(0x[0-9a-f]+)',op)
        if m:regs[int(m[1])]=int(m[2],16)
        m=re.fullmatch(r'add x(\d+), x(\d+), #(0x[0-9a-f]+)',op)
        if m and int(m[2]) in regs:
            v=regs[int(m[2])]+int(m[3],16);regs[int(m[1])]=v;s=string(k,v)
            if s and all(c.isprintable() or c in '\r\n\t' for c in s):r.update(string_address=hex(v),string=s)
        m=re.fullmatch(r'b[l]? #(0x[0-9a-f]+)',op)
        if m and int(m[1],16) in SYMS.get(k,{}):r['symbol']=SYMS[k][int(m[1],16)]
        if i.address in RELOCS.get(k,{}):r['relocation']=RELOCS[k][i.address]
        out.append(r)
        if i.mnemonic in ('bl','blr','b','br','ret','cbz','cbnz','tbz','tbnz') or i.mnemonic.startswith('b.'):regs.clear()
        elif i.mnemonic not in ('adrp','add'):
            m=re.match(r'x(\d+)(?:,|$)',i.op_str)
            if m:regs.pop(int(m[1]),None)
    return out
def main():
    assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
    if len(sys.argv)>1:
        cmd=sys.argv[1]
        if cmd=='symbols':
            for a,s in SYMS[sys.argv[2]].items():
                if any(x in s for x in sys.argv[3:]):print(hex(a),s)
        elif cmd=='string':
            for a in sys.argv[3:]:print(a,string(sys.argv[2],int(a,16)))
        elif cmd=='find':
            k=sys.argv[2];b=bytes.fromhex(sys.argv[3]);start=0
            while (start:=DATA[k].find(b,start))>=0:
                if k=='cp':print(hex(start+0x108000))
                else:
                    for s in ELFS[k].iter_sections():
                        if s['sh_offset']<=start<s['sh_offset']+s['sh_size']:print(s.name,hex(start-s['sh_offset']+s['sh_addr']))
                start+=1
        else:
            for spec in sys.argv[2:]:
                a,n=(int(x,16) for x in spec.split(':'))
                for r in dis(cmd,a,n):print(r['va'],r['instruction'],r.get('relocation',r.get('symbol',r.get('string',''))))
    else:reconstruct()

PINNED={
 'ap':'545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f',
 'cp':'c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba',
 'df':'5d6a9be3ba359cffb1a1894bb667071e0f0e2fe2749b6c5e36ce8364e57eae2a',
 'osal':'09ebf5980237fc473077dc844763dcb00cba423f431646e3be7c0ca49ea70ff3',
 'ko':'6aa0f5c8c72f5f6cf9aa9c905fc3f3f75b8bea0dfebaf13deb632b0de088eb38',
 'pcie':'26f376a9025f0b56b5ede7ebabdbf5dd8a5235d6627abe2abfd1430e2af578bc',
}
BLOCKS={
 'ap':[(0x2b638b8,0x48),(0x2b66dc8,0xb0),(0x2b66e08,0x870),(0x2b66ba8,0x18),
       (0x2dd1d94,0x40),(0x2df22d8,8),(0x2dd0754,0x40),(0x2debbb4,0x1fc),
       (0x2e109d0,0x154),(0x2e10c80,0xf8),(0x2de7070,0x38),(0x2de5340,0x14),
       (0x2de581c,0x160),(0x2de66f4,0x130),(0x2de83b4,0xb0),
       (0x2dd0054,0x40),(0x2deb504,0x90),(0x2dd0554,0x40),(0x2dd0594,0x40),
       (0x2dd05d4,0x40),(0x2dd0654,0x40),(0x2dd0694,0x40),(0x2dd06d4,0x40),(0x2dd0714,0x40),
       (0x2deb808,0x3ac),(0x2ddfb74,0x40),(0x2eabfd0,0x100),
       (0x2ddfaf4,0x40),(0x2eabcdc,0x210),(0x2b67644,0x38),(0x2b67a60,0x14)],
 'df':[(0x31f58,0x24),(0x32194,0xc),(0x32200,0x10),(0x32278,0x160),
       (0x323d8,0x78),(0x33e50,0x120),(0x33964,0x288),(0x32070,0x124),(0x31358,0x10)],
 'osal':[(0x5e64,0x20c)],
 'ko':[(0x3ba8,0x50),(0x3bf8,0x238)],
 'pcie':[(0x3c70,0x40),(0x34c0,0xfc)],
 'cp':[(0x5f1126,0x3e),(0x5f0fae,0x4e),(0x5f0f3c,0x1e),(0x1e8cc0,0x16a),
       (0x610d8a,0x2a),(0x610db4,0x148),(0x60eb9a,0x62),(0x60ecb8,0x12),
       (0x5f74be,0x44),(0x5f80e2,0x10c),(0x5f75dc,0x40),
       (0x60ed16,0x7a),(0x61103a,0xf2),(0x611858,0x56),
       (0x5ba396,0xda),(0x5ba566,0x28),(0x5ba5e6,6),(0x5bbaa4,0xea),
       (0x5bb858,0x4e),(0x5bb8d0,0x2a),(0x19eb20,0x10),(0x5f2b48,0x50)],
}
CHECKS=[
 ('ap',0x2b66e28,'bl #0x2dd1d94'),('ap',0x2df22d8,'str wzr, [x1]'),('ap',0x2df22dc,'ret '),
 ('ap',0x2b66f28,'bl #0x2dd0754'),('ap',0x2dd077c,'bl #0x2debbb4'),
 ('ap',0x2debbd8,'mov w1, #0x205'),('ap',0x2debbf4,'strb w3, [x29, #0x68]'),
 ('ap',0x2debc48,'mov w3, #0xe'),('ap',0x2debc50,'movk w3, #0x9059, lsl #16'),
 ('ap',0x2debc54,'bl #0x2e109d0'),('ap',0x2debc64,'bl #0x2e10c80'),
 ('ap',0x2debc70,'ldr w0, [x29, #0x58]'),('ap',0x2debcb8,'strb w3, [x29, #0x70]'),
 ('ap',0x2e10a8c,'bl #0x1593c60'),('ap',0x2e10a9c,'bl #0x15926f0'),
 ('ap',0x2e10cc4,'mov w3, #-1'),('ap',0x2e10cc8,'bl #0x1592950'),
 ('ap',0x2e10d70,'bl #0x1593dc0'),('ap',0x2de5940,'mov w20, #0'),
 ('ap',0x2b67674,'bl #0x2b63224'),('ap',0x2b67a6c,'bl #0x2b6353c'),
 ('df',0x32280,'mov w0, #0xa0a0'),('df',0x32284,'movk w0, #0xa0a0, lsl #16'),
 ('df',0x3228c,'str w0, [x1, #4]'),('df',0x3229c,'stp w0, w0, [x1, #0xc]'),
 ('df',0x323ac,'strh w20, [x19, #0xa]'),('df',0x32448,'str w1, [x19, #0x18]'),
 ('df',0x33f1c,'bl #0x30780'),('df',0x33998,'bl #0x30850'),
 ('df',0x33a84,'cmp w2, w1'),('df',0x320e8,'ldr w20, [x19, #0xc]'),
 ('osal',0x5e6c,'ands w23, w0, #0x7fff'),('osal',0x5eb8,'tbz w19, #0xf, #0x6050'),
 ('ko',0x3d78,'tst x19, #0x70000000'),('ko',0x3d84,'ldr x2, [x2, #0x458]'),
 ('ko',0x3d94,'blr x2'),('ko',0x3df8,'mov w0, #0'),('ko',0x3bb8,'str x0, [x1, #0x458]'),
 ('pcie',0x3c94,'bl #0x3c94'),('pcie',0x3c7c,'bl #0x34c0'),
 ('cp',0x5f112e,'movs r1, #0xe'),('cp',0x5f1134,'movt r1, #0x9059'),
 ('cp',0x1e8d44,'mov.w r3, #-1'),('cp',0x1e8d4c,'bl #0x5bb858'),
 ('cp',0x5f80e8,'movw r0, #0x205'),('cp',0x5f814a,'movw r1, #0x1205'),
 ('cp',0x5f8164,'movs r0, #0'),('cp',0x5f8166,'movw r1, #0x1205'),
 ('cp',0x5f816c,'str r0, [sp, #4]'),('cp',0x5f8178,'blx ip'),
 ('cp',0x5f81aa,'movt r0, #0xf033'),('cp',0x60ed52,'strh.w r6, [sp, #4]'),
 ('cp',0x60ed5e,'strh.w r0, [sp, #6]'),('cp',0x611048,'ldr.w ip, [ip, #0x30]'),
 ('cp',0x6110b6,'bl #0x5ba5e6'),('cp',0x5ba428,'str r3, [r4, #0x18]'),
]

def section_block(k,name):
    e=ELFS[k];s=e.get_section_by_name(name);tab=e.get_section_by_name('.symtab')
    rs=e.get_section_by_name('.rela'+name)
    rel={r['r_offset']:{'symbol':tab.get_symbol(r['r_info_sym']).name,'section':tab.get_symbol(r['r_info_sym'])['st_shndx'],'addend':hex(r['r_addend'])} for r in rs.iter_relocations()} if rs else {}
    rows=[]
    for i in Cs(CS_ARCH_ARM64,CS_MODE_ARM).disasm(s.data(),0):
        r={'offset':hex(i.address),'bytes':i.bytes.hex(),'instruction':i.mnemonic+' '+i.op_str}
        if i.address in rel:r['relocation']=rel[i.address]
        rows.append(r)
    return {'section':name,'raw':s.data().hex(),'instructions':rows}

def serial_snapshot(p):
    b=p.read_bytes();lines=b.split(b'\n');selected=set()
    for i,l in enumerate(lines):
        if any(x in l for x in [b'target=0x9059000e',b'Skip snd to 0xe\r',b'FX3_BOOT_GATE_SAMPLE',b'udif_pcie blacklisted',b'FX3_INSMOD_BEGIN_']):
            selected.update(range(max(0,i-1),min(len(lines),i+2)))
        if b'FX3_TASK_SNAPSHOT_327_BEGIN' in l:
            end=next(j for j in range(i+1,len(lines)) if b'FX3_TASK_SNAPSHOT_327_END' in lines[j])
            selected.update(j for j in range(i,end+1) if lines[j].startswith((b'FX3_TASK_',b'Name:',b'State:',b'29 ',b'[<')))
    return {'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),
            'events':[{'line':i+1,'text':lines[i].decode(errors='replace').rstrip('\r')} for i in sorted(selected)],
            'gate_sample_counts':{hex(a):sum(b'pc='+hex(a).encode()+b' ' in s for s in lines if b'FX3_BOOT_GATE_SAMPLE' in s) for a in [0x2b63224,0x2b67674,0x2b60208,0x2b6353c,0x2b634dc]},
            'destination_events':[{'line':i+1,'text':s.decode(errors='replace').rstrip('\r')} for i,s in enumerate(lines) if b'target=0x9059000e' in s]}

def reconstruct():
    files={}
    for k,b in DATA.items():
        h=hashlib.sha256(b).hexdigest();assert h==PINNED[k],(k,h)
        files[k]={'path':str(PATHS[k].relative_to(ROOT)),'sha256':h,'bytes':len(b)}
    checks=[]
    for k,a,expected in CHECKS:
        row=dis(k,a,4)[0];assert row['instruction']==expected,(k,hex(a),row['instruction'],expected)
        checks.append({'image':k,**row})
    blocks={k:[{'start':hex(a),'length':n,'raw':read(k,a,n).hex(),'instructions':dis(k,a,n)} for a,n in spans] for k,spans in BLOCKS.items()}
    seq=dis('ap',0x2b66e08,0x870)
    assert len(seq)==0x870//4 and seq[-1]['va']=='0x2b67674'
    branches=[r for r in seq if re.match(r'^(bl |blr |b |br |b\.|cbz |cbnz |tbz |tbnz )',r['instruction'])]
    assert struct.unpack('<I',read('cp',0xb7ea24+0x10,4))[0]==0x5f80f3
    assert struct.unpack('<I',read('cp',0xb7ea24+0x14,4))[0]==0x5f8159
    assert struct.unpack('<I',read('cp',0xb8113c+0x88,4))[0]==0x60ed17
    assert struct.unpack('<I',read('cp',0xb81b90+0x2c,4))[0]==0x61103b
    assert struct.unpack('<I',read('cp',0xb81b90+0x30,4))[0]==0x611057
    # A software-chosen canonical outer padding of zero is distinguished from
    # the original compiler padding, whose runtime bytes were not captured.
    def envelope(reply_id,body,padding=b'\0'*4):
        return struct.pack('<IIHHII',reply_id,0xa0a0a0a0,1,24+len(body),24,24+len(body))+padding+body
    bodies=[]
    for mode in (0,1):
        body=bytearray(struct.pack('<HHHH',0x2001,0x205,28,1)+bytes(20));body[8]=1;body[16]=mode
        bodies.append({'dfmode':mode,'body_hex':body.hex(),'canonical_zero_padding_52B_hex':envelope(0x81cf61c0,body).hex(),
                       'status':'STATIC_POSSIBILITY_NOT_CAPTURED_REQUEST'})
    body=struct.pack('<HHHHI',0x2001,0x1205,12,1,0)
    reply=envelope(0,body)
    assert len(reply)==36 and body.hex()=='012005120c00010000000000'
    runs=[serial_snapshot(BASE/'runtime/runs'/n/'serial.log') for n in ['ap77agate-f63dd39e','ap70lcd-f61554d9']]
    assert runs[0]['gate_sample_counts']=={'0x2b63224':3,'0x2b67674':0,'0x2b60208':0,'0x2b6353c':0,'0x2b634dc':3}
    aux={}
    for name,p in {'ap77_init':BASE/'runtime/ap77-ui-gate-observe/init-reviewed.sh',
                   'ap77_command':BASE/'runtime/runs/ap77agate-f63dd39e/command.json'}.items():
        b=p.read_bytes();aux[name]={'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(b).hexdigest(),
                                  'bytes':len(b),'text':b.decode()}
    e=ELFS['pcie'];tab=e.get_section_by_name('.symtab')
    pcie_data_relocations=[]
    for r in e.get_section_by_name('.rela.data').iter_relocations():
        s=tab.get_symbol(r['r_info_sym']);idx=s['st_shndx']
        pcie_data_relocations.append({'offset':hex(r['r_offset']),'symbol':s.name,
          'symbol_section':e.get_section(idx).name if isinstance(idx,int) else idx,'symbol_value':hex(s['st_value']),
          'addend':hex(r['r_addend'])})
    assert any(r['offset']=='0xb8' and r['symbol_section']=='.text' and r['addend']=='0x3c70' for r in pcie_data_relocations)
    report={'schema':'fx3-svc-9059000e-static-audit-v1','scope':'Read-only; no QEMU, original execution, camera or runtime modification',
      'files':files,'checks':checks,'blocks':blocks,'sequence_complete_call_and_branch_inventory':branches,
      'sequence_instruction_count':len(seq),'sequence_call_count':sum(r['instruction'].startswith('bl ') for r in seq),
      'sequence_noncall_branch_count':sum(not r['instruction'].startswith('bl ') for r in branches),
      'pcie_init':section_block('pcie','.init.text'),'pcie_data_relocations':pcie_data_relocations,'runs':runs,'auxiliary_sources':aux,
      'original_strings':{k:{hex(a):string(k,a) for a in addrs} for k,addrs in {
          'ap':[0x391a718,0x3919920,0x39687a8],
          'cp':[0xb3dc70,0xb3f2f0,0xb3f410,0xb3f430,0xb3ccc0,0x1e8fec]}.items()},
      'rtti_and_vtables':{hex(a):{'raw':read('cp',a,n).hex(),'u32':[hex(v) for v in struct.unpack('<'+'I'*(n//4),read('cp',a,n))]} for a,n in [(0xb7ea1c,0x2c),(0xb81134,0xa0),(0xb81b88,0x50)]},
      'request':{'destination':'0x9059000e','observed_first_8B_hex':'c061cf81a0a0a0a0','observed_size':None,
                 'statically_constructed_size':52,'body_candidates':bodies,'outer_padding_offsets_20_23':'not written by original AP MakeDataflowHeader; unknown stack bytes',
                 'tag2':'explicit magic 0xa0a0a0a0, never uninitialized padding','full_capture_available':False},
      'reply':{'destination':'request outer reply_id, cross-check OSAL source; AP77 0x81cf61c0',
               'osal_source':'0x9059000e','body_hex':body.hex(),'canonical_zero_padding_36B_hex':reply.hex(),
               'outer_reply_id':0,'outer_padding':'chosen zero; original CP +20..23 not initialized by header builder',
               'original_semantics':'software acknowledgement after attempting to enqueue f033; send return is not checked; not physical display completion'},
      'wait':{'queue':'dynamic reply ID from appFw+2de7070, AP77 0x81cf61c0','timeout_u32':'0xffffffff',
              'dataflow_receive':'appFw+2e10cc8 -> df+33998 -> osal_rcv_msg_tmo',
              'success':'body+8 status32=0 -> 2de581c/2de5940 returns0 -> 2b66f30 branches to 2b66fe0',
              'validation_limit':'wrapper ignores GetMsg return, source and cmd; canonical software peer must still validate exact request and reply'},
      'service':{'AP_transport':'osal_uipc.ko public callback registered by pcie-if.ko, not an ID0xe local receiver',
                 'CP_receiver':'VDF::SubsystemApiExecMgr at0x102dff8 initialized with9059000e by5f1126; Main1e8cc0 receives object+8',
                 'VM_absence':'AP77 init script does not insmod pcie-if.ko; serial original OSAL has NULL public callback; CP processor/service not instantiated',
                 'UI_relationship':'VDF timecode control, not libObj Widget timer1004 or GPE draw/flush'},
      'software_contract':{'status':'NEEDS_EXACT_FULL_REQUEST_CAPTURE_BEFORE_ALLOWLIST_ACTIVATION',
                'acceptance':'whitelist one captured destination/op/52B/OSAL-source/entire request; reject others; no unsolicited reply or forced task completion',
                'implementation':'existing preload send dispatch can consume original request exactly once and allocate36B reply to its live reply queue; kernel public callback registration is not required for interception',
                'physical_transport_alternative':'pcie-if needs real CP/PCIe/DMA infrastructure; do not insmod merely to silence missing callback'},
      'unknowns':['AP77 request full52B including dfmode and outer padding were not logged',
                  'exact CP global queue creation/registration routine upstream of VDF Main not closed; CP consumer and AP forwarding registrar are independently closed',
                  'future VDF/TP requests and getfunc/barrier after this reply require runtime receipts',
                  'No physical timecode, menu, image, audio or camera acceptance']}
    init=report['pcie_init']['instructions']
    assert next(r for r in init if r['offset']=='0x20')['relocation']['symbol']=='pcieif_reg_public'
    assert next(r for r in dis('pcie',0x3c94,4))['relocation']=='osal_reg_public+0x0'
    assert OUT==ROOT/'work/fx3-vm-20261101/lead-claude/audits/svc-9059000e'
    OUT.joinpath('svc-9059000e-proof.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(f"PASS: {len(files)} original hashes, {len(checks)} exact instructions, {len(seq)} sequence instructions, {len(branches)} call/branch edges; proof rebuilt")

if __name__=='__main__':main()
