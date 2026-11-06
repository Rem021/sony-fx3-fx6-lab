#!/usr/bin/env python3
"""Offline FX3 display-target audit. Only adjacent proof JSON may be written."""
import sys
sys.dont_write_bytecode = True
import hashlib, io, json, plistlib, re, struct, subprocess
from pathlib import Path
from capstone import Cs, CS_ARCH_ARM64, CS_ARCH_ARM, CS_MODE_ARM, CS_MODE_THUMB
from elftools.elf.elffile import ELFFile

ROOT = Path('/Volumes/KAFU2T/AI/Projects/Mac')
VM = ROOT/'work/fx3-vm-20261101/menu-repair-01'
OUT = Path(__file__).resolve().parent
LIB = VM/'original-uipc/ap-projection/regular-files/usr/lib'
RUN = VM/'runtime/runs/ap85r4osdring-5dcb8371'
assert OUT == ROOT/'work/fx3-vm-20261101/lead-claude/audits/display-target-hinge'
assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID'] == 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'

class Image:
    def __init__(self, name):
        self.name = name
        self.path = (ROOT/'work/sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin' if name=='cp' else LIB/({'ap':'appFw.so','obj':'libObj.so'}.get(name,name)))
        self.raw = self.path.read_bytes()
        self.cs = Cs(CS_ARCH_ARM, CS_MODE_THUMB) if name=='cp' else Cs(CS_ARCH_ARM64, CS_MODE_ARM)
        self.cs.skipdata = True
        self.ptrs, self.plt, self.sym = {}, {}, {}
        if name=='cp': return
        self.elf = ELFFile(io.BytesIO(self.raw))
        self.segs = [s for s in self.elf.iter_segments() if s['p_type']=='PT_LOAD']
        sy = self.elf.get_section_by_name('.dynsym')
        if sy: self.sym = {s.name:(s['st_value'],s['st_size']) for s in sy.iter_symbols()}
        rel = self.elf.get_section_by_name('.rela.plt')
        if rel:
            sy = self.elf.get_section(rel['sh_link']); pv=self.elf.get_section_by_name('.plt')['sh_addr']
            self.plt={pv+32+16*n:sy.get_symbol(r['r_info_sym']).name for n,r in enumerate(rel.iter_relocations())}
        for sec in self.elf.iter_sections():
            if sec['sh_type']!='SHT_RELA': continue
            sy=self.elf.get_section(sec['sh_link'])
            for r in sec.iter_relocations():
                i=r['r_info_sym']; s=sy.get_symbol(i) if i else None
                self.ptrs[r['r_offset']]=(s['st_value'] if s else 0)+r['r_addend']
    def read(self,a,n):
        if self.name=='cp':
            off=a-0x108000
            assert 0<=off<=len(self.raw)-n
            return self.raw[off:off+n]
        s=next(s for s in self.segs if s['p_vaddr']<=a and a+n<=s['p_vaddr']+s['p_filesz'])
        o=s['p_offset']+a-s['p_vaddr']; return self.raw[o:o+n]
    def string(self,a): return self.read(a,512).split(b'\0',1)[0].decode(errors='replace')
    def dis(self,a,n):
        rows=[]
        for i in self.cs.disasm(self.read(a,n),a):
            row={'va':hex(i.address),'raw':i.bytes.hex(),'asm':(i.mnemonic+' '+i.op_str).strip()}
            if i.mnemonic in ('b','bl') and i.op_str.startswith('#'): row['symbol']=self.plt.get(int(i.op_str[1:],16),'')
            rows.append(row)
        return rows
    def strings(self,pattern):
        rx=re.compile(pattern,re.I)
        for m in re.finditer(rb'[ -~]{5,}',self.raw):
            t=m.group().decode()
            if not rx.search(t): continue
            if self.name=='cp': a=m.start()+0x108000
            else:
                seg=next((s for s in self.segs if s['p_offset']<=m.start()<s['p_offset']+s['p_filesz']),None)
                if seg is None: continue
                a=seg['p_vaddr']+m.start()-seg['p_offset']
            print(hex(a),t)
    def xrefs(self,target):
        out=[]
        for sec in self.elf.iter_sections():
            if not sec['sh_flags']&4: continue
            b=sec.data(); base=sec['sh_addr']
            for k,(w,) in enumerate(struct.iter_unpack('<I',b[:len(b)//4*4])):
                a=base+4*k
                if w&0x7c000000==0x14000000:
                    imm=w&0x3ffffff
                    if imm&(1<<25): imm-=1<<26
                    if a+4*imm==target: out.append({'va':hex(a),'kind':'branch'})
                if w&0x9f000000==0x90000000:
                    imm=((w>>5)&0x7ffff)<<2|((w>>29)&3)
                    if imm&(1<<20): imm-=1<<21
                    page=(a&~4095)+(imm<<12); rd=w&31
                    if page!=target&~4095: continue
                    for j in range(1,7):
                        if k*4+j*4+4>len(b): break
                        v=struct.unpack_from('<I',b,(k+j)*4)[0]
                        if v&0x7f000000==0x11000000 and (v>>5)&31==rd:
                            addr=page+((v>>10)&4095)*(4096 if v&(1<<22) else 1)
                            if addr==target: out.append({'va':hex(a+j*4),'kind':'adrp-add','start':hex(a)})
        return {'code':out,'pointers':[hex(k) for k,v in self.ptrs.items() if v==target]}

def branch_case(ap, device_type, vertical, horizontal, close, sideway, hinge, previous=0):
    """Interpret ONLY this routine's Boolean branch graph, never execute guest code.

    Calls outside the function are treated as explicit getter/log/set contracts;
    frame/prologue/lock operations are not executed. All 128 cases must terminate
    at its common orientation-write tail. This is a static counterexample tool,
    not a CPU, physical hinge model or executable firmware implementation.
    """
    ins={int(r['va'],16):r['asm'] for r in ap.dis(0x2823890,0x88c)}
    getters={0x16f0ca8:device_type,0x2943334:vertical,0x294330c:horizontal,
             0x294335c:close,0x2943384:sideway,0x29433ac:hinge,0x2932168:previous}
    reg={}; pending=None; eq=False; pc=0x2823890; category=None; path=[]
    def value(t):
        if t.startswith('#'): return int(t[1:],0)
        if t in ('wzr','xzr'): return 0
        return reg.get(t)
    for _ in range(800):
        if pc==0x2823b80:
            assert category is not None and reg.get('w20') in range(6),(category,reg)
            return {'type':device_type,'V':vertical,'H':horizontal,'C':close,'S':sideway,'hinge':hinge,
                    'category270':category,'orientation243':reg['w20'],'branch_path':path}
        asm=ins[pc]; op,_,args=asm.partition(' '); operands=args.split(', '); nxt=pc+4
        if op=='bl':
            target=int(args[1:],16)
            if target in getters:
                pending=getters[target]
                if target==0x16f0ca8: reg['w0']=pending; pending=None
            elif target==0x282383c: category=reg.get('w1'); path.append(hex(pc))
        elif op=='ldr' and operands[0].startswith('w') and args.endswith('[x0]') and pending is not None:
            reg[operands[0]]=pending; pending=None
        elif op=='mov' and operands[0].startswith('w'): reg[operands[0]]=value(operands[1])
        elif op=='cmp':
            a,b=map(value,operands); assert a is not None and b is not None,(hex(pc),asm,reg)
            eq=(a==b)
        elif op in ('b.eq','b.ne'):
            if eq==(op=='b.eq'): nxt=int(args[1:],16)
        elif op in ('cbz','cbnz'):
            v=value(operands[0]); assert v is not None,(hex(pc),asm,reg)
            if (v==0)==(op=='cbz'): nxt=int(operands[1][1:],16)
        elif op=='b': nxt=int(args[1:],16)
        pc=nxt
    raise AssertionError('branch bound exceeded')

BLOCKS={
 'ap':[(0x2823890,0x88c),(0x28254cc,0x178),(0x275f9f4,0x68),
       (0x16ef200,0xa0),(0x16ee3b8,0x48),(0x294330c,0xc8),
       (0x2763020,0x48),(0x282383c,0x54),(0x2932154,0x28),(0x293285c,0x28),
       (0x16f0ca8,0x18),(0x27d74a8,0x450),(0x27ed7f4,0xc0),
       (0x276503c,0x48),(0x27bd074,0x54),(0x294268c,0x28),
       (0x2b8bb74,0xe0),(0x2df3d08,0x2f8),(0x16f1998,0xb0),
       (0x2dcae08,0x7c),(0x2df264c,0xe0),(0x2de72e8,0x44),
       (0x2c210ec,0x28),(0x2dec02c,0x100),(0x29810d0,0xa0)],
 'obj':[(0xc8850,0x58),(0xc9c08,0x54),(0xc9bb4,0x54),(0xcbaa0,0x164),
        (0xcb640,0xac),(0x1771f4,0x84),(0x175044,0x10),(0x176b84,0x20),
        (0x16ea10,0xd4),(0xf2638,0x1a0),(0xf2fa0,0x108),(0xf22f0,0x48)],
 'cp':[(0x49b8c8,0x88),(0x1a8a90,0x80)]}

CHECKS=[
 ('ap',0x28254f8,'mov w0, #0x1bd'),('ap',0x2825538,'mov w0, #0x1bc'),
 ('ap',0x2825578,'mov w0, #0x1bb'),('ap',0x28255b8,'mov w0, #0x1be'),
 ('ap',0x28255f8,'mov w0, #0x1bf'),('ap',0x2825630,'bl #0x2823890'),
 ('ap',0x16ef26c,'bl #0x1593300'),('ap',0x275fa34,'stp wzr, wzr, [x29, #0x28]'),
 ('ap',0x2823aec,'mov w1, #2'),('ap',0x2823b20,'mov w20, #2'),
 ('ap',0x2823d68,'mov w1, #3'),('ap',0x2823ecc,'mov w1, #7'),
 ('ap',0x2763048,'mov w0, #0x270'),('ap',0x2823ba4,'mov w0, #0x243'),
 ('ap',0x27ed854,'cmp w21, #2'),('ap',0x27ed85c,'ccmp w21, #9, #4, ne'),
 ('ap',0x27ed864,'ccmp w20, #1, #0, eq'),('ap',0x27ed868,'csel w20, w20, w0, ne'),
 ('ap',0x2765064,'mov w0, #0xd22'),('ap',0x27d77a0,'mov x0, #0x7ba'),
 ('ap',0x2dcae38,'bl #0x2dd1f14'),('ap',0x2df26bc,'bl #0x2de70a8'),
 ('ap',0x2de72fc,'mov w2, #-1'),('ap',0x16f1a0c,'bl #0x1593490'),
 ('ap',0x16f1a1c,'bl #0x1593960'),('obj',0xc889c,'str w2, [x1, #8]'),
 ('obj',0xc9c30,'ldr w0, [x1, #8]'),('obj',0x177208,'tst w0, #0xff'),
 ('obj',0x17720c,'b.eq #0x17726c'),('obj',0x175044,'ldr w0, [x0, #0x8ac]'),
 ('obj',0x16ea60,'cbz w0, #0x16eadc'),('obj',0x16eadc,'bl #0x15da80')]

def rebuild(check=False):
    proof={'scope':'offline static audit and frozen AP85r4 readback; no QEMU, guest or device execution',
           'line_convention':'1-based split on LF bytes; strip CR only after counting',
           'sources':{},'blocks':[],'checks':[]}
    def source(path,pin=None):
        b=path.read_bytes(); digest=hashlib.sha256(b).hexdigest()
        if pin: assert digest==pin,(str(path),digest,pin)
        proof['sources'][str(path.relative_to(ROOT))]={'bytes':len(b),'sha256':digest}
        return b
    images={k:Image(k) for k in BLOCKS}
    pins={'ap':'545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f',
          'obj':'c4681d209a7fe2ed63752be3b0be89ab7b7ce400679c00068c8c6e47d39f83ae',
          'cp':'c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba'}
    for k,im in images.items():
        source(im.path,pins[k])
        for a,n in BLOCKS[k]:proof['blocks'].append({'image':k,'va':hex(a),'length':n,'raw':im.read(a,n).hex(),'disassembly':im.dis(a,n)})
    for k,a,expected in CHECKS:
        r=images[k].dis(a,4)[0]; assert r['asm']==expected,(k,hex(a),r,expected)
        proof['checks'].append({'image':k,**r})
    ap=images['ap']
    proof['strings']={hex(a):ap.string(a) for a in [0x379c118,0x379c153,0x379c1ba,0x379c2af,0x379c2dc,0x379c339,
       0x37a5cc0,0x37a44f8,0x379b0db,0x379b0c7,0x39227cf,0x3960c90,0x3968a40,0x3b2c7bc,0x3b2c7e2,0x3b2c80c]}
    categories=['NORMAL_CLOSE','NORMAL_OPEN','REVERSE_CLOSE','REVERSE_OPEN','SELF_SHOOTING','LOW_ANGLE','SIDE_OPEN','VALI_ANGLE','NORMAL_CLOSE_HINGE_OPEN','REVERSE_CLOSE_HINGE_OPEN','SIDE_OPEN_HINGE_OPEN']
    cases=[branch_case(ap,t,v,h,c,s,g) for t in range(4) for v in range(2) for h in range(2) for c in range(2) for s in range(2) for g in range(2)]
    for c in cases:c['name']=categories[c['category270']]
    assert len(cases)==128
    normal=branch_case(ap,2,1,0,0,0,0); reverse=branch_case(ap,2,0,0,1,1,0); missing=branch_case(ap,2,0,0,0,0,0)
    assert (normal['category270'],normal['orientation243'])==(1,0)
    assert (reverse['category270'],reverse['orientation243'])==(2,2)
    assert (missing['category270'],missing['orientation243'])==(7,2)
    proof['branch_truth_table']={'method':'bounded static branch interpreter, previous orientation=0; no original code execution',
        'cases':cases,'normal_open':normal,'reverse_close':reverse,'all_zero_uninitialized_counterexample':missing,
        'enum2_not_unique':sorted({c['name'] for c in cases if c['orientation243']==2})}
    initial_index=struct.unpack('<I',ap.read(0x47ce0a8,4))[0]
    initial_type=struct.unpack('<I',ap.read(0x2f99ce0+4*initial_index,4))[0]
    assert (initial_index,initial_type)==(8,2)
    proof['compiled_initial_panel_type']={'global_index_va':'0x47ce0a8','file_initial_index':initial_index,
        'table_va':'0x2f99ce0','file_initial_type':initial_type,'getter':'0x16f0ca8',
        'limit':'file initial data, not current runtime readback or a proof that no later writer exists'}
    proof['parameter_identity']={'270':'panel category, getter293285c ->822c9f4',
        '243':'display orientation, getter2932154 ->822c71c',
        'd22':'active display output, getter294268c ->834375c; 0 EVF,1 MONITOR,2 NONE',
        'd72_d76':'five InfraInput status parameters, horizontal,vertical,close,sideway,hinge',
        'warning':'VM enum243=2 does not identify category270=2; no current 270/five-key snapshot exists in selected evidence'}
    # String registration records are (type32,id32,aux64,name64), not name-first.
    proof['parameter_registration']=[]
    for p in [0x41783b0,0x4178f50,0x4178fb0,0x4188460,0x4188be0,0x4188bf8,0x4188c10,0x4188c28,0x4188c40,0x418d7a0]:
        raw=ap.read(p-16,24); typ,ident,aux,_=struct.unpack('<IIQQ',raw); name=ap.string(ap.ptrs[p])
        proof['parameter_registration'].append({'va':hex(p-16),'raw_unrelocated':raw.hex(),'type':typ,'id':hex(ident),'aux':aux,'name':name,'name_relocated':hex(ap.ptrs[p])})
    proof['display_output_enum_names']=[{'index':i,'pointer_va':hex(0x41381d0+8*i),'name':ap.string(ap.ptrs[0x41381d0+8*i])} for i in range(3)]
    # Independent read of original same-model template rows; offsets remain file offsets.
    seed=source(VM/'original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin','bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2')
    pairs=list(struct.iter_unpack('<II',ap.read(0x2f8f8d8,0x22d0)))
    codes={0x1bb:0x71c3,0x1bc:0x71c4,0x1bd:0x71c5,0x1be:0x71c6,0x1bf:0x71cb}
    mapping=[]
    for u,p in codes.items():
        index=pairs.index((u,p)); logical=[]; hardware=[]
        for off in range(0x53570,0x53570+1112*48,48):
            v=struct.unpack_from('<12I',seed,off)
            if v[2]==p:logical.append({'file_offset':hex(off),'u32':list(v),'raw':seed[off:off+48].hex()})
        for rec,base in enumerate([0x71190,0x13cdb4]):
            size=struct.unpack_from('<I',seed,base+20)[0]
            for off in range(base+24,base+24+size,64):
                v=struct.unpack_from('<16I',seed,off)
                if v[9]==p:hardware.append({'record':rec,'file_offset':hex(off),'category':v[1],'bank':v[2],'bit':v[3],'active_level':v[4],'on_value':v[10],'raw':seed[off:off+64].hex()})
        assert len(logical)==1 and logical[0]['u32'][9]==0x410025
        mapping.append({'UI_key':hex(u),'InfraInput_key':hex(p),'map_va':hex(0x2f8f8d8+8*index),'logical':logical,'hardware':hardware,
                        'normal_open_status':None if u==0x1bf else int(u==0x1bc),
                        'raw20B_normal_open_example':None if u==0x1bf else struct.pack('<5I',p,0,int(u==0x1bc),0,1).hex()})
    assert [(x['hardware'][0]['bank'],x['hardware'][0]['bit']) for x in mapping[:4]]==[(7,21),(7,19),(7,18),(7,20)]
    assert not mapping[4]['hardware']
    proof['hinge_input_mapping']=mapping
    kp=VM/'original-uipc/ap-projection/full-v4/payloads/d9fcf59b62f9960878f5ea433d350112f4a03fb9c6cd9d30154fb3e3ff54a057'
    ko=ELFFile(io.BytesIO(source(kp,'d9fcf59b62f9960878f5ea433d350112f4a03fb9c6cd9d30154fb3e3ff54a057')))
    textsec=ko.get_section_by_name('.text').data(); cs=Cs(CS_ARCH_ARM64,CS_MODE_ARM)
    proof['original_input_driver']=[{'address_domain':'.text section relative, ET_REL; not runtime VA','offset':hex(a),'raw':textsec[a:a+n].hex(),
       'disassembly':[{'offset':hex(i.address),'raw':i.bytes.hex(),'asm':i.mnemonic+' '+i.op_str} for i in cs.disasm(textsec[a:a+n],a)]}
       for a,n in [(0x12f0,0xf4),(0x1f60,0x2c)]]
    proof['input_source_limits']=['Selected template record1 supplies GPIO7 for four angle keys, not GPIO5 or direct Backup243 state.',
        'Hinge-detect71cb has logical config but no physical row in these two selected1120000 tables; source unproven.',
        'SysCon/CP live electrical producer and active VM cache contents are not established by template rows.',
        'Other243 writers exist, including29810d0 map restore; selected runtime evidence does not identify the last writer or active restore map.',
        'Sentinel7fffffff in original cache is normalized to zero by275f9f4/16ef284; all-zero inputs can produce VALI_ANGLE270=7 and orientation243=2.']
    # Fixed VM launcher/model are evidence, never executed.
    for rel in ['runtime/ap85-osd-software-ring-r4/init-reviewed.sh','runtime/helpers/fx3-display-info.c','runtime/gpio-model/fx3_gpio_bank5.c','runtime/helpers/fx3-ui-gate-v11.c']:
        b=source(VM/rel); lines=b.decode().split('\n')
        rx=r'insmod|FX3_DISPLAY_INFO=|response\[18\]|No input signal|off==0x10|group==1|struct statistics|st.count\[id\]'
        proof.setdefault('model_source_lines',{})[rel]=[{'line':i+1,'text':s} for i,s in enumerate(lines) if re.search(rx,s)]
    log=source(RUN/'serial.log','c493986a68c7dc4d8f05e24167c9eee3808e99a2087a01d92f370921b7306d8e').decode(errors='replace').split('\n')
    def hits(rx):return [{'line':i+1,'text':s.rstrip('\r')} for i,s in enumerate(log) if re.search(rx,s)]
    proof['serial']={'orientation':hits(r'FX3_PANEL_REVERSE_ENUM|FX3_PANEL_CONSUMER_APPLIED|FX3_DISPLAY_INFO_COMMIT'),
       'draws':hits(r'FX3_GPE_CMD '),'OSD_first_and_late':hits(r'FX3_OSD_HEADLESS_ACK frame=(1|1350) '),
       'UI_first_and_1000':hits(r'FX3_UI_GATE_SAMPLE id=8 n=(1|1000) '),
       'SYS0400':hits(r'FX3_PROVIDER_REQUEST .*raw=0d200004|relative=0x2df26c0|relative=0x2dcae3c'),
       'input_receiver':hits(r'name=I-InputRecv queue=0x807a0020'),
       'panel_out_requests':hits(r'FX3_PROVIDER_REQUEST .*raw=0d201801')}
    assert len(proof['serial']['panel_out_requests'])==1
    panel_raw=bytes.fromhex(re.search(r'raw=([0-9a-f]+)',proof['serial']['panel_out_requests'][0]['text']).group(1))
    assert panel_raw==bytes.fromhex('0d201801160001800301000000000000000000000100')
    proof['captured_panel_out']={'raw':panel_raw.hex(),'update_mask':panel_raw[8],'panel':panel_raw[9],'evf':panel_raw[10],
       'line':proof['serial']['panel_out_requests'][0]['line'],
       'limit':'Early startup request, no-wait; neither current d22 nor physical LCD acceptance. Observer uniqueness/capacity means no exhaustive later-request absence claim.'}
    assert len(proof['serial']['draws'])==2 and 'op=FillRect' in proof['serial']['draws'][0]['text']
    gate=source(RUN/'ui-gate-counters.bin'); h=struct.unpack_from('<8Q',gate)
    assert h[0]==0x3145544147335846 and h[2] in (0,1)
    vals=struct.unpack_from('<96Q',gate,0x100+h[2]*0x1000)
    proof['gate_readback']={'header':list(h),'selected_bank':h[2],'counts':list(vals[:64]),'statistics':list(vals[64:]),'UI_updates':vals[8]}
    assert vals[8]==1360
    osd=json.loads(source(RUN/'osd-ring-readback.json'))
    final=osd['polls'][-1]; assert final['final'] and final['global_words'][4:7]==[1358,1358,1358]
    frames=osd['frames']; assert frames and all(f['pixel_source_sequence']==1 and f['update_id']=='0x1005' for f in frames)
    proof['OSD_readback']={'final_poll':final,'observed_frames':len(frames),'update_ids':sorted({f['update_id'] for f in frames}),
       'pixel_source_sequences':sorted({f['pixel_source_sequence'] for f in frames}),'first_nonuniform_found':osd['first_nonuniform_found'],
       'sequence_gap_count':len(osd['sequence_gaps']),'limit':'QMP ring overwrites intermediate slots; global counters are not a complete per-frame payload history'}
    # Exact raw snapshots independently prove the retained AP pixels are zero.
    proof['retained_pixels']=[]
    for name in ['osd-frame-000008.raw','osd-frame-001320.raw']:
        b=source(RUN/name); assert len(b)==614400 and not any(b)
        proof['retained_pixels'].append({'file':name,'span':len(b),'nonzero_bytes':0})
    proof['conclusions']=[
       {'grade':'A static','claim':'243 direction enum2 is many-to-one; 270 category2/9 is distinct and can force active MONITOR1 to NONE2.','evidence':['AP2823890..4118','AP27ed844..888']},
       {'grade':'B semantic','claim':'REVERSE_CLOSE is the nonvisible/inward closed state in display policy; NORMAL_CLOSE is the other closed orientation. Physical magnet polarity/angle has no independent device oracle.','evidence':['AP27ed854..868','template record1 GPIO7 active_level1']},
       {'grade':'A static; U dynamic','claim':'Five InfraInput cached keys feed category/orientation. Missing cache gives a concrete all-zero enum2 counterexample; actual VM270/cache/default-selection was not captured.','evidence':['AP28254cc..5630','Objc8850..88a0','AP275fa34','AP16ef284']},
       {'grade':'A frozen runtime','claim':'UI1360 updates and OSD metadata continuation coexist with only FillRect+Flush and zero retained pixels; earlier publication wait is crossed.','evidence':['serial21939..21973','serial59893','ui-gate-counters.bin selected bank1']},
       {'grade':'A static; U causal','claim':'GRM uses dirty state and WidgetSystem draw candidate count; no active Widget root/visibility/dirty readback ties display NONE to this no-draw run.','evidence':['Obj1771f4','Obj175044','Obj16ea58..16eadc']},
       {'grade':'A static; U downstream','claim':'0400 is SYS timecode TCMODE on SeqQueueCommon, not LCD/VDF initialize. It blocks that task; subsequent observer/queued work dependency on UI visibility is uncaptured.','evidence':['serial21793..21809','AP3960c90','AP2dcae38','AP2df26bc']},
       {'grade':'official model fact; U exact firmware hardware descriptor','claim':'FX3 has no built-in EVF; shared firmware EVF strings and software016a EVF640x480 are not physical-presence evidence.','evidence':['Sony Cine 2021-03-22','serial18666','fx3-display-info.c:5']}
    ]
    proof['web_sources']=[{'url':'https://sony-cinematography.com/articles/the-sony-fx3---what-s-it-all-about--a-brief-review-by-alister-chapman/',
       'published':'2021-03-22','checked':'2026-11-02','support':'Sony official Cinema site says the EVF was removed; LCD can flip out and around.',
       'limit':'Web research metadata; offline rebuild does not access network or certify webpage bytes.'}]
    proof['unproven']=['Current VM270, d22/d23, d72..d76 and five-key cache values / physical initial sensor trace.',
       'Exact original FX3 hardware capability descriptor proving no EVF; official model evidence is available but generic016a geometry is not that descriptor.',
       'Physical inward/outward hinge sensor calibration beyond native software policy; hinge-detect71cb source.',
       'Full global display-output-to-Widget visibility/dirty wiring and current root tree/resources/dirty counts.',
       'Causal proof that SYS0400 blocks a later UI-enabling observer/sequence; direct LCD initialization hypothesis is contradicted by its original name.',
       'Runtime correct-sensor protocol consumption, native notification and orientation change, following nonblack GPE/1003 and interactive menu acceptance.']
    target=OUT/'display-target-proof.json'; encoded=json.dumps(proof,ensure_ascii=False,indent=2)+'\n'
    if check:assert target.read_text()==encoded,'proof differs from independent rebuild'
    else:target.write_text(encoded)
    print('PASS display-target audit: original bytes + 128 branch cases + AP85r4 readback; causal/physical gaps explicitly open')

def main():
    if len(sys.argv)==1: return rebuild()
    if sys.argv[1]=='--check': return rebuild(True)
    mode,name,*args=sys.argv[1:]; im=Image(name)
    if mode=='dis':
        for row in im.dis(int(args[0],16),int(args[1],16)): print(row['va'],row['asm'],row.get('symbol',''))
    elif mode=='str':
        for a in args: print(a,im.string(int(a,16)))
    elif mode=='strings': im.strings(args[0])
    elif mode=='xref':
        for a in args: print(a,json.dumps(im.xrefs(int(a,16))))
    elif mode=='ptr':
        a,n=int(args[0],16),int(args[1],16)
        for v in range(a,a+n,8): print(hex(v),hex(im.ptrs.get(v,struct.unpack('<Q',im.read(v,8))[0])))
    else: raise ValueError(mode)

if __name__=='__main__': main()
