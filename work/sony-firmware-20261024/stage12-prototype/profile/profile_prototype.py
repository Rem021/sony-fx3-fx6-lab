#!/usr/bin/env python3
"""Experimental, memory-only AArch64 profile bridge. Never produces firmware.

The only candidate selector is ordinary movie + format6 + typed HS frame2.
No product/menu, full model, persistence, query, Start or hardware acceptance.
Hooks deny/log and resolve approved pure-local PLT linkage. The explicit legacy
single-address logging adapter is recorded; no encoder/field-output stubs.
"""
from pathlib import Path
import sys, json, struct, hashlib, subprocess, plistlib, datetime, re

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
B11 = ROOT / 'work/sony-firmware-20261024/stage11-model/builder'
M10 = ROOT / 'work/sony-firmware-20261024/stage10-mainpath/main'
V4 = ROOT / 'work/sony-firmware-20261024/stage4-windows-collab/mac-verification'
sys.path[:0] = [str(B11), str(M10), str(V4)]
from audit_typed_builder import Image
from offline_verify import Native, Micro, APP, MPR, SCRATCH, STACK, STACK_BASE, STACK_SIZE, STOP, read32, PACKET_RANGES
from unicorn import UC_PROT_READ, UC_PROT_EXEC
from unicorn.arm64_const import UC_ARM64_REG_X0, UC_ARM64_REG_X1, UC_ARM64_REG_X19, UC_ARM64_REG_X24, UC_ARM64_REG_X29, UC_ARM64_REG_PC, UC_ARM64_REG_LR

CODE = 0x0a000000  # New guest-only mapping beyond app PT_LOAD, not a static cave.
BUILDER_ENTRY, BUILDER_SITE = 0x2beae8c, 0x2bee8a0
SETTER_ENTRY, SETTER_SITE, SETTER_END = 0x2e6ea58, 0x2e6ed04, 0x2e6f040
FRAMEGET, Q60, Q24, Q120 = 0x2934d14, 0x2934e54, 0x2934e7c, 0x2934ea4
COUNT, TIMEOUT_US = 2000, 100000

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def p32(v): return struct.pack('<I', v & 0xffffffff)

class Asm:
    """Tiny, checked encoders for just the guest trampoline instruction subset."""
    def __init__(self, base): self.base, self.words, self.labels, self.fixups = base, [], {}, []
    @property
    def pc(self): return self.base + len(self.words)*4
    def emit(self, word): self.words.append(word)
    def label(self, name): self.labels[name] = self.pc
    def branch(self, target, cond=None, link=False):
        self.fixups.append((len(self.words), target, cond, link)); self.emit(0)
    def mov(self, rd, imm):
        assert 0 <= imm < 65536; self.emit(0x52800000 | imm << 5 | rd)
    def ldr(self, rd, rn, offset):
        assert offset % 4 == 0; self.emit(0xb9400000 | (offset//4) << 10 | rn << 5 | rd)
    def str(self, rd, rn, offset):
        assert offset % 4 == 0; self.emit(0xb9000000 | (offset//4) << 10 | rn << 5 | rd)
    def cmp(self, rn, imm): self.emit(0x7100001f | imm << 10 | rn << 5)
    def finish(self):
        for index, target, cond, link in self.fixups:
            dest = self.labels[target] if isinstance(target, str) else target
            delta = dest - (self.base+index*4); assert delta % 4 == 0
            n = delta//4
            if cond is None:
                assert -(1 << 25) <= n < 1 << 25
                self.words[index] = (0x94000000 if link else 0x14000000) | (n & 0x3ffffff)
            else:
                assert -(1 << 18) <= n < 1 << 18 and not link
                self.words[index] = 0x54000000 | (n & 0x7ffff) << 5 | cond
        return b''.join(p32(w) for w in self.words)

def trampolines(im):
    # Original ordinary/still format dispatcher: preserve original displaced SUB.
    a = Asm(CODE)
    a.branch(0x2bd0fe0, link=True); a.ldr(0, 0, 0)
    a.branch(0x2a4e6b0, link=True)  # Execute original pure movie predicate.
    a.cmp(0, 0); a.branch('stock', cond=0)
    a.cmp(19, 6); a.branch('stock', cond=1)
    a.cmp(27, 2); a.branch('stock', cond=1)
    for value, offset in [(15, 0x40), (6, 0x44), (2, 0x48)]:
        a.mov(0, value); a.str(0, 24, offset)
    a.str(31, 24, 0x4c)
    a.branch(0x2bec2f0)  # Real builder epilogue, never a host-supplied return.
    a.label('stock'); a.emit(struct.unpack('<I', im.read(BUILDER_SITE, 4))[0])
    a.branch(BUILDER_SITE+4)
    # HS420 setter site already establishes format6/color0. Still check full tuple.
    b = Asm(CODE+0x200)
    for offset, value in [(0x14, 6), (0x10, 15), (0x18, 2), (0x1c, 0)]:
        b.ldr(0, 24, offset); b.cmp(0, value); b.branch('stock', cond=1)
    b.mov(0, 6); b.branch(SETTER_SITE+4)
    b.label('stock'); b.emit(struct.unpack('<I', im.read(SETTER_SITE, 4))[0])
    b.branch(SETTER_SITE+4)
    return [(BUILDER_SITE, CODE, a.finish()), (SETTER_SITE, CODE+0x200, b.finish())]

class StrictMicro(Micro):
    def __init__(self, native, ranges, end=STOP, patches=(), resolve=False, logging_adapter=False):
        super().__init__(native, ranges, stubs={}, resolve_local=resolve)
        self.end, self.pcs, self.stores = end, [], []
        assert not logging_adapter or native is MPR
        self.logging_adapter = logging_adapter
        self.log_proofs, self.pending_log = [], None
        if logging_adapter: MPR.md.detail=True
        if patches:
            assert all(not (s['p_vaddr'] < CODE+4096 and CODE < s['p_vaddr']+s['p_memsz']) for s in native.segments)
            self.uc.mem_map(CODE, 4096, UC_PROT_READ|UC_PROT_EXEC)
            for site, address, raw in patches:
                self.uc.mem_write(address, raw)
                a=Asm(site); a.branch(address)
                self.uc.mem_write(site, a.finish())
                self.allowed.append((address,address+len(raw)))
    def code(self, u, a, n, user):
        self.pcs.append(hex(a))
        if self.logging_adapter and a == 0xc8c70:
            # Reuse the explicitly established stage4 log adapter only. No codec
            # passthrough, field writes or missing encoder implementation stubs.
            self.steps += 1
            ptr, length = u.reg_read(UC_ARM64_REG_X0), u.reg_read(UC_ARM64_REG_X1)
            if not (0 < length <= 0xfe0 and (STACK_BASE<=ptr and ptr+length<=STACK_BASE+STACK_SIZE or SCRATCH<=ptr and ptr+length<=SCRATCH+0x10000)):
                self.abort('unapproved logging input'); return
            ret=u.reg_read(UC_ARM64_REG_LR)
            self.pending_log={'callsite':hex(ret-4),'call_instruction_original_bytes':MPR.read(ret-4,4).hex(),'return_pc':hex(ret),'trace_until_x0_killed_or_return':[],'status':'pending'}
            self.log_proofs.append(self.pending_log)
            self.calls.append({'logging_adapter':'0xc8c70','guest_log_packet':bytes(u.mem_read(ptr,length)).hex(),'register_or_memory_return_value_written':False,'output_fields_written':False})
            self.ret(); return  # PC <- LR only. In particular X0 is untouched.
        if self.pending_log:
            if a == STOP:
                self.pending_log['status']='returned without consuming x0; caller ignores this helper scalar return'
                self.pending_log=None
            else:
                ins=next(MPR.md.disasm(MPR.read(a,4),a))
                reads,writes=ins.regs_access()
                rn={ins.reg_name(x) for x in reads}; wn={ins.reg_name(x) for x in writes}
                self.pending_log['trace_until_x0_killed_or_return'].append({'pc':hex(a),'original_bytes':ins.bytes.hex(),'asm':ins.mnemonic+' '+ins.op_str,'reads':sorted(rn),'writes':sorted(wn)})
                if rn & {'x0','w0'}:
                    self.abort('logging return x0 consumed before overwrite'); return
                if wn & {'x0','w0'}:
                    self.pending_log['status']='original guest overwrites x0 before reading logging return'
                    self.pending_log=None
        if a == self.end and self.end != STOP:
            self.steps += 1; self.abort('conversion block complete'); return
        super().code(u,a,n,user)
    def write(self, u, access, a, n, value, user):
        super().write(u,access,a,n,value,user)
        self.stores.append({'pc':hex(u.reg_read(UC_ARM64_REG_PC)), 'address':hex(a), 'size':n, 'value':value & ((1 << (8*n))-1)})
    def run(self, entry, args=()):
        # Use one budget for every application block; MPR packet has its own 20k.
        import offline_verify
        old_count,old_time=offline_verify.COUNT_LIMIT,offline_verify.TIMEOUT_US
        offline_verify.COUNT_LIMIT,offline_verify.TIMEOUT_US=COUNT,TIMEOUT_US
        try: r=super().run(entry,args)
        finally: offline_verify.COUNT_LIMIT,offline_verify.TIMEOUT_US=old_count,old_time
        if self.pending_log and r['reason']=='returned':
            assert self.pending_log['trace_until_x0_killed_or_return'][-1]['asm'].startswith('ret')
            self.pending_log['status']='returned without consuming x0; caller ignores this helper scalar return'
            self.pending_log=None
        r.update(pcs=self.pcs,stores=self.stores,stop_pc=hex(self.uc.reg_read(UC_ARM64_REG_PC)),instruction_limit=COUNT,timeout_us=TIMEOUT_US,logging_return_nonconsumption_proofs=self.log_proofs)
        return r

def builder(im, patches, frame, q60=12, q24=17, q120=9, fmt=6, exposure=5, poison=False):
    leaves=json.loads((B11/'model-leaf-accessors.json').read_text())['accessors']
    leafaddrs={int(x['accessor'],16) for x in leaves}|{0x2934c9c,0x29353a4,0x293d90c}
    ranges=[(BUILDER_ENTRY,0x2beea04),(0x2bd0fb0,0x2bd0ff8),(0x2a4e5e0,0x2a4e600),(0x2a4e6b0,0x2a4e6e4),(0x2a4e794,0x2a4e7cc),(0x2a4e87c,0x2a4e880)]+[(a,a+20) for a in leafaddrs]
    m=StrictMicro(APP,ranges,patches=patches[:1])
    values={0x2934c9c:fmt,0x293d90c:exposure,FRAMEGET:frame,Q60:q60,Q24:q24,Q120:q120}
    for a in leafaddrs: m.uc.mem_write(im.leaf(a),p32(values.get(a,0)))
    defaults=[15,6,24,0] if not poison else [0xfefefefe]*4
    m.uc.mem_write(SCRATCH+0x40,struct.pack('<4I',*defaults))
    r=m.run(BUILDER_ENTRY,[SCRATCH,0]); blob=bytes(m.uc.mem_read(SCRATCH,0x1000))
    r.update(synthetic_input={'typed_frame':frame,'q60':q60,'q24':q24,'q120':q120,'format':fmt,'exposure':exposure,'all_other_model_slots':0},constructor_executed=False,initial_builder_tuple=defaults,builder_tuple=list(struct.unpack('<4I',blob[0x40:0x50])),full_builder_sha256=hashlib.sha256(blob).hexdigest())
    return r

def setter(im, patches, values):
    frame,fmt,q,color=values
    m=StrictMicro(APP,[(SETTER_ENTRY,SETTER_END),(0x2e6f45c,0x2e6f494)],end=SETTER_END,patches=patches[1:])
    base=STACK_BASE+0x10000
    m.uc.mem_write(SCRATCH+0x10,struct.pack('<4I',*values))
    for reg,val in [(UC_ARM64_REG_X24,SCRATCH),(UC_ARM64_REG_X29,base),(UC_ARM64_REG_X19,base+0x310)]: m.uc.reg_write(reg,val)
    r=m.run(SETTER_ENTRY)
    r.update(input_builder_tuple=values,output_vpc_quality_frame=list(struct.unpack('<3I',bytes(m.uc.mem_read(base+0x480,12)))))
    return r

def allowed_cases(im):
    """Derive sets from stage11 raw JSON, cross-check each instruction with ELF."""
    source=json.loads((B11/'builder-static.json').read_text())
    ins=source['builder']
    for row in ins:
        assert im.read(int(row['va'],16),4).hex()==row['bytes']
    def comparisons(start,end,reg):
        return sorted({int(r['asm'].split('#')[1],0) for r in ins if start<=int(r['va'],16)<end and r['asm'].startswith('cmp '+reg+', #')})
    q60=comparisons(0x2bec4c4,0x2bec55c,'w21')
    tables=json.loads((B11/'selection-tables.json').read_text())['tables']
    table=next(t for t in tables if t['va']=='0x392f978')
    assert im.read(int(table['va'],16),12).hex()==table['raw']
    q24=[16+i for i,t in enumerate(table['targets']) if t!='0x2bec610']
    q120=comparisons(0x2bec670,0x2bec684,'w0')
    assert [q60,q24,q120]==[[8,12,16,21,26],[16,17,23,24,27],[4,9]]
    cases=[{'frame':f,**{key:q}} for frames,key,qs in [([0,1],'q60',q60),([4],'q24',q24),([5,6],'q120',q120)] for f in frames for q in qs]
    return {'source':'stage11-model/builder/builder-static.json and selection-tables.json; every source instruction/table cross-checked against pinned original ELF','quality60_50':q60,'quality24':q24,'quality120_100':q120,'cases':cases}

def mpr_call(entry,end,args,prepare=None,logging_adapter=False):
    m=StrictMicro(MPR,[(entry,end)],resolve=True,logging_adapter=logging_adapter)
    if prepare: prepare(m.uc)
    return m.run(entry,args),m

def downstream(tuple_vqf,logging_adapter=False):
    vpc,quality,frame=tuple_vqf
    def prepare(u): u.mem_write(SCRATCH+0x170,struct.pack('<3I',*tuple_vqf))
    validator,m=mpr_call(0xcc4d4,0xcc824,[SCRATCH],prepare,logging_adapter)
    codec,m=mpr_call(0xcd40c,0xcd4f8,[vpc,0],logging_adapter=logging_adapter)
    bitrate,m=mpr_call(0x2c0ce0,0x2c0d04,[quality],logging_adapter=logging_adapter)
    rational,m=mpr_call(0x2c0de8,0x2c0e98,[frame,SCRATCH,SCRATCH+4],logging_adapter=logging_adapter)
    rational.update(numerator=read32(m.uc,SCRATCH),denominator=read32(m.uc,SCRATCH+4))
    m=StrictMicro(MPR,list(PACKET_RANGES),resolve=True,logging_adapter=logging_adapter)
    m.uc.mem_write(SCRATCH+0x764,struct.pack('<4I',*tuple_vqf,0))
    packet=m.run(0xd13f8,[SCRATCH,SCRATCH+0x2000])
    raw=bytes(m.uc.mem_read(SCRATCH+0x2000,0x98))
    packet.update(packet_hex=raw.hex(),fields={'codec':raw[0x66],'width':struct.unpack_from('<H',raw,0x68)[0],'height':struct.unpack_from('<H',raw,0x6a)[0],'frame_enum':raw[0x80],'ntsc_flag':raw[0x81],'quality_enum':raw[0x82],'chroma':raw[0x94],'bitdepth':raw[0x95]})
    return {'actual_guest_setter_output_copied_as_input':tuple_vqf,'stream_type':0,'logging_adapter':{'address':'0xc8c70','behavior':'read and record diagnostic message; PC<-LR only; no register return value or guest memory/output writes; dynamic original-byte proof of logging X0 nonconsumption','enabled':logging_adapter},'validator':validator,'main_codec':codec,'bitrate':bitrate,'rational':rational,'open_parameter_preparation':packet,'EncOpen_or_Start_executed':False,'manual_target_output_writes':False}

def main():
    volume=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
    assert volume['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
    im=Image(); before={str(n.path.relative_to(ROOT)):sha(n.path) for n in [APP,MPR]}
    dependencies=[B11/'builder-static.json',B11/'selection-tables.json',B11/'model-leaf-accessors.json',B11/'verify_typed_selection.py',M10/'verify_setter_conversion.py',V4/'offline_verify.py',V4/'engineering-note.txt',V4/'requirements.lock']
    dependency_hashes={str(p.relative_to(ROOT)):sha(p) for p in dependencies}
    assert im.read(BUILDER_SITE,4).hex()=='61160051' and im.read(SETTER_SITE,4).hex()=='a0008052'
    patches=trampolines(im); allowed=allowed_cases(im); legit=[]
    for case in allowed['cases']:
        stock=builder(im,[],**case); candidate=builder(im,patches,**case)
        assert stock['reason']==candidate['reason']=='returned'
        assert stock['full_builder_sha256']==candidate['full_builder_sha256']
        st=setter(im,[],stock['builder_tuple']); pt=setter(im,patches,candidate['builder_tuple'])
        assert st['reason']==pt['reason']=='conversion block complete'
        assert st['output_vpc_quality_frame']==pt['output_vpc_quality_frame']
        legit.append({'case':case,'stock_builder':stock,'prototype_builder':candidate,'stock_setter':st,'prototype_setter':pt,'unchanged':True})
    negatives=[]
    for case in [dict(frame=3),dict(frame=7),dict(frame=0,q60=2),dict(frame=4,q24=2),dict(frame=5,q120=2),dict(frame=2,exposure=0),dict(frame=2,fmt=7),dict(frame=2,fmt=8)]:
        stock=builder(im,[],**case); candidate=builder(im,patches,**case)
        assert stock['reason']==candidate['reason']
        assert stock['full_builder_sha256']==candidate['full_builder_sha256']
        negatives.append({'case':case,'stock':stock,'prototype':candidate,'unchanged':True})
    setter_controls=[]
    for values in [[15,8,2,0],[15,7,13,0],[15,6,2,1],[20,6,13,0],[15,6,13,0],[18,6,2,0],[15,13,2,0],[15,6,2,2]]:
        s=setter(im,[],values); p=setter(im,patches,values)
        assert s['reason']==p['reason'] and s['output_vpc_quality_frame']==p['output_vpc_quality_frame']
        setter_controls.append({'input':values,'stock':s,'prototype':p,'unchanged':True})
    stock_target=builder(im,[],frame=2)
    target=builder(im,patches,frame=2,poison=True)
    assert stock_target['reason']=='unapproved execution 2f6fe3c'
    assert target['reason']=='returned' and target['builder_tuple']==[15,6,2,0]
    # All four target fields must have been written by guest instructions.
    for offset in [0x40,0x44,0x48,0x4c]:
        assert any(int(w['address'],16)==SCRATCH+offset for w in target['stores'])
    target_setter=setter(im,patches,target['builder_tuple'])
    assert target_setter['reason']=='conversion block complete' and target_setter['output_vpc_quality_frame']==[6,6,3]
    strict_chain=downstream(target_setter['output_vpc_quality_frame'])
    for name in ['validator','main_codec','open_parameter_preparation']:
        assert strict_chain[name]['reason']=='unapproved execution c8c70'
    chain=downstream(target_setter['output_vpc_quality_frame'],logging_adapter=True)
    for name in ['validator','main_codec','bitrate','rational','open_parameter_preparation']: assert chain[name]['reason']=='returned',(name,chain[name])
    for name in ['validator','main_codec','open_parameter_preparation']:
        assert all(p['status']!='pending' for p in chain[name]['logging_return_nonconsumption_proofs'])
    assert chain['validator']['return_u32']==0 and chain['main_codec']['return_u32']==15
    assert chain['bitrate']['return_u32']==16000
    assert [chain['rational'][x] for x in ['numerator','denominator']]==[30000,1001]
    assert chain['open_parameter_preparation']['fields']=={'codec':15,'width':1920,'height':1080,'frame_enum':3,'ntsc_flag':1,'quality_enum':22,'chroma':0,'bitdepth':1}
    after={str(n.path.relative_to(ROOT)):sha(n.path) for n in [APP,MPR]}
    assert before==after and dependency_hashes=={str(p.relative_to(ROOT)):sha(p) for p in dependencies}
    disassembly=[]
    for site,address,raw in patches:
        disassembly.append({'original_site':hex(site),'scratch_mapping':hex(address),'instruction_count':len(raw)//4,'scratch_sha256':hashlib.sha256(raw).hexdigest(),'assembly':[{'pc':hex(i.address),'asm':i.mnemonic+' '+i.op_str} for i in im.md.disasm(raw,address)]})
    report={'status':'PASS bounded experimental bridge only; goal remains unachieved','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'selector':{'experimental':True,'ordinary_movie_only':True,'setting_file_format':6,'typed_HS_frame':2,'fixed_quality_color':'16M HEVC42010; setter input quality2/color0; unrelated to typed quality2(400M)','menu_exposure_added':False,'coherent_full_mode_claimed':False},'volume_uuid':volume['VolumeUUID'],'source_before':before,'source_after':after,'dependencies_unchanged':dependency_hashes,'patches_in_guest_memory_only':disassembly,'static_cave_or_install_address_verified':False,'firmware_or_patchfile_exported':False,'logging_adapter':chain['logging_adapter'],'encoder_or_field_output_stubs':[],'hooks':'deny/log; approved pure-local PLT linkage only; single explicit stage4 logging adapter; no expected encoding/output fields','application_instruction_budget':COUNT,'timeout_us_each':TIMEOUT_US,'source_allowed_sets':allowed,'legitimate_HS_cases':legit,'builder_negative_and_other_format_controls':negatives,'setter_controls':setter_controls,'stock_target':stock_target,'experimental_target':target,'experimental_target_setter':target_setter,'strict_no_adapter_negative':strict_chain,'actual_guest_output_to_MPR':chain,'not_executed':['full model sequence','menu/product allowlist','derived format classification','query/remain conversion','persistence/re-entry','full setter','SetMovieRecParam/full route','EncOpen/Start','hardware encoder','writer/mux/bitstream','camera/USB/UI/auth/files/module/driver/WBI/flash','restore/recovery acceptance'],'source_original_unchanged':True,'goal_achieved':False}
    (OUT/'profile-results.json').write_text(json.dumps(report,indent=2)+'\n')
    (OUT/'source-receipt.json').write_text(json.dumps({'volume_uuid':volume['VolumeUUID'],'source_before':before,'source_after':after,'dependencies_unchanged':dependency_hashes,'script_sha256':sha(Path(__file__)),'results_sha256':sha(OUT/'profile-results.json'),'status':'PASS','test_counts':{'legitimate_HS_stock_vs_prototype':len(legit),'builder_negative_and_other_format':len(negatives),'setter_controls':len(setter_controls),'target_chain':1},'goal_achieved':False},indent=2)+'\n')
    print('PASS 19 legitimate HS combinations unchanged; 8 builder controls; 8 setter controls; experimental guest target -> [15,6,2,0] -> [6,6,3] -> MAIN codec15,1920x1080,42010,16000 raw,30000/1001. No Start/hardware/recovery.')

if __name__=='__main__': main()
