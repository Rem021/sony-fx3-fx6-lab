#!/usr/bin/env python3
"""Offline FX3 first-screen audit; only adjacent first-screen-proof.json is writable."""
import sys
sys.dont_write_bytecode = True
import hashlib, io, json, plistlib, re, struct, subprocess
from pathlib import Path
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM, CS_ARCH_ARM, CS_MODE_THUMB
from elftools.elf.elffile import ELFFile

ROOT = Path('/Volumes/KAFU2T/AI/Projects/Mac')
VM = ROOT/'work/fx3-vm-20261101/menu-repair-01'
LIB = VM/'original-uipc/ap-projection/regular-files/usr/lib'
OUT = Path(__file__).resolve().parent
RUN = VM/'runtime/runs/ap86bdisplayv2-3d542078'
assert OUT == ROOT/'work/fx3-vm-20261101/lead-claude/audits/first-screen-trigger'
assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID'] == 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'

class Image:
    def __init__(self,name):
        self.name=name; self.path=(ROOT/'work/sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin' if name=='cp' else LIB/({'ap':'appFw.so','obj':'libObj.so'}.get(name,name)))
        self.raw=self.path.read_bytes()
        self.ptrs={}; self.plt={}; self.sym={}
        self.cs=Cs(CS_ARCH_ARM,CS_MODE_THUMB) if name=='cp' else Cs(CS_ARCH_ARM64,CS_MODE_ARM)
        self.cs.skipdata=True
        if name=='cp': return
        self.elf=ELFFile(io.BytesIO(self.raw))
        self.segs=[s for s in self.elf.iter_segments() if s['p_type']=='PT_LOAD']
        self.cs=Cs(CS_ARCH_ARM64,CS_MODE_ARM); self.cs.skipdata=True
        self.ptrs={}; self.plt={}
        sy=self.elf.get_section_by_name('.dynsym')
        self.sym={s.name:(s['st_value'],s['st_size']) for s in sy.iter_symbols()} if sy else {}
        rel=self.elf.get_section_by_name('.rela.plt')
        if rel:
            sy=self.elf.get_section(rel['sh_link']); pv=self.elf.get_section_by_name('.plt')['sh_addr']
            self.plt={pv+32+16*n:sy.get_symbol(r['r_info_sym']).name for n,r in enumerate(rel.iter_relocations())}
        for sec in self.elf.iter_sections():
            if sec['sh_type']!='SHT_RELA': continue
            sy=self.elf.get_section(sec['sh_link'])
            for r in sec.iter_relocations():
                i=r['r_info_sym']; s=sy.get_symbol(i) if i else None
                self.ptrs[r['r_offset']]=(s['st_value'] if s else 0)+r['r_addend']
    def read(self,a,n):
        if self.name=='cp': return self.raw[a-0x108000:a-0x108000+n]
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
        rx=re.compile(pattern,re.I); out=[]
        for m in re.finditer(rb'[ -~]{5,}',self.raw):
            t=m.group().decode()
            if not rx.search(t): continue
            if self.name=='cp':
                out.append({'va':hex(m.start()+0x108000),'text':t}); continue
            seg=next((s for s in self.segs if s['p_offset']<=m.start()<s['p_offset']+s['p_filesz']),None)
            if seg is not None: out.append({'va':hex(seg['p_vaddr']+m.start()-seg['p_offset']),'text':t})
        return out
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

BLOCKS = {
 'ap':[(0x237f618,0x1194),(0x21916b0,0x2b8),(0x218fd0c,0x344),
       (0x2827290,0x13c),(0x27fd30c,0xc4),(0x293019c,0x64),
       (0x2930b9c,0x28),(0x29489e4,0x28),(0x293096c,0x44),
       (0x237f74c,0x160),(0x2b63908,0xd0),(0x2b63c2c,0x18),
       (0x2f72000,0x3c),(0x2f720ec,0x124),(0x285e3fc,0x94),
       (0x2b68330,0x68),(0x2dca610,0x1b0),(0x2dca7fc,0x1a4),
       (0x2dd1e14,0x40),(0x2dd1ed4,0x40),(0x2df22e8,0x88),
       (0x2df2528,0x124),(0x2de70a8,0x29c),(0x2de4574,0x160),
       (0x2b7f8cc,0xb94),(0x2d9ac90,0x240),
       (0x2dda334,0x180),(0x2dda5b4,0x80),(0x2dd8b54,0x40),
       (0x2e4efb8,0x2c8),(0x2e4f488,0x530),(0x2e4f99c,0x38),
       (0x2e4fbf0,0x360),(0x2e50150,0x220),(0x2e41e20,0x84),
       (0x2dd8814,0x40),(0x2e33bcc,0x228),(0x2e26c40,0x90),
       (0x2e3334c,0x6c),(0x2e2fb90,0x594),
       (0x1cdcf28,0x124),(0x2845900,0xb0),
       (0x16f1998,0xb0),(0x2bd763c,0x150)],
 'obj':[(0x1771f4,0x84),(0x16ea10,0xd4),(0x175044,0x10)],
 'cp':[(0x1a8134,0x40),(0x1a8190,0x70),(0x5ce312,0x10),
       (0x1ac9c8,0x40),(0x1ad03e,0x18),(0x1ad050,0x26),
       (0x1a9a3c,0x50),(0x1a9fcc,0xa),(0x5cada6,0x16),
       (0x1b9090,0x1a),(0x1b9146,0x34),(0x1b917a,0x34),
       (0x1b944a,0x8),(0x5c68de,0x12),(0x1ad1a4,0x26),
       (0x1ad37e,0xc),(0x1ad6b6,0x26),(0x1ab1ae,0x1c),
       (0x1ae03c,0x64),(0x1ae0c0,0x64),(0x1aef1c,0xae),
       (0x98c8ea,0xd2),(0x98f66a,0x6c)]}

CHECKS = [
 ('ap',0x2380784,'cmp w2, w1'),('ap',0x2380794,'bl #0x237fe28'),
 ('ap',0x238030c,'bl #0x2827348'),('ap',0x2380320,'cbz w0, #0x238034c'),
 ('ap',0x2380468,'cmp w0, #2'),('ap',0x2380470,'orr w23, w25, w23'),
 ('ap',0x2380620,'mov w0, #0x2e1'),('ap',0x23806c0,'mov w0, #0x178'),
 ('ap',0x28272b8,'cmp w1, w0'),('ap',0x28272bc,'b.hs #0x2827340'),
 ('ap',0x28272c4,'bl #0x27fd30c'),('ap',0x28272d4,'bl #0x2ebfdfc'),
 ('ap',0x27fd38c,'mov w1, #6'),('ap',0x27fd394,'bl #0x27bee0c'),
 ('ap',0x2dca864,'bl #0x2dd1ed4'),('ap',0x2df254c,'mov w1, #0x402'),
 ('ap',0x2df2598,'bl #0x2de70a8'),('ap',0x2de72fc,'mov w2, #-1'),
 ('ap',0x2de7300,'bl #0x1592de0'),('ap',0x2df2310,'mov w1, #0x404'),
 ('ap',0x2df2354,'bl #0x2de70a8'),('ap',0x2b8036c,'mov w0, #0x86'),
 ('ap',0x2b80370,'movk w0, #3, lsl #16'),('ap',0x2b8037c,'bl #0x27381b8'),
 ('ap',0x2b7f9a4,'stp w28, wzr, [x29, #0xa0]'),
 ('ap',0x2b8021c,'mov w0, #0x1db'),('ap',0x2b80224,'mov w0, #1'),
 ('ap',0x2e41e7c,'mov x5, #0'),('ap',0x2e41e80,'mov x4, #0'),
 ('ap',0x2e41e94,'str wzr, [x20]'),('ap',0x2e33bf4,'mov w2, #0x403d'),
 ('ap',0x2e33cc8,'cmp w0, #0xf, lsl #12'),
 ('ap',0x2e26c98,'bl #0x1592d30'),('ap',0x1cdcf2c,'mov w1, #0x86'),
 ('ap',0x1cdcf30,'movk w1, #3, lsl #16'),
 ('obj',0x175044,'ldr w0, [x0, #0x8ac]'),
 ('obj',0x16ea60,'cbz w0, #0x16eadc'),
 ('cp',0x1a813a,'ldrb r0, [r0, #8]'),
 ('cp',0x1a814a,'str.w r0, [r4, #0x434]'),
 ('cp',0x1ad042,'movs r0, #0x40'),('cp',0x1ad046,'movs r0, #0x41'),
 ('cp',0x1a9a6e,'movs r1, #2'),('cp',0x1a9a80,'movs r1, #4'),
 ('cp',0x1b916e,'orr r1, r1, #4'),('cp',0x1b9174,'movw r0, #0x402'),
 ('cp',0x1b91a2,'orr r1, r1, #0x10'),('cp',0x1b91a8,'movw r0, #0x404'),
 ('cp',0x1b944a,'movs r1, #0'),('cp',0x1ae06c,'movw r0, #0x1402'),
 ('cp',0x1ae08e,'str r6, [sp, #0x14]'),('cp',0x1ae0f0,'movw r0, #0x1404'),
 ('cp',0x1ae112,'str r6, [sp, #0x14]'),
 ('cp',0x98f68c,'movw r1, #0x403d'),('cp',0x98f694,'mov.w r1, #0xf000')]

def backup_property(data, ident, verify_checksum):
    _,_,_,rev,ns,np,start,size,checksum=struct.unpack_from('<III4s5I',data)
    assert rev==b'BK4\0' and start+size<=len(data)
    if verify_checksum: assert sum(data[:32])+sum(data[36:start+size])==checksum
    cnt,idx=struct.unpack_from('<HI',data,256+(ident>>16)*6)
    assert ident&65535<cnt and idx+cnt<=np
    p=256+ns*6+(idx+(ident&65535))*6
    attr,ptr=struct.unpack_from('<HI',data,p); assert ptr!=0xffffffff
    n,off=ptr>>24,ptr&0xffffff
    if n==255:n=struct.unpack_from('<H',data,off)[0];off+=2
    elif n==0:n,maxn=struct.unpack_from('<HH',data,off);off+=4;assert n<=maxn
    assert start<=off and off+n<=start+size
    return {'key':hex(ident),'entry_offset':hex(p),'attribute':hex(attr),
            'file_offset':hex(off),'size':n,'raw':data[off:off+n].hex(),
            'value_le':int.from_bytes(data[off:off+n],'little')}

def rebuild(check=False):
    proof={'scope':'offline original AP/Obj/CP, frozen AP86B display-v2; no guest/CP execution',
      'line_convention':'1-based LF bytes, CR removed after counting; not splitlines()',
      'sources':{},'code':{},'checks':[]}
    def source(path,pin=None):
        b=path.read_bytes();sha=hashlib.sha256(b).hexdigest()
        if pin:assert sha==pin,(str(path),sha)
        proof['sources'][str(path.relative_to(ROOT))]={'bytes':len(b),'sha256':sha}
        return b
    images={k:Image(k) for k in BLOCKS}
    pins={'ap':'545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f',
          'obj':'c4681d209a7fe2ed63752be3b0be89ab7b7ce400679c00068c8c6e47d39f83ae',
          'cp':'c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba'}
    for k,im in images.items():
        source(im.path,pins[k])
        proof['code'][k]=[{'va':hex(v),'length':n,'raw':im.read(v,n).hex(),
            'disassembly':im.dis(v,n)} for v,n in BLOCKS[k]]
    for k,v,want in CHECKS:
        r=images[k].dis(v,4)[0];assert r['asm']==want,(k,hex(v),r,want)
        proof['checks'].append({'image':k,**r})
    a,c=images['ap'],images['cp']
    proof['cp_timecode_tables']=[]
    for name,base,index,target in [
      ('wire402 internal40',0x1acb9e,2,0x1ad042),
      ('wire404 internal41',0x1acb9e,4,0x1ad046),
      ('phase0 internal40 event2',0x1a8f16,0x40,0x1a9a60),
      ('phase0 internal41 event4',0x1a8f16,0x41,0x1a9a72),
      ('TCUB event2',0x1b90aa,2,0x1b9146),('TCUB event4',0x1b90aa,4,0x1b917a),
      ('completion402 internal241',0x1ad1ca,2,0x1ad37e),
      ('completion404 internal242',0x1ad1ca,4,0x1ad384),
      ('internal241 reply1402',0x1aab30,0x41,0x1ab1ae),
      ('internal242 reply1404',0x1aab30,0x42,0x1ab1bc)]:
        slot=base+2*index;half=struct.unpack('<H',c.read(slot,2))[0]
        assert base+half*2==target,(name,hex(base+half*2))
        proof['cp_timecode_tables'].append({'name':name,'base':hex(base),'index':index,
          'slot':hex(slot),'raw':c.read(slot,2).hex(),'target':hex(target)})
    proof['cp_parsers']=[]
    for cmd,slot,target in [(0x402,0xb71d34,0x1a8135),(0x404,0xb71d3c,0x1a8191)]:
        raw=c.read(slot,8);assert struct.unpack('<II',raw)==(cmd,target)
        proof['cp_parsers'].append({'command':hex(cmd),'slot':hex(slot),'raw':raw.hex(),
          'thumb_function':hex(target),'meaning':c.string(0x1a8174 if cmd==0x402 else 0x1a8200)})
    proof['rtti']=[]
    for hdr in [0x455b220,0x42ee7f8]:
        ti=a.ptrs[hdr+8];nameptr=a.ptrs[ti+8]
        proof['rtti'].append({'header':hex(hdr),'typeinfo':hex(ti),'name_va':hex(nameptr),
          'name':a.string(nameptr),'slots':{hex(i):hex(a.ptrs.get(hdr+16+i,0)) for i in [0,8,0x10,0x18,0x88,0x90]}})
    proof['screen_names']=[]
    wanted={0x178,0x18e,0x192,0x193,0x2e1,0x407,0x2ae,0xa1,0x31c,0x324}
    for p,v in sorted(a.ptrs.items()):
        if not 0x4157000<p<0x415e000:continue
        ident,n=struct.unpack('<II',a.read(p-8,8))
        if ident in wanted and n<100:proof['screen_names'].append({'row':hex(p-8),
          'id':hex(ident),'declared_length':n,'name_va':hex(v),'name':a.string(v),
          'raw':a.read(p-8,16).hex()})
    proof['selected_strings']={k:{hex(v):images[k].string(v) for v in vs} for k,vs in {
      'ap':[0x313583a,0x313587d,0x31358f6,0x3135972,0x3135a30,0x3135ab8,
            0x30f9ec0,0x39607e8,0x3960720,0x3920da8,0x39552c8,0x3c3f70e,
            0x30384f8,0x3bc0cc4],
      'cp':[0x1a8174,0x1a8200]}.items()}
    date_names=[a.string(a.ptrs[0x41359e0+8*i]) for i in range(4)]
    assert date_names==['VAL_date_time_set_status_DATE_TIME_SET_MANUALLY',
      'VAL_date_time_set_status_DATE_TIME_SET_FORCIBLY','VAL_date_time_set_status_DATE_TIME_NOT_SET',
      'VAL_date_time_set_status_DATE_TIME_UNKNOWN']
    proof['date_status']={'enum_names':date_names,'enum_table_va':'0x41359e0',
      'current_param187_va':'0x8227358','next_param187_va':'0x822735c',
      'clock_force_settled_param1098_va':hex(0x821c538+0x149000+0x758),
      'backup_mapping':{'va':'0x40f92c8','raw':a.read(0x40f92c8,40).hex(),
         'parameter':hex(struct.unpack('<I',a.read(0x40f92c8,4))[0]),
         'backup_key':hex(struct.unpack('<I',a.read(0x40f92d4,4))[0])},
      'boot_udate_type_mapping':[]}
    assert proof['date_status']['backup_mapping']['parameter']=='0x187'
    assert proof['date_status']['backup_mapping']['backup_key']=='0x2cf01b4'
    for typ,want in [(0,0),(1,0),(2,2),(3,3)]:
        raw=a.read(0x3917778+2*typ,2);off=struct.unpack('<h',raw)[0]
        dest=0x2b63960+off*4
        at=dest+4 if dest==0x2b63c2c else dest
        ins=a.dis(at,4)[0];assert ins['asm']==f'mov w22, #{want}'
        proof['date_status']['boot_udate_type_mapping'].append({'input':typ,'table_slot':hex(0x3917778+2*typ),
          'raw':raw.hex(),'branch':hex(dest),'param187':want,'instruction':ins})
    seed=source(VM/'original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin',
      'bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2')
    ram=source(RUN/'backup-reserved-ram.bin')
    proof['backup']={name:[backup_property(b,k,name=='original_seed') for k in [0x2cf01b4,0x2cf1841,0x2cf1842]]
       for name,b in [('original_seed',seed),('AP86B_RAM',ram)]}
    assert [r['value_le'] for r in proof['backup']['original_seed']]==[2,0,4]
    assert [r['value_le'] for r in proof['backup']['AP86B_RAM']]==[0,4,4]
    log=source(RUN/'serial.log');lines=log.split(b'\n')
    def hits(pat,cap=None):
        rx=re.compile(pat);rows=[{'line':i+1,'text':b.decode(errors='replace').rstrip('\r')}
          for i,b in enumerate(lines) if rx.search(b.decode(errors='replace'))]
        return {'count':len(rows),'rows':rows if cap is None or len(rows)<=cap else rows[:cap//2]+rows[-cap//2:],
          'truncated':cap is not None and len(rows)>cap}
    patterns={
      'clock':r'DATE_CLOCK|FX3_DATE_CLOCK_BYTES',
      'boot_wait_return':r'FX3_BOOT_(CV_RETURN|SEQUENCE_NOTIFY|.*JOIN|.*NOTIFY|.*WAIT_RETURN)',
      'UUD':r'FX3_UUD_',
      'SYS400':r'FX3_DISPLAY_SYS400|FX3_DISPLAY_COMPLETION_(LIST|ITEM)|FX3_SYS_TCMODE_',
      'after400_queue':r'FX3_DISPLAY_QUEUE.*sample=43[5-8]|FX3_DISPLAY_QUEUE_NODE sample=43[5-8]',
      'SYS402_wire':r'raw=0d2002040a0001800000|relative=0x2df259c|relative=0x2dd1f00|relative=0x2dca868',
      'widgets':r'FX3_DISPLAY_WIDGET', 'dirty':r'FX3_DISPLAY_GRM_DIRTY',
      'GPE':r'FX3_GPE_CMD', 'panel':r'FX3_DISPLAY_PANEL|FX3_DISPLAY_CACHE',
      'face_dmm':r'FX3_FACE_DMM_(COMMIT|CONSUMED)',
      'delete_face_completion_recorded':r'type=0x30386|raw=86030300000000000000000000000000000000000000000000000000',
      'GUI_configuration_calls':r'FX3_TIMER_SNAPSHOT.*config=',
      'unobserved_new_replies':r'raw=0d200214|raw=0d200414'}
    proof['serial']={name:hits(pat,32 if name in ['widgets','dirty','panel','GUI_configuration_calls'] else None)
       for name,pat in patterns.items()}
    assert proof['serial']['SYS402_wire']['count']>=4
    assert proof['serial']['GPE']['count']==2
    assert proof['serial']['delete_face_completion_recorded']['count']==0
    proof['thread_snapshots']=[]
    for i,b in enumerate(lines):
        if b'Name:\tSeqQueueCommon' not in b:continue
        start=max(0,i-8)
        while start<i and b'FX3_TASK_SNAPSHOT_362_BEGIN' not in lines[start]:start+=1
        if start==i:start=i
        end=i+1
        while end<len(lines) and b'FX3_TASK_SNAPSHOT_362_END' not in lines[end]:end+=1
        end=min(end,len(lines)-1)
        proof['thread_snapshots'].append({'begin':start+1,'end':end+1,
          'rows':[{'line':j+1,'text':lines[j].decode(errors='replace').rstrip('\r')} for j in range(start,end+1)]})
    ring=source(RUN/'osd-ring-final.bin');hdr=struct.unpack_from('<4Q',ring,0x3000)
    assert hdr[0]==0x315653424f505344 and hdr[1]==1 and hdr[2] in [0,1]
    vals=struct.unpack_from('<134Q',ring,0x3100+hdr[2]*0x1000)
    proof['display_RAM']={'header':list(hdr),'bank':hdr[2],'pid':vals[0],
      'app_base':hex(vals[1]),'obj_base':hex(vals[2]),'sequence':vals[3],
      'counts':list(vals[4:68]),'state':list(vals[68:132]),'dirty_zero':vals[132],'dirty_nonzero':vals[133],
      'category270':vals[73],'direction243':vals[74],'model_index':vals[75],'active_d22':vals[76],
      'widget_candidate_count':vals[78],
      'warning':'bank mirror is sampled: queue length11 is retained at SYS400 checkpoint, not current heap; layer pointer is not visible Widget root proof'}
    assert (vals[73],vals[74],vals[75],vals[76],vals[78],vals[133])==(7,2,6,1,78,1)
    proof['display_RAM']['model_type']=struct.unpack('<I',a.read(0x2f99ce0+4*vals[75],4))[0]
    assert proof['display_RAM']['model_type']==0
    for fn in ['helpers/fx3-display-observe-v2.c','helpers/seed-date-clock-v2.c',
               'helpers/fx3-face-dmm-core-v1.c','helpers/fx3-release-inhibit.c']:
        source(VM/'runtime'/fn)
    proof['queued_sequence_inventory']=[
      {'index':0,'run':'0x2dca7fc','name':'model::sequence_sys_set_timecode_run',
       'observed_input1bc':'0','wire':'0402','status':'entered, captured synchronous request, no captured reply; native receive snapshots remain'},
      {'index':1,'run':'0x2dca610','name':'model::sequence_sys_set_timecode_preset',
       'observed_input1bc':'0','wire':'0404 NOT0401','status':'queued; +1c0/+1c4/+1c8 not sampled, bytes not fully frozen'},
      {'index':2,'run':'0x2b7f8cc','name':'model::sequence_delete_all_individual_face',
       'observed_input1bc':'0','status':'queued; UUD version already4 does not complete this sequence'},
      {'index':3,'run':'0x2d9ac90','name':'model::sequence_set_release_lock',
       'observed_input1bc':'0x80000033','status':'queued; selector+1b8/+1c0 unobserved'},
      {'index':'4..10','status':'seven task nodes not captured; no honest full inventory from first-four sampling'}]
    rep402=struct.pack('<4HI',0x200d,0x1402,12,0x8001,0)
    rep404=struct.pack('<4HI',0x200d,0x1404,12,0x8001,0)
    assert rep402.hex()=='0d2002140c00018000000000'
    assert rep404.hex()=='0d2004140c00018000000000'
    proof['protocols']={
      'SYS402':{'request_captured':'0d2002040a0001800000','reply_success':rep402.hex(),
        'destination':'0x92840747','reply_destination':'source of this exact request, not fixed queue',
        'reply_source':'0x92840747','CP_saved_run':'0x19eb3ec','CP_pending_word':'0x11cbd58 bit2',
        'meaning':'configuration saved and scheduled; not running timecode/hardware'},
      'SYS404':{'request_schema':'0d2004040c000180 + four captured u8 preset values',
        'request_if_all_four_values_zero':'0d2004040c00018000000000',
        'all_zero_runtime_proven':False,'reply_success':rep404.hex(),
        'CP_saved_preset':'0x19eb3f0..0x19eb3f3','CP_pending_word':'0x11cbd58 bit4',
        'meaning':'store actual preset then configuration acceptance; no counter/frame claim'},
      'face_delete':{'ordered_synchronous_wrappers':[
        ['2b7f9b0','2dda334 ->2e4f488 ->2e4efb8','local DMM op20 allocate-only unit1dc domain0'],
        ['2b7fa08','2dda374 ->2e4f4c0','local DMM op24 open by returned handle'],
        ['2b7fc18','2dda5b4 ->2e50150','native open/mmap, no OSAL reply'],
        ['2b7ff38','2dda5f4 ->2e50264','native munmap/close, no OSAL reply'],
        ['2b7ff84','2dda434 ->2e4f7b8','local DMM op25 close returned handle'],
        ['2b80128','2dda474 ->2e4f99c ->2e4f280','local DMM op23 free returned handle option0'],
        ['2b80230','2dda3f4 ->2e4fbf0','remote DMM op21 open unit1db domain1, input+8 copied from task+1c4 (saved handle), not a proved open-count field']],
        'after_sync':'2b8028c ->2dd8b54 ->2e41e20 sends90060197/0206 with no waiter; backup writes then internal30386 at2b8037c',
        'no_new_reply_for_0206':True,
        'honest_local_reply':'original local DMM provides real allocation/handle/mapping; must not synthesize fixed handles or success',
        'remote_8021_shape_example_existing_840a':None,
        'CP_recognition_or_frame_executed':False},
      'release_lock':{'PID403d_reply_if_wire_token80000033':'01003d403300008000f00000',
        'token_runtime_wire_proven':False,'actual_reply_schema':'01 00 3d 40 + echo actual u32 token + 00 f0 00 00',
        'destination':'0x90040193','reply_source':'0x90040193','reply_destination':'0x80020002',
        'acceptance':'idle software inhibit mask8000 only; track on/off refcount and actual token; no active release ACK',
        'extra_if_selector1':'40a5 no-wait then local condition_variable wait2e26c40 on9684918; no CP success byte can replace local callback',
        'selector_sampling_missing':['task+1b8','task+1c0','9684f80','9684fbc','9684fb8','9684918']}}
    r=bytearray(40);struct.pack_into('<H',r,0,0x8021);struct.pack_into('<H',r,8,1)
    struct.pack_into('<I',r,12,0x840a);struct.pack_into('<Q',r,24,0x1dd80000);struct.pack_into('<I',r,32,0xd100)
    proof['protocols']['face_delete']['remote_8021_shape_example_existing_840a']=r.hex()
    proof['protocols']['face_delete']['remote_8021_example_limits']='corr0 example only, actual request/correlation/live generation/open refs required; existing memory must persist, not zeroed'
    proof['first_screen_decision']={
      'start':'AppFw internal30072 -> scr0039_boot_controller process_power_on237fe28 ->285f3b4 boot future',
      'screen_manager':'presenter_controller_manager open_screen_ii218fd0c; manager21916b0 dispatches active controller vtable+88',
      'UUD_early_return':'238030c updateUUD; true ->set controller+110c3, log uud reset, return2380330 before date/screen choice',
      'date_gate':'2380464 status187==2 OR clock_force_settled1098; additional special-boot/feature checks; rep_boot2e1 if applicable',
      'normal_screen_candidates':['178 scr0103_0009','18e scr0103_0023','192 scr7248_0001','193 scr7221_0004'],
      'known_missing_work':'SYS402 blocks common queue before delete_all_individual_face/30386; this is a concrete prerequisite gap',
      'not_closed':'No current active screen/controller/pending manager snapshot; UUD completion-to-normal initial screen transition is not dynamically or wholly statically closed',
      'no_external_notification_to_forge':'30386 is AP-owned deletion completion after storage and model writes, not missing CP/SysCon ready event'}
    proof['sampling_plan']=[
      {'va':'AP2dca868 /2df259c','read':'result and request source/free, task identity','purpose':'native402reply consumption'},
      {'va':'AP2bd76f8 /2bd7754','read':'queue+10/+20/+88, all11nodes task/vptr/run, completion+158/+160','purpose':'identify remaining seven tasks and next active task'},
      {'va':'AP2dca610','read':'task+1bc/+1c0/+1c4/+1c8','purpose':'freeze actual0404 preset bytes'},
      {'va':'AP2d9ac90','read':'task+1b8/+1bc/+1c0, active-release/cache9684918','purpose':'release_lock branch and optional callback wait'},
      {'va':'AP237fe28 /2380310 /2380464 /23803f4','read':'controller pointer, +110c2/+110c3, saved187/1098, three proposed screen IDs','purpose':'pin the actual first screen decision'},
      {'va':'AP21916b0 /218fd0c','read':'manager+1d0 pending-screen, active IDs+2c4/+2c0 and controllers+2b8/+2b0, input root IDs','purpose':'current boot/rep/normal screen and creation return'},
      {'va':'AP2b8037c /1cdcf28','read':'actual30386 publication and receiving controller type','purpose':'UUD deletion completion without synthesizing it'},
      {'va':'Obj1771f4 /17723c /16ea60','read':'candidate qualifier, layer/Widget actual flags/resources, dirty','purpose':'first nonclear drawing; layer!=visible root'},
      {'va':'AP2930b9c /29489e4 /293019c /29301ec','read':'current187,1098,current mode143/option145','purpose':'do not infer current state from desired144 or Backup version'}]
    proof['unproven']=[
      'Exact current screen/root/visible widgets and complete UUD completion-to-first-screen causal edge.',
      'Remaining seven queue entries, future sequence branches, full actual0404 request, release selector and token.',
      'Exact original CP DMM dynamic allocation and lifecycle responses beyond conditional software geometry examples.',
      'SysCon/power/battery/lens-ready missing notification as a necessary gate: no such causal dependency proved here.',
      'Language/region/license feature gating across all first-start variants; no one fixed universal initial-screen list.',
      'Raw shadow state changes alone do not prove originalCP running, sensor/live-view, menu pixels, input feedback or physical camera acceptance.']
    reference=ROOT/'work/fx3-vm-20261101/lead-claude/research/a7c2-latest/README.md'
    source(reference)
    proof['research']={'checked_date':'2026-11-02','sources':[
      'https://www.capstone-engine.org/lang_python.html',
      'https://github.com/chocotan/a7c2-qemu'],
      'a7c2_fixed_reference':'b3d7c1fed349f1d918acc4259f1d2b3a7c52a500',
      'limit':'Local frozen research describes original menu640x480; current upstream homepage checked, fixed raw progress document fetch failed; not FX3 proof; rebuild is offline'}
    target=OUT/'first-screen-proof.json';encoded=json.dumps(proof,ensure_ascii=False,indent=2)+'\n'
    if check:assert target.read_text()==encoded,'proof differs from independent rebuild'
    else:target.write_text(encoded)
    print(f'PASS first-screen audit: {len(CHECKS)} instruction checks, CP402/404 tables, AP86B serial/RAM, explicit open gates')

def main():
    if len(sys.argv)==1: return rebuild()
    if sys.argv[1]=='--check': return rebuild(True)
    mode,name,*args=sys.argv[1:]; im=Image(name)
    if mode=='dis':
        for row in im.dis(int(args[0],16),int(args[1],16)): print(row['va'],row['asm'],row.get('symbol',''))
    elif mode=='str':
        for a in args: print(a,im.string(int(a,16)))
    elif mode=='strings':
        for row in im.strings(args[0]): print(row['va'],row['text'])
    elif mode=='xref':
        for a in args: print(a,json.dumps(im.xrefs(int(a,16))))
    elif mode=='sym':
        for name,(a,n) in im.sym.items():
            if re.search(args[0],name,re.I): print(hex(a),hex(n),name)
    elif mode=='ptr':
        a,n=int(args[0],16),int(args[1],16)
        for v in range(a,a+n,8): print(hex(v),hex(im.ptrs.get(v,struct.unpack('<Q',im.read(v,8))[0])))
    else: raise ValueError(mode)

if __name__=='__main__': main()
