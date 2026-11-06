#!/usr/bin/env python3
"""Read-only FX3 VDF0152 audit; writes only its adjacent proof. No guest execution."""
from pathlib import Path
import hashlib, json, struct, sys, re, subprocess, plistlib
from capstone import Cs, CS_ARCH_ARM64, CS_ARCH_ARM, CS_MODE_THUMB
from elftools.elf.elffile import ELFFile
sys.dont_write_bytecode = True
OUT=Path(__file__).resolve().parent
ROOT=next(p for p in OUT.parents if p.name=='Mac' and (p/'README.md').is_file())
TASK=ROOT/'work/fx3-vm-20261101'
AP=TASK/'menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/appFw.so'
CP=ROOT/'work/sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin'
a,b=AP.read_bytes(),CP.read_bytes()
with AP.open('rb') as f:
    elf=ELFFile(f)
    loads=[(s['p_vaddr'],s['p_offset'],s['p_filesz']) for s in elf.iter_segments() if s['p_type']=='PT_LOAD']
    plt=elf.get_section_by_name('.plt')['sh_addr'];rela=elf.get_section_by_name('.rela.plt');syms=elf.get_section(rela['sh_link'])
    imports={plt+32+16*i:syms.get_symbol(r['r_info_sym']).name for i,r in enumerate(rela.iter_relocations())}
def offset(v):return next(o+v-x for x,o,n in loads if x<=v<x+n)
def raw(k,v,n):
    d,o=(a,offset(v)) if k=='AP' else (b,v-0x108000)
    return d[o:o+n]
def dis(k,v,n):
    cs=Cs(CS_ARCH_ARM64,0) if k=='AP' else Cs(CS_ARCH_ARM,CS_MODE_THUMB)
    return [{'va':hex(i.address),'bytes':i.bytes.hex(),'instruction':i.mnemonic+' '+i.op_str} for i in cs.disasm(raw(k,v,n),v)]
def u32(v):return struct.unpack('<I',raw('CP',v,4))[0]
def cstr(k,v):
    d,o=(a,offset(v)) if k=='AP' else (b,v-0x108000)
    return d[o:d.index(b'\0',o)].decode(errors='replace')
def rtti(name):
    pos=b.index(name.encode()+b'\0');ti=b.index(struct.pack('<I',pos+0x108000))+0x108000-4
    vt=b.index(struct.pack('<I',ti))+0x108000+4
    return {'name_va':hex(pos+0x108000),'name':name,'typeinfo':hex(ti),'vtable':hex(vt),'slots':{hex(i):hex(u32(vt+i)) for i in range(0,24,4)}}
REQUEST=bytes.fromhex('0d205201100001800300010000eb8080')
REPLY=bytes.fromhex('0d2052110c00018000005900')
LOG_SNAPSHOTS={'ap83ar4face-4cd8574a': {'prefix_bytes': 5806839, 'prefix_sha256': '3ff35ff9044ab8949906a8967b75ce3f7b68fdd52d2de592bd13d85dc4d932e0'}, 'ap84amttcg-953a9d56': {'prefix_bytes': 5579408, 'prefix_sha256': 'f7539016c59ca9fab3b3dda11eaf72a8aa7bfbf7b902f3b8518daf34fe4b68ae'}, 'ap84ar2native-4b70eab2': {'prefix_bytes': 5692947, 'prefix_sha256': '079b672fe641451a54b8aecbbcf3870b7b02a5f721cf24eecbc95b696217d705'}, 'ap84bicount0-b2028788': {'prefix_bytes': 2365594, 'prefix_sha256': '940214a7539204d86c746380b9f05b6d012aec9be30281a2ac52653ce4e48e42'}}
AP_BLOCKS=[(0x2d95948,0x200),(0x2dcfc94,0x40),(0x2de9de4,0x3f4),
 (0x2de7070,0x38),(0x2de70a8,0x2a0),(0x2de4574,0x2a0),(0x2ebf3b0,0x9c)]
CP_BLOCKS=[(0x1ac9ee,0x1a),(0x1ace44,6),(0x1ad052,0x26),
 (0x1ab68c,0x1a),(0x1abb60,0x26),(0x1b5280,0x1b0),
 (0x5f7ee4,0x1f6),(0x1e8298,0x68),(0x1e80f4,0x10c),
 (0x5ff8b0,0x110),(0x60fbd8,0x6e),(0x60ee36,6),(0x60fd8e,0xa),
 (0x5f8b6c,0x46),(0x60f7c8,0x52),(0x1df39c,0x4e),(0x1df3ec,0x3c),
 (0x1e0e5c,0x96),(0x1e0ef4,0x46),(0x1e10f0,0x60),
 (0x60cabc,0x24),(0x60cae0,0x24),(0x60cd22,0x24),
 (0xa5e3f2,0x38),(0xa66770,0x18),(0xa5e17a,0x3a),
 (0x1ad6fc,0x5a),(0x1ada60,0xe),(0x1adb84,0x34),
 (0x1adbd4,0xc6),(0x1adca8,0x3e),(0x1ac4b8,0x16),
 (0x1ac714,0xc),(0x5c9b4e,0x52),(0x1aef1c,0x68)]
CHECKS=[('AP',0x2d95a14,'bl #0x2dcfc94'),('AP',0x2d95a1c,'cbnz w0, #0x2d95a70'),
 ('AP',0x2dcfcbc,'bl #0x2de9de4'),('AP',0x2de9e08,'mov w0, #0x152'),
 ('AP',0x2de9e24,'mov w0, #3'),('AP',0x2dea074,'strb wzr, [x29, #0x5c]'),
 ('AP',0x2dea0e0,'bl #0x2de70a8'),('AP',0x2dea0e8,'bl #0x2de4574'),
 ('AP',0x2dea0cc,'mov w4, #0xc'),('AP',0x2de72fc,'mov w2, #-1'),
 ('AP',0x2de7300,'bl #0x1592de0'),('AP',0x2de7314,'bl #0x1591c40'),
 ('AP',0x2de7320,'bl #0x15943d0'),('AP',0x2de46c4,'cmp w0, #0x590, lsl #12'),
 ('AP',0x2de46cc,'mov w19, #0'),('AP',0x2de47d0,'mov w19, #0x69'),
 ('AP',0x2de47d4,'cmn w0, #1'),('AP',0x2d95b44,'bl #0x2ebf3b0'),
 ('CP',0x1ace44,'movs r0, #0x9d'),('CP',0x1abb62,'bl #0x1b5280'),
 ('CP',0x1b528c,'movw r2, #0x202'),('CP',0x1b541c,'bl #0x5daac2'),
 ('CP',0x5f7eea,'movw r0, #0x202'),('CP',0x5f7f2a,'cmp r0, #2'),
 ('CP',0x5f7f32,'cmp r0, #7'),('CP',0x5f7f78,'movw r1, #0x1202'),
 ('CP',0x5f8064,'movt r0, #0xf026'),('CP',0x5f80c2,'bl #0x1e8298'),
 ('CP',0x5ff8b6,'movw r0, #0xf026'),('CP',0x5ff904,'ldr.w r2, [r0, #0x518]'),
 ('CP',0x5ff92a,'bl #0x1e0e5c'),('CP',0x5ff964,'bl #0x1e0ef4'),
 ('CP',0x5ff9b8,'movs r1, #0x32'),('CP',0x60cac0,'bl #0xa5e3f2'),
 ('CP',0xa5e41e,'bl #0xa63abe'),('CP',0x1ada60,'movw r1, #0x1202'),
 ('CP',0x1ada68,'movw ip, #0x296'),('CP',0x1adcc4,'ldr r0, [r0, #8]'),
 ('CP',0x1adcda,'mov.w r2, #0x590000'),('CP',0x1adcde,'orrs r0, r2'),
 ('CP',0x1ac71a,'bl #0x5c9b4e'),('CP',0x5c9b6c,'movw r0, #0x1152'),
 ('CP',0x5c9b8e,'str r5, [sp, #0xc]'),('CP',0x5c9b94,'bl #0x1aef1c')]

def minimum_model(packet,state,*,destination,source,lease,profile):
    """Finite pure software acceptance contract, NOT an installed transport shim.
    Caller supplies the source of THIS original request (not a fixed queue ID).
    Original handler retains request ownership. Returned reply ownership passes
    only after its send succeeds; failures require rollback by the adapter.
    """
    if (packet!=REQUEST or destination!=0x92840747 or not source or
        lease!='owned_single_request' or profile!='headless_peaking_config'):
        raise ValueError('outside frozen software-only peaking contract')
    state['peaking']={'selector':3,'peaking':0,'level':1,'magnification':0,
        'color_type':0,'y':235,'cb':128,'cr':128,'raw_payload':packet[8:].hex(),
        'legacy_packet':'01200202100001000300010000eb8080',
        'pending_hardware':True,'software_config_accepted':True,
        'physical_peaking_verified':False}
    return REPLY

def main():
    volume=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
    assert volume['VolumeUUID'].upper()=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
    hashes={AP:'545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f',
        CP:'c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba'}
    for p,h in hashes.items():assert hashlib.sha256(p.read_bytes()).hexdigest()==h
    proof={'scope':'original AP/CP static audit and finite pure software contract; no QEMU or original code execution',
        'sources':{},'code':{},'checks':[],'volume_uuid':volume['VolumeUUID']}
    def source(p,limit=None):
        with p.open('rb') as f:data=f.read() if limit is None else f.read(limit)
        proof['sources'][str(p.relative_to(ROOT))]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
        return data
    source(AP);source(CP)
    for k,blocks in [('AP',AP_BLOCKS),('CP',CP_BLOCKS)]:
        proof['code'][k]={hex(v):{'bytes':raw(k,v,n).hex(),'length':n,
            'disassembly':dis(k,v,n),'note':'bounded code; mixed Thumb literal/TBB bytes are not independent control-flow evidence'} for v,n in blocks}
    for k,v,want in CHECKS:
        got=dis(k,v,4)[0]['instruction'];assert got==want,(k,hex(v),got,want)
        proof['checks'].append({'binary':k,'va':hex(v),'instruction':got,'bytes':raw(k,v,4 if k=='AP' else len(bytes.fromhex(dis(k,v,4)[0]['bytes']))).hex()})
    proof['imports']={hex(v):imports[v] for v in (0x1592de0,0x1592f10,0x1591c40,0x15943d0,0x1594120,0x1592ec0)}
    assert proof['imports']['0x1592de0']=='osal_rcv_msg_tmo'
    assert proof['imports']['0x1591c40']=='memcpy'
    proof['classes']=[rtti(n) for n in ('N3VDF20VdfSrvcCmdSetPeakingE','N3VDF16DevCmdSetPeakingE')]
    assert proof['classes'][0]['slots']['0xc']=='0x5f7ee5'
    assert proof['classes'][0]['slots']['0x10']=='0x5f7ef5'
    assert proof['classes'][0]['slots']['0x14']=='0x5f7f91'
    assert proof['classes'][1]['slots']['0x14']=='0x5ff8d3'
    proof['tables']=[]
    for name,base,index,target in [('wire0152',0x1aca08,0x152-0x100,0x1ace44),
        ('internal9d',0x1ab6a6,0x9d-0x1f,0x1abb60),('reply0296',0x1ac4ce,0x296-0x225,0x1ac714)]:
        slot=base+index*2;half=struct.unpack('<H',raw('CP',slot,2))[0]
        assert base+half*2==target
        proof['tables'].append({'name':name,'slot':hex(slot),'raw':raw('CP',slot,2).hex(),'target':hex(target)})
    proof['subsystem_slots']={hex(k):{'slot':hex(0xb8120c+k),'target':hex(u32(0xb8120c+k))} for k in (0x518,0x50,0x568,0x3cc)}
    assert u32(0xb8120c+0x518)==0x60fbd9
    proof['selector_routing']=[{'mask':hex(u32(0xb81088+8*i)),'queue':hex(u32(0xb8108c+8*i))} for i in range(5)]
    proof['magnification_level_table']=[list(struct.unpack('<III',raw('CP',0xb7f080+i*12,12))) for i in range(15)]
    assert proof['magnification_level_table'][1]==[0,1,1]
    proof['strings']={k:{hex(v):cstr(k,v) for v in values} for k,values in {
        'AP':(0x3953d37,0x3953d96,0x3953db8,0x3967ae0,0x3915e04,0x3915e25),
        'CP':(0xd87a4f,0xd87a66,0xd87a80,0x1b5430,0x1b5450,0x1b546c,0x1b5484,0x1b549c)}.items()}
    color_table=raw('AP',0x39635fc,4);assert color_table.hex()=='041b2127'
    targets=[0x2dea098+4*x for x in color_table]
    assert targets==[0x2dea0a8,0x2dea104,0x2dea11c,0x2dea134]
    proof['AP_color_branch_table']={'va':'0x39635fc','raw':color_table.hex(),'targets':[hex(v) for v in targets],
        'triples':[[81,90,240],[210,16,146],[29,255,83],[235,128,128]],
        'interpretation':'YCbCr by original CP log names; familiar color labels are inference, not original enum names'}
    fields=['selector','peaking','level','magnification','color_type','y','cb','cr']
    proof['request']={'hex':REQUEST.hex(),'length':16,'header_le16':list(struct.unpack('<4H',REQUEST[:8])),
        'fields':[{'offset':8+i,'name':name,'value':REQUEST[8+i]} for i,name in enumerate(fields)],
        'legacy_hex':'01200202100001000300010000eb8080',
        'translation':'1b52b6..52f0 preserves selector3;1b52f4..5336 copies all 7 remaining bytes',
        'peaking_zero':'CP1e0e96..9e maps exactly1 to enabled and all other values0; captured configuration is off'}
    proof['runtime_receipts']=[]
    logs=[TASK/'menu-repair-01/runtime/runs'/name/'serial.log' for name in LOG_SNAPSHOTS]
    for p in logs:
        snapshot=LOG_SNAPSHOTS[p.parent.name];data=source(p,snapshot['prefix_bytes'])
        assert hashlib.sha256(data).hexdigest()==snapshot['prefix_sha256'],str(p)
        proof['sources'][str(p.relative_to(ROOT))]['scope']='frozen prefix, later appends excluded'
        lines=data.split(b'\n')
        rows=lambda lo,hi:[{'line':i+1,'text':lines[i].decode(errors='replace')} for i in range(lo-1,min(hi,len(lines)))]
        hits=[i for i,x in enumerate(lines) if b'FX3_PROVIDER_REQUEST ' in x and b'raw=0d205201' in x]
        assert len(hits)==1,(p,hits)
        i=hits[0];assert b'raw='+REQUEST.hex().encode()+b' ' in lines[i]
        lo=next(j for j in range(i-1,-1,-1) if b'FX3_PROFILE_STACK_BEGIN ' in lines[j] and b'header=0x152200d' in lines[j])
        frames=[];basefp=None
        for j in range(lo,i):
            mat=re.search(rb'FX3_PROFILE_FRAME depth=(\d+) fp=(0x[0-9a-f]+).*relative=(0x[0-9a-f]+)',lines[j])
            if mat:
                depth,fp,rel=[int(x,0 if x.startswith(b'0x') else 10) for x in mat.groups()]
                if depth==0 and basefp is None:basefp=fp
                if basefp<=fp<=basefp+0x2d0:frames.append({'line':j+1,'depth':depth,'fp':hex(fp),'relative':hex(rel)})
        assert [x['relative'] for x in frames[:6]]==['0x2de7264','0x2dea0e4','0x2dcfcc0','0x2d95a18','0x2bd76fc','0x2f71ba0']
        proof['runtime_receipts'].append({'log':str(p.relative_to(ROOT)),'request_line':i+1,
            'context':rows(lo+1,i+2),'selected_frames':frames,
            'reply_header_marker_count':data.count(b'0d205211'),
            'absence_limit':'markers are bounded/deduplicated; absence is not global proof of no messages'})
        if p.parent.name.startswith('ap83'):
            assert i+1==23895
            proof['AP83_last_snapshot_327']=rows(48527,48586)
            assert b'osal_rcv_msg_tmo' in b'\n'.join(lines[48526:48586])
    for rel in ['COMMON-CONTEXT.md','PLAN.md','audits/post-clear-idle/README.md','audits/boot-vdf-tail/README.md','audits/vdf011a-0159/README.md']:
        source(TASK/'lead-claude'/rel)
    # Boundary cases are checked independently per field and transport metadata.
    kwargs={'destination':0x92840747,'source':0x81cf61c2,'lease':'owned_single_request','profile':'headless_peaking_config'}
    state={};assert minimum_model(REQUEST,state,**kwargs)==REPLY
    tests=[]
    for i,name in enumerate(fields):
        changed=bytearray(REQUEST);changed[8+i]^=1
        tests.append((name+'_changed',bytes(changed),{}))
    tests += [('short',REQUEST[:-1],{}),('long',REQUEST+b'\0',{})]
    for i in range(8):
        changed=bytearray(REQUEST);changed[i]^=1;tests.append(('header_byte_'+str(i),bytes(changed),{}))
    tests += [('wrong_destination',REQUEST,{'destination':0x92840748}),('no_source',REQUEST,{'source':0}),
        ('no_lease',REQUEST,{'lease':'unowned'}),('wrong_profile',REQUEST,{'profile':'physical_camera'})]
    rejects=[]
    for name,packet,override in tests:
        temp=json.loads(json.dumps(state));before=json.loads(json.dumps(temp))
        try:minimum_model(packet,temp,**(kwargs|override))
        except ValueError:assert temp==before;rejects.append({'case':name,'packet':packet.hex(),'override':override})
        else:raise AssertionError(name)
    proof['software_contract']={'scope':'finite proof-only state acceptance, no runtime installation',
        'reply_hex':REPLY.hex(),'reply_length':len(REPLY),'reply_status':hex(struct.unpack('<I',REPLY[8:])[0]),
        'state_after_accept':state,'rejections':rejects,
        'adapter_obligations':['Bind current request source/metadata and one owner; no fixed source queue IDs',
          'Stage full raw config before reply; commit after successful send; allocation/send failure rolls back and frees own reply',
          'Original caller retains request lifecycle and releases reply via2de7320; never fabricate original completion tokens',
          'No f026/hardware/6003/6005/frame/sensor event fabrication; pending_hardware stays true']}
    proof['completion']={'legacy':'2001/1202,12B,status32@8',
        'bridge':'1ada60:1202→0296;1adbd4:oldstatus OR590000;1ac5b0 TBH→1ac714→5c9b4e',
        'normalization':'NONE at5c9b4e; exact status copied unchanged',
        'success_hex':REPLY.hex(),'invalid_input_reply':'0d2052110c00018001005900',
        'device_error_reply':'0d2052110c00018005005900',
        'bridge_send_error_reply':'0d2052110c000180ffffffff',
        'AP_status_conversion':{'0x590000':0,'0x590001':'0x6a','0x590005':'0x6e','-1':'0x69'},
        'no_dynamic_completion':'This worker has no new original CP execution or AP1152-consumption receipt'}
    proof['open_items']=['Original CP service object event/mask lifecycle and device queues were statically traced but not run',
        'No live sensor, active peaking, hardware completion or physical overlay evidence; software acceptance is a chosen backend contract',
        'Exact original user-facing labels of selector bits, level and magnification enum not proved',
        'OSAL timeout-1 cancellation and global shared-queue correlation invariants not fully audited',
        'No AP input struct dump before wrapper: field provenance is code-derived; runtime packet is directly captured',
        'No menus, frame advance, button response, or normal standby acceptance; OSD completion gate is separate']
    target=OUT/'vdf0152-proof.json';target.write_text(json.dumps(proof,indent=2,ensure_ascii=False)+'\n')
    print(f'PASS: {len(CHECKS)} instruction checks, 3 TBH mappings, 2 RTTI classes, {len(logs)} runtime captures, {len(rejects)} rejections; {target.name} rebuilt')
if __name__=='__main__':
    if len(sys.argv)>1:
        for arg in sys.argv[1:]:
            k,v,n=arg.split(':');v,n=int(v,16),int(n,16)
            print(k,hex(v));print('\n'.join(x['va']+': '+x['instruction'] for x in dis(k,v,n)))
    else:main()
