#!/usr/bin/env python3
"""Read original FX3 bytes/logs; only write adjacent vdf0146-proof.json.
No emulation, guest API, runtime mutation, lock acquisition or hardware access.
"""
from pathlib import Path
import hashlib, json, struct, sys, subprocess, plistlib, re, copy
from capstone import Cs, CS_ARCH_ARM64, CS_ARCH_ARM, CS_MODE_THUMB
from elftools.elf.elffile import ELFFile
sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
ROOT = next(p for p in OUT.parents if p.name == 'Mac' and (p/'README.md').is_file())
TASK = ROOT/'work/fx3-vm-20261101'
RUNTIME = TASK/'menu-repair-01/runtime'
AP = TASK/'menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/appFw.so'
CP = ROOT/'work/sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin'
PTHREAD = AP.parents[2]/'lib/libpthread-2.25.so'
BACKUP = TASK/'menu-repair-01/original-uipc/original-modules/backup.ko'
HASHES = {'AP': '545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f',
          'CP': 'c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba'}
REQUEST = bytes.fromhex('0d2046010a0001800100')
REPLY = bytes.fromhex('0d2046110c00018000005900')
DATA = {'AP': AP.read_bytes(), 'CP': CP.read_bytes()}
DATA['PT']=PTHREAD.read_bytes();DATA['BK']=BACKUP.read_bytes()
with BACKUP.open('rb') as f:
    bkelf=ELFFile(f);BKOFF=bkelf.get_section_by_name('.text')['sh_offset']
    bksym=bkelf.get_section_by_name('.symtab')
    BKRELOCS={r['r_offset']:bksym.get_symbol(r['r_info_sym']).name for r in bkelf.get_section_by_name('.rela.text').iter_relocations()}
with AP.open('rb') as f:
    elf = ELFFile(f)
    LOADS = [(s['p_vaddr'], s['p_offset'], s['p_filesz']) for s in elf.iter_segments() if s['p_type'] == 'PT_LOAD']
    plt = elf.get_section_by_name('.plt')['sh_addr']
    rela = elf.get_section_by_name('.rela.plt'); syms = elf.get_section(rela['sh_link'])
    IMPORTS = {plt+32+16*i: syms.get_symbol(r['r_info_sym']).name for i,r in enumerate(rela.iter_relocations())}
    RELOCS = {r['r_offset']: dict(r.entry) for r in elf.get_section_by_name('.rela.dyn').iter_relocations()}

def off(k, v):
    if k == 'CP': return v-0x108000
    if k == 'PT': return v # original pthread PT_LOAD: this bounded text VA == offset
    if k == 'BK': return BKOFF+v # ET_REL .text offset, NOT runtime VA
    return next(o+v-b for b,o,n in LOADS if b <= v < b+n)
def raw(k, v, n):
    o=off(k,v); out=DATA[k][o:o+n]; assert len(out)==n
    return out
def dis(k, v, n):
    cs=Cs(CS_ARCH_ARM,CS_MODE_THUMB) if k=='CP' else Cs(CS_ARCH_ARM64,0)
    return [{'va':hex(i.address),'bytes':i.bytes.hex(),'instruction':i.mnemonic+' '+i.op_str}
            for i in cs.disasm(raw(k,v,n),v)]
def cstr(k,v):
    o=off(k,v); b=DATA[k]; return b[o:b.index(b'\0',o)].decode()
def u32(v): return struct.unpack('<I',raw('CP',v,4))[0]
def u64(v): return struct.unpack('<Q',raw('AP',v,8))[0]
def rtti(name):
    b=DATA['CP']; va=b.index(name.encode()+b'\0')+0x108000
    ti=b.index(struct.pack('<I',va))+0x108000-4
    vt=b.index(struct.pack('<I',ti))+0x108000+4
    return {'name':name,'name_va':hex(va),'typeinfo':hex(ti),'vtable':hex(vt),
            'slots':{hex(i):hex(u32(vt+i)) for i in range(0,24,4)}}

BLOCKS = {'AP': [(0x2d9e6c8,0x270),(0x2dd0194,0x40),(0x2deaa78,0x80),
 (0x2de70a8,0x2a0),(0x2de4574,0x2a0),(0x2ebf3b0,0x9c),
 (0x2ddfb34,0x40),(0x2eabe58,0x178),(0x2eace78,0xa0),(0x2eacdb0,0xc8),
 (0x2c4b004,0x170),(0x2c4b174,0x164),(0x2d9e938,0x3c),
 (0x2bd7604,0x1ac),(0x1724ccc,0x24),(0x2bd1ecc,0x160),
 (0x16f2150,0x9c),(0x16f2450,0x50),(0x16f25ec,0x68),
 (0x2f6e00c,0x54),(0x2bd2d34,0xa0),
 (0x2b72754,0x1a0),(0x2b725c8,0x170),(0x2b728f4,0x16c),
 (0x2b04674,0x1a0),(0x2b2378c,0x9c),(0x2ebf650,0x34),
 (0x27395e8,0x50),(0x2191748,0x14)],
 'CP': [(0x1ac9ee,0x1a),(0x1acdfc,6),(0x1ad050,0x24),
 (0x1ab68c,0x1a),(0x1ab978,0x2a),(0x1a1b9c,0x128),
 (0x5f5e98,0x5e),(0x5f5ef6,0x6e),(0x1e8298,0x64),
 (0x60765a,0x7c),(0x6103f6,0xa),(0x60ef4c,6),(0x60c658,4),
 (0x5df21c,0x3e),(0x60c736,0xea),
 (0x1ad9ca,0x18),(0x1adaee,6),(0x1adb84,0x34),
 (0x1adbd4,0x118),(0x1ac4b8,0x16),(0x1ac67e,0xc),
 (0x5c9a06,0x52),(0x1aef1c,0x68)],
 'PT':[(0xd4d8,0x120)],'BK':[(0x2ba8,0xec),(0x3010,0x110),(0x11c0,0x140)]}
CHECKS = [
 ('AP',0x2d9e708,'ldrb w0, [x21, #0x1b9]'),('AP',0x2d9e714,'b.eq #0x2d9e79c'),
 ('AP',0x2d9e72c,'bl #0x2ddfb34'),('AP',0x2d9e760,'bl #0x2dd0194'),
 ('AP',0x2d9e768,'cbnz w0, #0x2d9e88c'),('AP',0x2d9e780,'bl #0x2f6ff0c'),
 ('AP',0x2d9e7ac,'ret '),('AP',0x2d9e884,'bl #0x2ebf3b0'),
 ('AP',0x2dd01bc,'bl #0x2deaa78'),('AP',0x2deaa94,'strh wzr, [x29, #0x28]'),
 ('AP',0x2deaa9c,'mov w1, #0x146'),('AP',0x2deaab8,'strb w0, [x29, #0x28]'),
 ('AP',0x2deaac8,'mov w4, #0xc'),('AP',0x2deaadc,'bl #0x2de70a8'),
 ('AP',0x2deaae0,'ldr w0, [x29, #0x38]'),('AP',0x2deaae4,'bl #0x2de4574'),
 ('AP',0x2de72fc,'mov w2, #-1'),('AP',0x2de7300,'bl #0x1592de0'),
 ('AP',0x2de7314,'bl #0x1591c40'),('AP',0x2de7320,'bl #0x15943d0'),
 ('AP',0x2de46c4,'cmp w0, #0x590, lsl #12'),('AP',0x2de46cc,'mov w19, #0'),
 ('AP',0x2eabebc,'bl #0x2eace78'),('AP',0x2eacea0,'bl #0x1592f10'),
 ('AP',0x2eabfc8,'str wzr, [x22]'),('AP',0x2c4b048,'strb w0, [x20, #0x1ba]'),
 ('AP',0x2c4b07c,'strb w0, [x20, #0x1b9]'),('AP',0x2bd76c8,'bl #0x1724ccc'),
 ('AP',0x2bd76f8,'blr x1'),('AP',0x2bd7754,'bl #0x2bd1ecc'),
 ('AP',0x2bd7788,'b #0x2bd763c'),('AP',0x2bd1f04,'ldr x20, [x21, #0x158]'),
 ('AP',0x16f247c,'cmp w0, #2'),('AP',0x16f2488,'cbnz w0, #0x16f25ec'),
 ('AP',0x2f6e050,'bl #0x2bd2d34'),
 ('CP',0x1acdfc,'movs r0, #0x90'),('CP',0x1ab97c,'bl #0x1a1b9c'),
 ('CP',0x1ab99c,'bl #0x5c9a06'),
 ('CP',0x1a1bc2,'movt r0, #0x321'),('CP',0x1a1c00,'ldrb r3, [r5, #8]'),
 ('CP',0x1a1c32,'strb.w r5, [sp, #0x138]'),('CP',0x1a1c60,'bl #0x5daac2'),
 ('CP',0x5f5e9e,'movw r0, #0x321'),('CP',0x5f5ed0,'cmp r0, #1'),
 ('CP',0x5f5ed8,'movs r0, #1'),('CP',0x5f5ee8,'blx ip'),
 ('CP',0x5f5eec,'bl #0x5f5ef6'),('CP',0x5f5f18,'movt r0, #0xf02f'),
 ('CP',0x5f5f5a,'bl #0x1e8298'),('CP',0x607660,'movw r0, #0xf02f'),
 ('CP',0x607698,'ldr.w r2, [r0, #0x7d0]'),('CP',0x6076ac,'beq #0x6076d0'),
 ('CP',0x6076c4,'bl #0x60c658'),('CP',0x6076cc,'bl #0x60c736'),
 ('CP',0x6103fc,'strb r1, [r0, r2]'),('CP',0x1ad9ca,'movw r1, #0x1321'),
 ('CP',0x1adaee,'movw ip, #0x28b'),('CP',0x1adcc4,'ldr r0, [r0, #8]'),
 ('CP',0x1adcda,'mov.w r2, #0x590000'),('CP',0x1adcde,'orrs r0, r2'),
 ('CP',0x1ac684,'bl #0x5c9a06'),('CP',0x5c9a24,'movw r0, #0x1146'),
 ('CP',0x5c9a46,'str r5, [sp, #0xc]'),('CP',0x5c9a4c,'bl #0x1aef1c'),
 ('AP',0x2b046f8,'bl #0x1592d30'),('AP',0x2b047cc,'bl #0x1592d30'),
 ('AP',0x2b237f8,'bl #0x1593f80'),('AP',0x2739620,'bl #0x2b04738'),
 ('AP',0x2191754,'bl #0x27395e8'),('AP',0x2ebf660,'bl #0x1592760'),
 ('PT',0xd54c,'add x19, x20, #0x28'),('PT',0xd558,'add x19, x19, x22'),
 ('PT',0xd5ec,'svc #0'),('PT',0xd5f0,'cmn x0, #1, lsl #12'),
 ('BK',0x2bd8,'mov w2, #0x30'),('BK',0x2be0,'bl #0x11c0')]

def accept(packet, state, *, destination, source, lease_source, generation,
           profile, owned=True, alloc_ok=True, send_ok=True):
    """Finite illustrative software config contract; NOT installed transport."""
    if (packet!=REQUEST or destination!=0x92840747 or not source or
        source!=lease_source or not owned or generation<=0 or
        profile!='headless_touch_config' or not alloc_ok or not send_ok or
        generation in state.get('completed',[])):
        raise ValueError('outside captured transaction/config contract')
    staged={'desired_touch_panel':1,'software_config_accepted':True,
            'physical_touch_verified':False,'pending_hardware':True,
            'original_device_f02f_executed':False,'generation':generation}
    state['touch_panel']=staged
    state.setdefault('completed',[]).append(generation)
    return REPLY

def build():
    vol=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
    assert vol['VolumeUUID'].upper()=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
    proof={'scope':'static original bytes and saved runtime only; no QEMU, original CP execution or runtime installation',
           'volume_uuid':vol['VolumeUUID'],'sources':{},'code':{},'instruction_checks':[]}
    def source(p,limit=None):
        b=p.read_bytes(); b=b if limit is None else b[:limit]
        proof['sources'][str(p.relative_to(ROOT))]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),
          'scope':'whole saved file' if limit is None else 'frozen prefix; later bytes excluded'}
        return b
    for k,p in [('AP',AP),('CP',CP),('PT',PTHREAD),('BK',BACKUP)]:
        want=HASHES.get(k,{'PT':'7394f861930c45dd5076a700da5755faf0f6bed08544b0d60eadb85a14a7d592',
                         'BK':'8a8d8c949699c130c116d0006806d8b7f92b20869c92a72876529a2001d60c4d'}.get(k))
        assert hashlib.sha256(source(p)).hexdigest()==want
        proof['code'][k]={hex(v):{'file_offset':hex(off(k,v)),'bytes':raw(k,v,n).hex(),
          'disassembly':dis(k,v,n),'note':'bounded original window; Thumb literal data is not independent control-flow evidence'} for v,n in BLOCKS[k]}
    for k,v,want in CHECKS:
        item=dis(k,v,4)[0]; assert item['instruction']==want,(k,hex(v),item,want)
        proof['instruction_checks'].append({'binary':k,**item})
    proof['imports']={hex(v):IMPORTS[v] for v in (0x1592de0,0x1591c40,0x15943d0,0x1592f10,0x1594030,
        0x1592d30,0x1593f80,0x1592760,0x15936e0)}
    assert proof['imports']['0x1594030']=='pthread_mutex_unlock'
    proof['tables']=[]
    for name,base,index,want in [('wire146',0x1aca08,0x146-0x100,0x1acdfc),
        ('internal90',0x1ab6a6,0x90-0x1f,0x1ab978),('reply28b',0x1ac4ce,0x28b-0x225,0x1ac67e)]:
        slot=base+2*index; value=struct.unpack('<H',raw('CP',slot,2))[0]; target=base+2*value
        assert target==want
        proof['tables'].append({'name':name,'base':hex(base),'index':index,'slot':hex(slot),
                                'raw':raw('CP',slot,2).hex(),'target':hex(target)})
    proof['classes']=[rtti(n) for n in ['N3VDF24VdfInputCmdSetTouchPanelE','N3VDF24DevPanelCmdSetTouchPanelE']]
    assert proof['classes'][0]['slots']['0x14']=='0x5f5ebb'
    assert proof['classes'][1]['slots']['0x14']=='0x60767d'
    proof['subsystem_slots']={hex(x):{'slot':hex(0xb8120c+x),'target':hex(u32(0xb8120c+x))} for x in [0x7d0,0xe4]}
    assert u32(0xb819dc)==0x6103f7
    proof['selector_routing']=[{'mask':hex(u32(0xb81088+8*i)),'queue':hex(u32(0xb8108c+8*i))} for i in range(5)]
    # AArch64 data VAs are not file offsets after the second PT_LOAD.
    assert u64(0x47977b8)==0x46f17d8 and u64(0x46f17f8)==0x2d9e6c8
    assert RELOCS[0x47977b8]['r_addend']==0x46f17d8
    proof['AP_vtable']={'GOT':'0x47977b8','relocation':RELOCS[0x47977b8],
      'vtable_header':'0x46f17d8','run_slot':'0x46f17f8','run':'0x2d9e6c8',
      'header_bytes':raw('AP',0x46f17d8,0x30).hex(),
      'warning':'Use ELF PT_LOAD translation; data VA differs from file offset by 0x10000 here'}
    proof['strings']={'AP':{hex(v):cstr('AP',v) for v in [0x3957260,0x39572c9,0x3957340,
      0x3957283,0x39572a6,0x39572ef,0x3957314,
      0x3908530,0x3908568,0x3908898,0x3908928]}}
    proof['backup_relocations']={hex(v):n for v,n in BKRELOCS.items() if 0x2ba8<=v<0x2ca0 or 0x3010<=v<0x3120}
    proof['sequence_calls']=[i for i in dis('AP',0x2d9e6c8,0x270) if i['instruction'].startswith(('bl ','blr '))]
    proof['sequence_success_tail_calls']=[i for i in dis('AP',0x2d9e76c,0x44) if i['instruction'].startswith(('bl ','blr '))]
    assert [i['instruction'] for i in proof['sequence_success_tail_calls']]==['bl #0x2f6ff0c','bl #0x2f6ff74']
    proof['wire']={'request_hex':REQUEST.hex(),'request_length':10,'payload':{'8':'ON=1','9':'AP zeroed reserved'},
      'legacy_request_hex':'012021030c00010001000000','device_request_hex':'01202ff00c00010001000000',
      'legacy_reply':'2001/1321/12B/status@8;0 for payload byte0<=1,1 otherwise',
      'reply_hex':REPLY.hex(),'reply_command':'0x1146','reply_length':12,'reply_status':'0x590000',
      'invalid_legacy_status1_reply_hex':'0d2046110c00018001005900',
      'bridge_send_failure_hex':'0d2046110c000180ffffffff',
      'semantics':'Original Execute emits1321 before f02f. Acceptance is not physical touch completion.'}
    # Freeze existing runtime files; do not run any helper or request live memory.
    manifests=[('ap99r2cpdate600-9391e358',10468934,'7d9e1c85022bd4b20926af19eabc32fd9e505fc4012bcc380befb431dcae36ea'),
      ('ap98datecapture600-b6f825f4',59304909,'15fd1fb8118b5b229223aa1e2346b370745ba07efd022f606ef2f0ac7ea0179a')]
    proof['runtime']={}
    for name,size,sha in manifests:
        p=RUNTIME/'runs'/name/'serial.log';b=source(p,size);assert hashlib.sha256(b).hexdigest()==sha
        lines=b.split(b'\n')
        tags=[b'FX3_DATE98_SYNC phase=',b'raw=0d204601',b'FX3_UIPC_RECV_BEGIN tid=424',
              b'FX3_BOOT_CV_RETURN',b'FX3_BACKUP99_WRITE',b'FX3_BACKUP99_READBACK',
              b'FX3_UI_CONFIG_',b'FX3_UI_GATE_SAMPLE id=5 ',b'FX3_UI_GATE_SAMPLE id=6 ',
              b'FX3_UI_GATE_SAMPLE id=10 ',b'FX3_UI_GATE_SAMPLE id=11 ']
        hits=[{'LF':i+1,'text':x.decode(errors='replace')} for i,x in enumerate(lines) if any(t in x for t in tags)]
        markers={t.decode():sum(t in x for x in lines) for t in [b'FX3_GPE_NATIVE_TARGET',b'raw=0d204611',b'FX3_UI_CONFIG_ENTER']}
        proof['runtime'][name]={'LF_segments':len(lines),'evidence':hits,'marker_counts':markers,
          'limits':'Bounded/deduplicated observers; marker absence is not a lossless global absence proof.'}
        if name.startswith('ap99'):
            i=next(i for i,x in enumerate(lines) if b'FX3_PROVIDER_REQUEST ' in x and b'raw='+REQUEST.hex().encode() in x)
            assert i+1==14411
            proof['runtime'][name]['request_stack']=[{'LF':j+1,'text':lines[j].decode(errors='replace')} for j in range(14398,14415)]
            frames=[int(re.search(rb'relative=(0x[0-9a-f]+)',x).group(1),16) for x in lines[14398:14409] if b'FX3_PROFILE_FRAME' in x]
            assert frames[:6]==[0x2de7264,0x2deaae0,0x2dd01c0,0x2d9e764,0x2bd76fc,0x2f71ba0]
            daemon=[]
            for j,line in enumerate(lines):
                if b'FX3_TASK_SNAPSHOT_528_BEGIN' in line:
                    end=next(q for q in range(j+1,len(lines)) if b'FX3_TASK_SNAPSHOT_528_END' in lines[q])
                    daemon.append([{'LF':q+1,'text':lines[q].decode(errors='replace')} for q in range(j,end+1)])
            assert len(daemon)==3
            assert all('backup_get_cp_data' in '\n'.join(x['text'] for x in block) for block in daemon)
            proof['backup_daemon_snapshots']=daemon
        else:
            first=next(i for i,x in enumerate(lines) if b'FX3_GPE_NATIVE_TARGET' in x)
            proof['runtime'][name]['first_native_target_context']=[{'LF':j+1,'text':lines[j].decode(errors='replace')} for j in range(first-6,first+3)]
    snap=RUNTIME/'ap99r2cpdate600-9391e358-no-frame-task-snapshots.json'
    snapshots=json.loads(source(snap))
    selected=[{k:x[k] for k in ['tid','name','LF','syscall','stack']} for x in snapshots if x['name'] in ['AppFw','SeqQueueCommon']]
    proof['task_snapshots']=selected
    assert len(selected)==6
    assert all('0x7edbde4a88' in x['syscall'][0] for x in selected if x['name']=='AppFw')
    assert all('osal_rcv_msg_tmo' in '\n'.join(x['stack']) for x in selected if x['name']=='SeqQueueCommon')
    log99=RUNTIME/'runs/ap99r2cpdate600-9391e358/serial.log'
    loglines=log99.read_bytes()[:10468934].split(b'\n')
    appframe=next(x for x in loglines[14398:14409] if b'FX3_PROFILE_FRAME depth=0 ' in x)
    ptframe=next(x for x in loglines[14398:14409] if b'module=/lib/libpthread.so.0 ' in x)
    def framebase(line):
        lr=int(re.search(rb'lr=(0x[0-9a-f]+)',line).group(1),16)
        relative=int(re.search(rb'relative=(0x[0-9a-f]+)',line).group(1),16)
        return lr-relative
    appbase,ptbase=framebase(appframe),framebase(ptframe)
    assert appbase==0x7ed2fb3000 and ptbase==0x7f85192000
    syscall=next(x['syscall'][0] for x in selected if x['name']=='AppFw').split()
    futexaddr,syscallpc=int(syscall[1],16),int(syscall[-1],16)
    assert syscallpc-ptbase==0xd5f0 and futexaddr-appbase==0x8e31a60+0x28
    with PTHREAD.open('rb') as f:
        ptelf=ELFFile(f)
        ptsym=next(s for s in ptelf.get_section_by_name('.dynsym').iter_symbols() if s.name=='pthread_cond_wait')
        assert ptsym['st_value']==0xd4d8 and ptsym['st_size']==0x2ec
    proof['UI_wait_address_binding']={'app_base_from_original_frame':hex(appbase),
      'pthread_base_from_original_frame':hex(ptbase),'observed_syscall_pc':hex(syscallpc),
      'relative_PC':hex(syscallpc-ptbase),'pthread_symbol':'pthread_cond_wait@d4d8,size2ec',
      'futex_address':hex(futexaddr),'relative_futex':hex(futexaddr-appbase),
      'original_model_setting_value_CV':'0x8e31a60','pthread_group0_futex_offset':'0x28',
      'grade':'B-strong object/callchain inference; exact AppFw user LR not saved'}
    kw={'destination':0x92840747,'source':0x81cf61c3,'lease_source':0x81cf61c3,
        'generation':1,'profile':'headless_touch_config'}
    state={};assert accept(REQUEST,state,**kw)==REPLY
    cases=[]
    for i in range(10):
        b=bytearray(REQUEST);b[i]^=1;cases.append((f'changed_byte_{i}',bytes(b),{}))
    cases += [('truncated',REQUEST[:-1],{}),('appended',REQUEST+b'\0',{}),
      ('wrong_destination',REQUEST,{'destination':0x92840748}),('no_source',REQUEST,{'source':0}),
      ('source_mismatch',REQUEST,{'lease_source':0x81cf61c2}),('no_owner',REQUEST,{'owned':False}),
      ('wrong_profile',REQUEST,{'profile':'physical_touch'}),('allocation_failure',REQUEST,{'alloc_ok':False}),
      ('send_failure',REQUEST,{'send_ok':False}),('replay',REQUEST,{}),('invalid_generation',REQUEST,{'generation':0})]
    rejects=[]
    for name,packet,override in cases:
        tmp=copy.deepcopy(state);before=copy.deepcopy(tmp)
        # Distinct generation isolates non-replay validation and failure paths.
        params=kw|({'generation':2} if name!='replay' else {})|override
        try: accept(packet,tmp,**params)
        except ValueError: assert tmp==before;rejects.append(name)
        else: raise AssertionError(name)
    again=copy.deepcopy(state);assert accept(REQUEST,again,**(kw|{'generation':2}))==REPLY
    proof['software_contract']={'profile':'headless_touch_config','state_after_accept':state,
      'second_distinct_transaction_accepts_identical_request':again,'reject_cases':rejects,
      'obligations':['Stage actual config; allocate independent reply; commit after actual send success; rollback/free own reply on failure',
      'Use current request source and unique allocation/lease/generation; captured source is evidence only',
      'Never free caller request twice; AP frees delivered reply naturally at2de7320',
      'Do not synthesize hardware completion, touch samples, Common task completion or UI readiness']}
    proof['ordered_sync_inventory']=[
      {'order':0,'scope':'boot force clock option1 before current task','request':'80900141/32B native sync',
       'status':'AP99 LF14294 actual in-place status0/result0; not a new12B packet',
       'followup':'force1098=1 (not UI clear), LF14306 and LF14421..14427'},
      {'order':1,'scope':'sequence_set_touch_panel first action','request':'807b002b/12B op1 body010000000c00000001000000',
       'wait':'NO_WAIT;2eacea0 osal_snd_msg; no reply to inject'},
      {'order':2,'scope':'same sequence second action','request':REQUEST.hex(),'reply':REPLY.hex(),'wait':'infinite'},
      {'order':3,'scope':'same sequence success tail','request':None,'status':'CLOSED EMPTY SET; only logging/return at2d9e76c..7ac'},
      {'order':4,'scope':'completion observers and remaining Common queue','request':'UNRESOLVED dynamic heap/vtable list',
       'reply':None,'required_capture':'queue pointer/10 node chain/20 count/88 active;task158/160 observers; task vptr and original inputs'},
      {'order':5,'scope':'first manual date setting later, if dequeued','request':'80900141/32B native sync from2b72680 (option0), or2b72988(option2)',
       'reply':'in-place signed16 status0 plus original transport/free/model0; actual date/timezone/reason handshake required',
       'status':'Conditional future task; NOT proved to be immediate next queue node; exact body/order unresolved'}]
    proof['ordered_sync_inventory'].append({'order':'concurrent, after date change; no total order relative to146',
      'scope':'AppFw waits Backup daemon, not a new Common run request',
      'request':'Backup_sync_subsystem(2cf)/Backup_sync_all -> backup_get_cp_data -> CP Backup op0x30 via11c0',
      'status':'AP99 actual daemon stack saved3 times; body/dynamic source/reply and CP semantics UNRESOLVED',
      'reply':None,'must_not':'Never send a guessed zero ACK: original CP snapshot transfer/storage and return checks matter'})
    proof['UI_causality']={'proved':['AP98 paints despite Common date sync never returning; Common queue drain is not a universal prerequisite',
      'AP99 boot CV returned before current request; only one config update observed and AppFw later sleeps on futex7edbde4a88',
      'Sequence dispatcher unlocks queue before run at2bd76c8; no proof146 holds the queue mutex across receive',
      'Original pthread d5f0 is pthread_cond_wait; futex address uses condvar+28+group*4',
      'AppFw futex minus original app base is8e31a88=condition_variable8e31a60+28',
      'Original model_setting_value sync wait/notify uses8e31a60; AppBackupDaemon simultaneously waits Backup_sync_all/get_cp_data'],
      'strong_inference':'UI is waiting Backup synchronization after new date/force updates; Common146 is an independent stall. Exact user LR/caller and daemon command13 vs14 are not captured.',
      'unresolved':['Exact AppFw user stack and whether sync_and_wait_comp or execute_sync_all_if_necessary called it',
      'Full dynamically queued Common tasks/inputs and their requests through first setup',
      'Causal effect of answering146 on first drawing; original touch reply alone makes no UI claim']}
    assert 0x7edbde4a88-0x7ed2fb3000==0x8e31a60+0x28
    proof['unproven']=['No CP/device execution or physical touch/display/live-view acceptance',
      'No actual1146 consumption, sequence return, next-queue snapshot or original first frame in AP99',
      'Exact UI caller and CP Backup get_data completion plus complete later synchronous inventory remain open',
      'Transport cancellation/correlation and real allocation/send/concurrency fault tests not run']
    return proof

def main():
    if len(sys.argv)>1 and sys.argv[1]=='dis':
        k,v,n=sys.argv[2:];print(json.dumps(dis(k.upper(),int(v,16),int(n,16)),indent=2));return
    p=build();encoded=json.dumps(p,ensure_ascii=False,indent=2)+'\n';target=OUT/'vdf0146-proof.json'
    if '--check' in sys.argv: assert target.read_text()==encoded; verb='matches'
    else: target.write_text(encoded);verb='rebuilt'
    print(f'PASS {len(CHECKS)} instruction checks,3 TBH mappings,2 RTTI classes,2 saved logs,6 task snapshots,'
          f'{len(p["software_contract"]["reject_cases"])} rejected cases; {target.name} {verb}; UI Backup wait B-strong, next queue OPEN')
if __name__=='__main__': main()
