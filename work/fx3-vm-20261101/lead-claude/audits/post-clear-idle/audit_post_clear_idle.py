#!/usr/bin/env python3
"""Offline AP83a audit. Reads fixed evidence; writes only adjacent proof JSON.

No emulator, guest, CP code, probe, device, or predecessor rebuild is executed.
"""
import sys
sys.dont_write_bytecode = True
import hashlib, json, plistlib, re, struct, subprocess
from pathlib import Path
from collections import defaultdict
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM, CS_ARCH_ARM, CS_MODE_THUMB
from elftools.elf.elffile import ELFFile

OUT = Path(__file__).resolve().parent
ROOT = Path('/Volumes/KAFU2T/AI/Projects/Mac')
RT = ROOT/'work/fx3-vm-20261101/menu-repair-01/runtime'
RUN = RT/'runs/ap83ar4face-4cd8574a'
LIB = RT.parent/'original-uipc/ap-projection/regular-files/usr/lib'
CP = ROOT/'work/sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin'
UUID = 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID'] == UUID

class Image:
    def __init__(self, name):
        self.name = name
        self.path = CP if name == 'cp' else LIB/name
        if not self.path.exists():
            self.path = LIB.parents[1]/'lib'/name
        self.raw = self.path.read_bytes()
        self.plt, self.ptrs, self.sym = {}, {}, {}
        if name == 'cp':
            self.cs = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
            return
        self.f = self.path.open('rb'); self.e = ELFFile(self.f)
        self.segs = [s for s in self.e.iter_segments() if s['p_type']=='PT_LOAD']
        self.cs = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
        sy = self.e.get_section_by_name('.dynsym')
        if sy: self.sym = {s.name:(s['st_value'],s['st_size']) for s in sy.iter_symbols()}
        rel = self.e.get_section_by_name('.rela.plt')
        if rel:
            sy = self.e.get_section(rel['sh_link']); pv = self.e.get_section_by_name('.plt')['sh_addr']
            self.plt = {pv+32+16*n:sy.get_symbol(r['r_info_sym']).name for n,r in enumerate(rel.iter_relocations())}
        for sec in self.e.iter_sections():
            if sec['sh_type']!='SHT_RELA': continue
            sy = self.e.get_section(sec['sh_link'])
            for r in sec.iter_relocations():
                i = r['r_info_sym']; s = sy.get_symbol(i) if i else None
                self.ptrs[r['r_offset']] = (s['st_value'] if s else 0)+r['r_addend']
    def read(self, va, n):
        if self.name == 'cp': return self.raw[va-0x108000:va-0x108000+n]
        s = next(s for s in self.segs if s['p_vaddr']<=va and va+n<=s['p_vaddr']+s['p_filesz'])
        o = s['p_offset']+va-s['p_vaddr']; return self.raw[o:o+n]
    def string(self, va): return self.read(va, 512).split(b'\0',1)[0].decode(errors='replace')
    def dis(self, va, n):
        rows = []
        for i in self.cs.disasm(self.read(va,n),va):
            row = {'va':hex(i.address),'raw':i.bytes.hex(),'asm':i.mnemonic+' '+i.op_str}
            if i.mnemonic in ('b','bl') and i.op_str.startswith('#'): row['symbol'] = self.plt.get(int(i.op_str[1:],16),'')
            rows.append(row)
        return rows
    def xrefs(self, target):
        out = []
        for sec in self.e.iter_sections():
            if not sec['sh_flags']&4: continue
            b = sec.data(); base = sec['sh_addr']
            for k,(w,) in enumerate(struct.iter_unpack('<I',b[:len(b)//4*4])):
                if w&0x7c000000!=0x14000000: continue
                imm = w&0x3ffffff
                if imm&(1<<25): imm-=1<<26
                va = base+k*4
                if va+4*imm==target: out.append(hex(va))
        return {'calls':out,'pointers':[hex(k) for k,v in self.ptrs.items() if v==target]}

def main():
    if len(sys.argv)>1:
        mode,name,*args = sys.argv[1:]; im = Image(name)
        if mode=='dis':
            for row in im.dis(int(args[0],16),int(args[1],16)): print(row['va'],row['asm'],row.get('symbol',''))
        elif mode=='str':
            for va in args: print(va,im.string(int(va,16)))
        elif mode=='xref':
            for va in args: print(va,json.dumps(im.xrefs(int(va,16))))
        elif mode=='sym':
            for k,v in im.sym.items():
                if re.search(args[0],k,re.I): print(k,hex(v[0]),hex(v[1]))
        return
    rebuild()

def rebuild():
    proof = {'scope':'AP83a r4 offline evidence; no QEMU/guest/device execution or runtime write',
             'line_convention':'1-based LF only, CR stripped for presentation; review JSON line numbers are not reused',
             'sources':{},'code':[],'checks':[]}
    def source(path):
        b = path.read_bytes()
        proof['sources'][str(path.relative_to(ROOT))] = {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
        return b
    def checked(im, va, asm):
        got = im.dis(va,4)[0]
        assert got['asm']==asm, (im.name,hex(va),got,asm)
        proof['checks'].append({'image':im.name,**got})
    images = {k:Image(k) for k in ['appFw.so','libObj.so','libosal_uipc.so','libc-2.25.so']}
    images['trace'] = Image(str(RT/'helpers/ioctl-trace-v12.so'))
    expected = {'appFw.so':'545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f',
        'libObj.so':'c4681d209a7fe2ed63752be3b0be89ab7b7ce400679c00068c8c6e47d39f83ae',
        'libosal_uipc.so':'09ebf5980237fc473077dc844763dcb00cba423f431646e3be7c0ca49ea70ff3',
        'libc-2.25.so':'f9104526eb7e5d2ea533c1a209bb0b83e69367f569e4c966895c8e106e6382c9',
        'trace':'f2799333d67b4b118634e273f50f7d48106a228c1c40132075d923f040ca0b74'}
    for k,im in images.items(): assert hashlib.sha256(source(im.path)).hexdigest()==expected[k]
    windows = {
        'appFw.so':[(0x16f1998,0xb0),(0x16f2478,0x18),(0x16f25ec,0xb0),
            (0x2de70a8,0x2a8),(0x2d95948,0x134),(0x2dcfc94,0x40),(0x2de9de4,0x38c),
            (0x2d2f290,0x80),(0x2d2f404,0xc),(0x2d2f6f4,0x258),(0x2d2fed8,0xc),
            (0x2d1dc50,0x30),(0x2d1dd30,0xc4),(0x2d11dd4,0xbc)],
        'libObj.so':[(0x16ea10,0xd4),(0x15d8e8,0x30),(0x15d6a4,0x38),(0x154bc8,0x2c),
            (0x1549fc,0x50),(0x154890,0x16c),(0x153f7c,0x38),(0x1543a8,0x4c),
            (0xf3604,0x3c),(0xf2e80,8),(0xf2210,0x28),(0xfd344,0x50),(0xf2428,0x150),
            (0xf2638,0x1a0),(0xf22f0,0x28),(0xf2238,0xb8),(0xf2820,0x110),
            (0xf2fa0,0xe4),(0xf1fbc,0x8c),(0xf25f4,0x44),(0xf1d90,0x8c),(0xf1e1c,0x80)],
        'libosal_uipc.so':[(0x4858,0x218),(0x37b0,0x70)],
        'libc-2.25.so':[(0xc1cb0,0x1c)], 'trace':[(0x10d74,0x60)]}
    for k,ws in windows.items():
        for va,n in ws:
            im=images[k]; rows=im.dis(va,n)
            assert sum(len(bytes.fromhex(x['raw'])) for x in rows)==n, (k,hex(va))
            proof['code'].append({'image':k,'va':hex(va),'length':n,'raw':im.read(va,n).hex(),'instructions':rows})
    a,o,u = (images[k] for k in ['appFw.so','libObj.so','libosal_uipc.so'])
    for k,va,asm in [
        ('appFw.so',0x16f1a1c,'bl #0x1593960'),('appFw.so',0x16f2640,'bl #0x16f1998'),
        ('libObj.so',0x16ea28,'bl #0x15d8e8'),('libObj.so',0x15d8f0,'ldr x0, [x0, #0x18]'),
        ('libObj.so',0x1543cc,'bl #0xf3604'),('libObj.so',0xf3620,'bl #0xf2e80'),
        ('libObj.so',0xf2e84,'b #0xf2210'),('libObj.so',0xf2224,'bl #0xfd344'),
        ('libObj.so',0xfd348,'mov w1, #-1'),('libObj.so',0xfd354,'bl #0x55670'),
        ('libObj.so',0xf2448,'bl #0xfd344'),('libObj.so',0xf227c,'bl #0xfd384'),
        ('libObj.so',0xf22cc,'bl #0xfd384'),('libObj.so',0xf22f4,'mov w3, #0x6003'),
        ('libObj.so',0xf2300,'mov w3, #0x6005'),('libObj.so',0xf28d8,'bl #0xf22f0'),
        ('libosal_uipc.so',0x37c4,'add x20, x29, #0x20'),('libosal_uipc.so',0x37dc,'mov x1, #-0x7fffffff'),
        ('trace',0x10d90,'sub sp, sp, #0x330'),('appFw.so',0x2dea0e0,'bl #0x2de70a8'),
        ('appFw.so',0x2d95a14,'bl #0x2dcfc94'),('appFw.so',0x2d2fedc,'bl #0x2d1b580')]:
        checked(images[k],va,asm)
    # Constructor-selected interface: table pointer is object+8, not its vtable.
    assert o.ptrs[0x261d70]==0x153f9c
    vt = o.ptrs[0x262ec8]+16
    assert o.ptrs[vt+0x28]==0x1543a8
    proof['graphics_callback_binding']={'interface_getter':'154bc8 ->1549fc singleton +8',
        'initializer':'154890..1549f8', 'interface_slot_18':{'constructor_store':'1548f4','GOT':hex(0x261d70),'value':hex(o.ptrs[0x261d70])},
        'virtual_dispatch':'153f9c ->vtable+28', 'vtable':hex(vt),'slot':hex(vt+0x28),'target':hex(o.ptrs[vt+0x28])}
    proof['strings']=[{'image':'appFw.so','va':hex(v),'value':a.string(v)} for v in [0x3953db8,0x3967ae0,0x3937760]]
    raw = source(RUN/'serial.log'); lines=raw.decode(errors='replace').split('\n')
    def rows(lo,hi):return [{'line':i+1,'text':lines[i].rstrip('\r')} for i in range(lo,hi)]
    def matching(pattern,lo=0,hi=None):
        return [r for r in rows(lo,len(lines) if hi is None else hi) if re.search(pattern,r['text'])]
    def ix(marker,start=0): return next(i for i in range(start,len(lines)) if lines[i].rstrip('\r')==marker)
    snapshots=[]
    for turn in [1,2,3]:
        start=ix(f'FX3_AP_SNAPSHOT_{turn}_BEGIN');end=ix(f'FX3_AP_SNAPSHOT_{turn}_END',start)
        tasks=[]
        for i in range(start,end):
            match=re.fullmatch(r'FX3_TASK_SNAPSHOT_(\d+)_BEGIN\r?',lines[i])
            if not match:continue
            tid=int(match[1]);stop=ix(f'FX3_TASK_SNAPSHOT_{tid}_END',i)
            def field(prefix):
                hits=[(j+1,lines[j].split(':',1)[-1].strip()) for j in range(i+1,stop) if lines[j].startswith(prefix)]
                return {'line':hits[0][0],'value':hits[0][1]} if hits else None
            syscalls=[r for r in rows(i,stop) if re.match(r'^(29|98) ',r['text'])]
            task={'tid':tid,'name':field('Name:'),'state':field('State:'),'range':[i+1,stop+1],
                  'syscalls':syscalls,'wchan_explicit':None,'snapshot':rows(i,stop+1)}
            tasks.append(task)
        maps=matching(r' /(?:usr/)?lib/(?:appFw|libObj|libosal|libc-|libpthread|libstdc\+\+)',start,end)
        snapshots.append({'turn':turn,'range':[start+1,end+1],'tasks':tasks,'selected_maps':maps})
    proof['snapshots']=snapshots
    proof['wchan_limit']='No separate wchan field/file in this run; wait functions come from saved kernel stack, not invented user stacks.'
    key=lambda task: task['name'] and (task['name']['value'].startswith('SeqQueue') or task['name']['value'] in ['AppFw','ExternalOSDIF','grm_gpe','grm_result','MPGRM_GPE0','MPGRM_GPE0_COMP','SeqThreadPool1','uipc_proxy_0'])
    proof['last_key_threads']=[{k:v for k,v in t.items() if k!='snapshot'} for t in snapshots[-1]['tasks'] if key(t)]
    maps=snapshots[-1]['selected_maps']
    proof['image_bases']={}
    for label,base,name in [('AP',0x7f5526e000,'appFw.so'),('Obj',0x7f9c70c000,'libObj.so'),('libc',0x7fa9449000,'libc-2.25.so'),('pthread',0x7fa9c2b000,'libpthread-2.25.so')]:
        hits=[r for r in maps if name in r['text'] and r['text'].startswith(f'{base:x}-')]
        assert hits,(label,hex(base),name)
        proof['image_bases'][label]={'base':hex(base),'evidence':hits[0]}
    gate=source(RUN/'ui-gate-counters.bin');h=struct.unpack_from('<8Q',gate)
    assert h[0]==0x3145544147335846 and h[1]==2 and h[2] in [0,1]
    vals=struct.unpack_from('<96Q',gate,0x100+h[2]*0x1000)
    names=['peak_all','peak_gate','field_samples']+[f'hist_{i}' for i in range(6)]+[f'gate_hist_{i}' for i in range(6)]+['system_false','backlog_skip','time_skip','time_pass','dequeue_total','timer_dequeue','a12_nonzero','a13_nonzero','last_object','last_a18','last_a12','last_a13','first_ns','last_ns','mirror_skip','selftest','bound']
    counts={str(i):v for i,v in enumerate(vals[:64])};stats=dict(zip(names,vals[64:]));assert len(names)==32
    old=json.loads(source(RT/'ap83ar4-gate-readback.json'))
    assert counts==old['counts'] and stats==old['statistics']
    assert (counts['4'],counts['5'],counts['8'],counts['9'],counts['10'],counts['11'])==(561,561,2,12853,532,561)
    records=[]
    fields=['id','n','tid','pc','x0','x1','x2','x3','x4','x19','x20','x21','x22','x25','x26','x27','x28','fp','token_or_req','create_sequence','create_function','completion_sequence','completion_handle','commit']
    for i in range(h[5]):
        off=0x4000+i*192 if i<64 else 0xd000+(i-64)*192
        rec=dict(zip(fields,struct.unpack_from('<24Q',gate,off)))
        assert rec['commit']==0x544f4f4245544147
        records.append(rec)
    proof['gate']={'header':h,'counts':counts,'statistics':stats,'boot_records':records,
        'bank_offset':hex(0x100+h[2]*0x1000),'limit':'Latest completed mirror, not a user-memory/sem-ID dump; last_ns updates only at sampled logging, not stop time.'}
    # Strong constrained fit: every frame and the ioctl argument offset are original code.
    mainfp=next(r['fp'] for r in records if r['id']==40 and r['tid']==289)
    chain=[('appFw 16f1998',0x30),('libObj 16ea10',0x40),('libObj 1543a8',0x20),
        ('libObj f3604',0x10),('libObj f2210',0x20),('libObj fd344',0x10),
        ('libosal 4858',0x160),('libosal 37b0',0x30),('ioctl-trace 10d74',0x390),('libc c1cb0',0)]
    assert sum(n for _,n in chain)==0x5f0
    fits=[]
    for snap in snapshots[1:]:
        t=next(t for t in snap['tasks'] if t['tid']==289);sr=t['syscalls'][0];v=sr['text'].split()
        assert v[0]=='29' and int(v[2],16)==0xffffffff80000001
        sp,ptr=int(v[-2],16),int(v[3],16)
        assert mainfp-sp==0x5f0 and ptr==sp+0x390+0x20
        assert int(v[-1],16)-0x7fa9449000==0xc1cbc
        fits.append({'turn':snap['turn'],'syscall':sr,'main_fp':hex(mainfp),'sp':hex(sp),'ioctl_arg':hex(ptr),
                     'delta':hex(mainfp-sp),'argument_delta':hex(ptr-sp)})
    proof['UI_wait_fit']={'grade':'B strong; no saved caller LR/sem ID or complete user stack',
        'chain':[(k,hex(v)) for k,v in chain],'fits':fits,
        'release':'ExternalOSDIF f22f0 dispatches 6003/6005 to f2238/f22b0; both signal its +48 semaphore; f2428 consumes same semaphore before posting first frame.'}
    tags=r'FX3_(?:UUD_|CHANGE_MODE_INPUT|FACE_(?:DMM_(?:COMMIT|CONSUMED)|ICDT_(?:COMMIT|CONSUMED))|PIN_(?:COMMIT|CONSUMED)|BOOT_EVENT_LINK|BOOT_CV_|TIMER_(?:ENTRY|ID |TABLE|INFO |RETURN)|UI_WIRE|UI_FILL_|GPE_(?:CMD|RAW)|VDF_PLANE_COMMIT|MONITOR_LUT_COMMIT)'
    proof['serial_evidence']=matching(tags)
    updates=matching(r'FX3_UI_GATE_SAMPLE id=8 ');assert len(updates)==2
    proof['updates_and_observation_stats']=updates+matching(r'FX3_UI_GATE_SAMPLE id=(?:4|5|6|9|10|11) ')[-12:]+matching(r'FX3_UIPC_OBSERVER_END pid=202 ')[-1:]+matching(r'FX3_TIMER_OBSERVER_END pid=202 ')[-1:]
    cmds=matching(r'FX3_GPE_CMD ');assert len(cmds)==2 and 'op=FillRect' in cmds[0]['text'] and 'op=Flush' in cmds[1]['text']
    proof['GPE_commands']=cmds
    assert not matching(r'FX3_UI_GATE_SAMPLE id=(?:4|5|6|7|8|10|11) ',updates[1]['line'])
    raw_frame=source(RUN/'osd-draw-0001.raw')
    proof['frame_readback']={'bytes':len(raw_frame),'all_zero':not any(raw_frame),'warning':'Host snapshot length is 1228800; native fmt0/640x480 payload is 614400. Do not infer RGBA32 native format from dump length.'}
    # Freeze complete observed request and its real, interleaved stack by FP region.
    ri=next(i for i,x in enumerate(lines) if 'FX3_PROVIDER_REQUEST destination=0x92840747 bytes=16' in x and 'raw=0d205201' in x)
    raw_request=re.search(r'raw=([0-9a-f]+)',lines[ri])[1]
    assert raw_request=='0d205201100001800300010000eb8080'
    begin=next(i for i in range(ri-100,ri) if 'FX3_PROFILE_STACK_BEGIN destination=0x92840747 header=0x152200d tid=327' in lines[i])
    stack=[r for r in rows(begin,ri+1) if 'FX3_PROFILE_FRAME' in r['text'] and re.search(r'fp=0x7f41fe7',r['text'])]
    assert len(stack)==9
    proof['pending_sync']=[{'grade':'A request/static wait, B attribution of unchanged final receive wait',
        'thread':'SeqQueueCommon','tid':327,'destination':'0x92840747','source':'0x81cf61c2',
        'request':rows(ri,ri+1)[0],'raw':raw_request,'purpose':'sequence_set_peaking -> vdf_set_peaking',
        'timeout':-1,'expected_reply_bytes':12,'expected_reply_command':'0x1152 (header pairing; status semantics not reconstructed here)',
        'stack':stack,'interleaved_context':rows(begin,ri+2),
        'limit':'Trailing four request bytes may include initialized/unspecified colour state; no generic success reply proposed.'}]
    proof['no_wait_0500']=matching(r'FX3_PROVIDER_REQUEST destination=0x92840747 bytes=10.*raw=0d200005')
    proof['reply_observation_limit']='UIPC observer reached 256 capacity, 143 drops; absence of a logged receive/reply alone is not proof. Use static synchronous call and stable final wait; no exhaustive absent-reply claim for other threads.'
    proof['mode']={'observed_inputs':matching(r'FX3_(?:CHANGE_MODE_INPUT|UUD_CHANGE_MODE_INPUT)'),
        'param144_stores':matching(r'FX3_UUD_PARAM144_STORE'),
        'face_enter_return':matching(r'FX3_UUD_FACE_(?:ENTER|RETURN)'),
        'verdict':'mode2/option6 requested and face entry returned; common face preparation completed far enough to dispatch separate peaking task, so mode-transition completion is strongly supported, but current mode/current option were not dumped. No later option0 write or normal-mode input captured; ordinary shooting standby is not accepted.',
        'next_observed_task':'sequence_set_peaking, blocked on VDF0152; do not confuse with a new change_mode or completed live-view start'}
    proof['notification_observations']={p:matching(re.escape(p)) for p in ['0x1142','0x1160','pending_f024=1','pending_f029=1','0x6003','0x6005']}
    ptxt=source(RUN/'printk-decoded.txt').decode(errors='replace').split('\n')
    proof['printk']={'line_count':len(ptxt),'last_osal_errors':[{'line':i+1,'text':x} for i,x in enumerate(ptxt) if 'osal_snd_msg' in x][-12:],
        'limit':'Finite ring retained tail only; no independent user-stack or notification payload recovery.'}
    for f in ['receipt.json','osd-draws.json','command.json','printk-decode-observer.json']:source(RUN/f)
    for f in ['fx3-ui-gate-v11.c','fx3-ui-gate-v11.so','ioctl-trace-v12.c']:source(RT/'helpers'/f)
    br=json.loads(source(RT/'ap83a-face-dmm-realcopy-r4/build-receipt.json'))
    assert hashlib.sha256((RT/'helpers/fx3-ui-gate-v11.so').read_bytes()).hexdigest()=='54eeed923a6412cd2c6743f6e8c968d1ede71b92aa79aca4575868ebccc4a9ec'
    reference=RT.parent/'success-cases/source/runtime/analysis'
    for f in ['headless-osd.c','headless-osd.h']:source(reference/f)
    source(RT.parent/'success-cases/a7c2-main.json')
    proof['A7C2_reference']={'commit':'b3d7c1fed349f1d918acc4259f1d2b3a7c52a500',
        'source':'Existing local fixed-source snapshot; not executed or recopied',
        'comparison':'hosd_step waits serially for 1002 + matching 1003/1005, leases/captures/persists AP pixels and only then sends 8B 6003/6005 source74d to76c. Its offsets/format/geometry must be rederived for FX3.'}
    proof['open_items']=['No final user FP/LR chain or semaphore ID/object identity dump: UI attribution remains B strong despite two exact independent address fits.',
        'No captured current mode/current option property readback; no normal option0 transition accepted.',
        'No complete Widget visibility/dirty/raster resource state or first nonblack frame; frame completion can unblock but cannot promise menu content.',
        'No native FX3 6003 producer or complete 0152 CP handler/status conversion audited; proposed software consumer must claim only real AP snapshot consumption.',
        'No live-view/CP/VDF physical output, sensor readiness, panel scanout, original camera operation, or post-fix runtime acceptance.']
    path=OUT/'post-clear-idle-proof.json'
    path.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'proof':str(path),'checks':len(proof['checks']),'code_windows':len(proof['code']),
        'threads_last':len(proof['last_key_threads']),'UI_wait_grade':'B strong','GPE_commands':len(cmds),
        'pending_sync':'VDF0152/peaking','no_QEMU':True},ensure_ascii=False))

if __name__=='__main__': main()
