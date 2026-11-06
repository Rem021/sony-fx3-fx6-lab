"""Execute only MPR's parameter-packet preparation and pure local converters.
Never calls EncOpen, a device driver, a syscall bridge or a hardware emulator.
"""
from emulate_h265_converter import Micro,ROOT,OUT,mpr,SCRATCH,STACK,STOP,p32,u32
from fx3_native import *
from unicorn import *
from unicorn.arm64_const import *

symbols=mpr.symbols();defined={s['name']:s for s in symbols if s['defined'] and s['name']}
plt=mpr.plt();dependencies=[]
for i in mpr.instructions(0xd13f8,0xd166c):
    if i.mnemonic=='bl':
        address=int(i.op_str[1:],0);name=plt.get(address,'')
        dependencies.append({'callsite':hex(i.address),'branch_target':hex(address),'plt_name':name,'implementation_ELF_VA':defined.get(name,{}).get('VA')})
print('Dependencies',dependencies)
(OUT/'encoder-packet-local-dependencies.json').write_text(json.dumps(dependencies,indent=2),encoding='utf-8')

class PacketMicro:
    def __init__(self):
        self.uc=Uc(UC_ARCH_ARM64,UC_MODE_ARM);self.reason=None;self.steps=0;self.calllog=[]
        pages=set()
        for segment in mpr.elf.iter_segments():
            if segment['p_type']!='PT_LOAD':continue
            a=segment['p_vaddr']&~4095;z=(segment['p_vaddr']+segment['p_memsz']+4095)&~4095
            for page in range(a,z,4096):
                if page not in pages:self.uc.mem_map(page,4096);pages.add(page)
            self.uc.mem_write(segment['p_vaddr'],segment.data())
        self.resolved_data=[]
        for sec in mpr.elf.iter_sections():
            if sec.name not in ('.rela.dyn','.rela.plt'):continue
            symtab=mpr.elf.get_section(sec['sh_link'])
            for rel in sec.iter_relocations():
                kind=rel['r_info_type'];value=None
                if kind==1027:value=rel['r_addend']
                elif kind in (1025,1026):
                    sym=symtab.get_symbol(rel['r_info_sym'])
                    if sym['st_shndx']!='SHN_UNDEF':value=sym['st_value']+rel['r_addend']
                if value is not None:
                    self.uc.mem_write(rel['r_offset'],struct.pack('<Q',value))
                    self.resolved_data.append((rel['r_offset'],value))
        self.uc.mem_map(STACK-0x10000,0x20000);self.uc.mem_map(SCRATCH,0x10000);self.uc.mem_map(STOP,4096)
        self.uc.reg_write(UC_ARM64_REG_SP,STACK);self.uc.reg_write(UC_ARM64_REG_LR,STOP)
        self.allowed=[(0xd13f8,0xd166c)]
        # Only the statically referenced local conversion functions are admitted.
        for d in dependencies:
            if d['implementation_ELF_VA']:
                s=defined[d['plt_name']];a=int(s['VA'],16);self.allowed.append((a,a+s['size']))
        # These local helpers are reached by the admitted conversion functions.
        for s in symbols:
            if s['defined'] and (s['name'].startswith('_ZN3mpr5pconv') or s['name'].startswith('_ZN3mpr14Get') or s['name'].startswith('_ZN3mpr16Get') or s['name'].startswith('_ZN3mpr13Get')):
                a=int(s['VA'],16);self.allowed.append((a,a+s['size']))
        self.uc.hook_add(UC_HOOK_CODE,self.code)
        self.uc.hook_add(UC_HOOK_MEM_INVALID,self.invalid)
    def abort(self,r):self.reason=r;self.uc.emu_stop()
    def invalid(self,uc,access,address,size,value,user):self.reason=f'unmapped {access} {address:x}+{size:x}';return False
    def code(self,uc,address,size,user):
        self.steps+=1
        if address==STOP:self.abort('returned');return
        if address==0xc8c70:
            uc.reg_write(UC_ARM64_REG_X0,0);uc.reg_write(UC_ARM64_REG_PC,uc.reg_read(UC_ARM64_REG_LR));return
        if address in plt:
            name=plt[address]
            if name in defined:
                dest=int(defined[name]['VA'],16)
                if any(a<=dest<z for a,z in self.allowed):
                    self.calllog.append({'PLT':hex(address),'symbol':name,'local_target':hex(dest)})
                    uc.reg_write(UC_ARM64_REG_PC,dest);return
            self.abort('unapproved PLT '+name);return
        if not any(a<=address<z for a,z in self.allowed):self.abort(f'unapproved execution {address:x}');return
        if u32(uc,address)&0xffe0001f==0xd4000001:self.abort('SVC forbidden')
    def run(self,vpc,frame=3,quality=12):
        IN=SCRATCH;OUTPUT=SCRATCH+0x2000
        self.uc.mem_write(IN,b'\0'*0x1000);self.uc.mem_write(OUTPUT,b'\0'*0x1000)
        # Main stream fields in execEncOpen_t, observed in original ARM64 code.
        self.uc.mem_write(IN+0x764,struct.pack('<IIII',vpc,quality,frame,0))
        self.uc.reg_write(UC_ARM64_REG_X0,IN);self.uc.reg_write(UC_ARM64_REG_X1,OUTPUT)
        try:self.uc.emu_start(0xd13f8,STOP,timeout=2_000_000,count=20000)
        except UcError as e:
            if self.reason is None:self.reason='emulator error '+str(e)
        if self.reason is None:self.reason='returned' if self.uc.reg_read(UC_ARM64_REG_PC)==STOP else 'budget exhausted'
        raw=bytes(self.uc.mem_read(OUTPUT,0x98))
        return {'VideoParamComb':vpc,'FrameRate':frame,'VQuality':quality,'reason':self.reason,'steps':self.steps,'packet_hex':raw.hex(),'observed_fields':{'file_format_65':raw[0x65],'codec_66':raw[0x66],'width':struct.unpack_from('<H',raw,0x68)[0],'height':struct.unpack_from('<H',raw,0x6a)[0],'frame_enum_80':raw[0x80],'ntsc_flag_81':raw[0x81],'quality_enum_82':raw[0x82],'color_format_94':raw[0x94],'bit_depth_95':raw[0x95]},'local_link_resolution':self.calllog}

cases=[PacketMicro().run(vpc,frame) for vpc in [5,7] for frame in [3,7]]
checks={'all_parameter_builders_returned':all(c['reason']=='returned' for c in cases),'all_packets_keep_UHD_dimensions':all(c['observed_fields']['width']==3840 and c['observed_fields']['height']==2160 for c in cases),'30p_codec_frame_preserved':all(c['observed_fields']['frame_enum_80']==3 for c in cases if c['FrameRate']==3),'codec_and_quality_match_same_profile_60p':all(all(cases[i]['observed_fields'][f]==cases[i+1]['observed_fields'][f] for f in ['file_format_65','codec_66','quality_enum_82','color_format_94','bit_depth_95']) for i in [0,2])}
result={'scope':'Original SetEncOpenParam and pure local conversion instructions. Logging stubbed; same-library PLT and data relocations resolved. Input buffer addresses and nonessential flags are synthetic zeros. EncOpen/EncStart and hardware codec not called.','cases':cases,'checks':checks}
(OUT/'encoder-packet-emulation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
for c in cases:print(c['VideoParamComb'],c['FrameRate'],c['reason'],c['observed_fields'])
print(checks)
if not all(checks.values()):raise SystemExit('Encoder packet hypothesis not fully verified')
