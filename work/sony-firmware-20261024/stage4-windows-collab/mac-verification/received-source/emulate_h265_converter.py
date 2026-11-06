"""Bounded, device-free ARM64 micro-emulation of selected firmware functions.

Only listed instruction ranges may execute. No OS/syscall bridge, device,
filesystem, process, network or complete camera application is exposed.
The unloaded C++ bitrate hash map is replaced by a documented lookup adapter.
"""
from fx3_native import *
import unicorn
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_INVALID
from unicorn.arm64_const import *
OUT=ROOT/'outputs/h265-path-research'
app=Native('/lib/appFw.so');mpr=Native('/lib/libmpr.so')
STACK_BASE=0x10000000;STACK_SIZE=0x40000;STACK=STACK_BASE+0x30000
SCRATCH=0x11000000;STOP=0x12000000
def p32(v):return struct.pack('<I',v&0xffffffff)
def u32(uc,addr):return struct.unpack('<I',uc.mem_read(addr,4))[0]

class Micro:
    def __init__(self,native,ranges,stubs=None):
        self.uc=Uc(UC_ARCH_ARM64,UC_MODE_ARM);self.native=native
        self.ranges=ranges;self.stubs=stubs or {};self.steps=0;self.reason=None;self.calls=[]
        pages=set()
        for start,end in ranges:
            pages.update(range(start&~4095,(end+4095)&~4095,4096))
        for addr in self.stubs:pages.add(addr&~4095)
        for page in sorted(pages):
            self.uc.mem_map(page,4096)
            try:self.uc.mem_write(page,native.read(page,4096))
            except ValueError:pass
        self.uc.mem_map(STACK_BASE,STACK_SIZE);self.uc.mem_map(SCRATCH,0x4000);self.uc.mem_map(STOP,4096)
        self.uc.reg_write(UC_ARM64_REG_SP,STACK);self.uc.reg_write(UC_ARM64_REG_LR,STOP)
        self.uc.hook_add(UC_HOOK_CODE,self.on_code)
        self.uc.hook_add(UC_HOOK_MEM_INVALID,self.on_bad_memory)
    def ret(self,value=None):
        if value is not None:self.uc.reg_write(UC_ARM64_REG_X0,value)
        self.uc.reg_write(UC_ARM64_REG_PC,self.uc.reg_read(UC_ARM64_REG_LR))
    def abort(self,reason):self.reason=reason;self.uc.emu_stop()
    def on_bad_memory(self,uc,access,address,size,value,user):
        self.reason=f'unmapped access {access} {address:x}+{size:x}';return False
    def on_code(self,uc,address,size,user):
        self.steps+=1
        if address==STOP:self.abort('returned');return
        if address in self.stubs:
            self.calls.append(hex(address));self.stubs[address](self);return
        if not any(a<=address<z for a,z in self.ranges):self.abort(f'non-whitelisted execution {address:x}');return
        word=u32(uc,address)
        if word&0xffe0001f==0xd4000001:self.abort('SVC forbidden');return
    def run(self,entry):
        try:self.uc.emu_start(entry,STOP,timeout=2_000_000,count=10_000)
        except unicorn.UcError as e:
            if self.reason is None:self.reason='emulator error: '+str(e)
        if self.reason is None:
            self.reason='returned' if self.uc.reg_read(UC_ARM64_REG_PC)==STOP else 'instruction/time limit'
        return self.reason

def get_vquality(mbps):
    # Real MPR instructions, no logging or table adapter required.
    micro=Micro(mpr,[(0xc9c04,0xc9e84),(0x2e0000,0x2e1000)])
    micro.uc.reg_write(UC_ARM64_REG_X0,mbps)
    reason=micro.run(0xc9c04)
    return {'input_Mbps':mbps,'result_VQuality':micro.uc.reg_read(UC_ARM64_REG_X0)&0xffffffff,'reason':reason,'steps':micro.steps}

quality_results={n:get_vquality(n) for n in [30,45,50,75,100,150,200,280]}
if any(r['reason']!='returned' for r in quality_results.values()):
    print(json.dumps(quality_results,indent=2));raise SystemExit('MPR quality conversion did not complete')
literal_quality_pairs=list(struct.iter_unpack('<II',app.read(0x39898b0,0xd0)))
literal_quality_map=dict(literal_quality_pairs)
if any(literal_quality_map[n]!=r['result_VQuality'] for n,r in quality_results.items()):
    raise SystemExit('App literal quality map and MPR conversion disagree')

def convert(frame,quality,patched=False,sq=False):
    lookup=[]
    def mode(m):m.ret(1 if sq else 0)
    def bitrate_map(m):
        key=u32(m.uc,m.uc.reg_read(UC_ARM64_REG_X1))
        if key not in quality_results:m.abort('unmodelled bitrate map key '+str(key));return
        value=literal_quality_map[key];node=SCRATCH+0x1000
        m.uc.mem_write(node+0xc,p32(value));lookup.append({'Mbps_key':key,'VQuality':value,'provider':'original app .rodata pairs at 0x39898b0..0x3989980, installed into map object by initialization call 0x1693dbc; checked against original MPR GetVQuality instructions'})
        m.ret(node)
    def assertion(m):m.abort('firmware assertion reached')
    micro=Micro(app,[(0x2e68048,0x2e69ef0),(0x3989000,0x398a000)],{0x2a4e798:mode,0x2e68010:bitrate_map,0x2f6fe3c:assertion})
    if patched:
        original=app.read(0x39895ae,1)
        if original!=b'\x0a':raise RuntimeError('Unexpected candidate source byte')
        micro.uc.mem_write(0x39895ae,b'\x53')
    args=[0,6,0,frame,0,0,0,0]
    for i,v in enumerate(args):micro.uc.reg_write(UC_ARM64_REG_X0+i,v)
    micro.uc.mem_write(STACK,b'\0'*0x300)
    for arg in [12,13,14]:micro.uc.mem_write(STACK+(arg-9)*8,struct.pack('<Q',quality))
    for offset,ptr in [(0x210,SCRATCH),(0x218,SCRATCH+4),(0x220,SCRATCH+8)]:micro.uc.mem_write(STACK+offset,struct.pack('<Q',ptr))
    micro.uc.mem_write(SCRATCH,p32(0xfeedf00d)*3)
    reason=micro.run(0x2e68048)
    return {'input_frame_ordinal':frame,'input_record_setting_ordinal':quality,'normal_or_SQ':'SQ' if sq else 'normal','candidate_memory_patch':patched,'reason':reason,'VideoParamComb':u32(micro.uc,SCRATCH),'DefStruct_FrameRate':u32(micro.uc,SCRATCH+4),'DefStruct_VQuality':u32(micro.uc,SCRATCH+8),'steps':micro.steps,'lookup_adapter':lookup}

cases=[]
for patched in [False,True]:
    for frame in [0,1,2,3,4,5,6,8]:
        for quality in [8,16,17,24,30]:cases.append(convert(frame,quality,patched))
checks=[]
for q in [8,16,17,24]:
    old=next(x for x in cases if not x['candidate_memory_patch'] and x['input_frame_ordinal']==2 and x['input_record_setting_ordinal']==q)
    new=next(x for x in cases if x['candidate_memory_patch'] and x['input_frame_ordinal']==2 and x['input_record_setting_ordinal']==q)
    checks.append({'record_setting':q,'original_30p_asserts':old['reason']=='firmware assertion reached','candidate_30p_returns_true_frame3':new['reason']=='returned' and new['DefStruct_FrameRate']==3})
for old in cases[:len(cases)//2]:
    if old['input_frame_ordinal']==2:continue
    new=next(x for x in cases if x['candidate_memory_patch'] and x['input_frame_ordinal']==old['input_frame_ordinal'] and x['input_record_setting_ordinal']==old['input_record_setting_ordinal'])
    checks.append({'unchanged_frame':old['input_frame_ordinal'],'record_setting':old['input_record_setting_ordinal'],'unchanged_result':all(old[k]==new[k] for k in ['reason','VideoParamComb','DefStruct_FrameRate','DefStruct_VQuality'])})
result={'engine':'Unicorn '+unicorn.__version__,'scope':'Isolated converter micro-emulation with selected instruction/data pages. Candidate is one byte changed only in volatile emulator memory. Not an encoder, codec stream, hardware or camera test.','quality_lookup_adapter':list(quality_results.values()),'original_app_quality_pairs':literal_quality_pairs,'candidate':{'ELF_VA':'0x39895ae','original':'0a','candidate_in_emulator_only':'53','meaning':'route only normal HS 4K 30p to existing 60/50 quality-selection branch; preserve actual frame ordinal'},'cases':cases,'checks':checks}
(OUT/'converter-emulation-results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('Quality map',quality_results)
print('Cases:',len(cases),'checks:',len(checks))
for r in cases:
    if r['input_frame_ordinal']==2 and r['input_record_setting_ordinal'] in [16,17]:print(r)
print('All checks',all(all(v for k,v in c.items() if isinstance(v,bool)) for c in checks))
