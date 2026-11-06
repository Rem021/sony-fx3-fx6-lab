#!/usr/bin/env python3
"""Device-free FX3 7.02 selected-function replication. No native ELF execution.

Reads only fixed original ELF/ZIP paths; writes JSON diagnostics beside this file.
Guest address space is memory only. No host syscall, device, network, file or MMIO
forwarding exists. Code pages are guest read-only. Unknown execution/access stops.
"""
from pathlib import Path
import hashlib, io, json, struct, sys, time, zipfile
from elftools.elf.elffile import ELFFile
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
import unicorn
from unicorn import (Uc, UcError, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE,
                     UC_HOOK_MEM_INVALID, UC_HOOK_MEM_WRITE, UC_PROT_READ,
                     UC_PROT_WRITE, UC_PROT_EXEC)
from unicorn.arm64_const import (UC_ARM64_REG_X0, UC_ARM64_REG_X1,
    UC_ARM64_REG_SP, UC_ARM64_REG_LR, UC_ARM64_REG_PC)

OUT = Path(__file__).resolve().parent
BASE = OUT.parents[1]
INPUT = BASE / 'stage2/extraction/files'
ZIP = OUT.parent / 'FX3-7.02-4K30-H265离线研究证据.zip'
EXPECTED = {
 'appFw.so': '545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f',
 'libmpr.so': '9aeef3b9edb3d011c0c90cd2387b3a47bd3b506ebfa57be39ad1a9729771b57c'}
STACK_BASE, STACK_SIZE, STACK = 0x10000000, 0x40000, 0x10030000
SCRATCH, STOP = 0x11000000, 0x12000000
COUNT_LIMIT, TIMEOUT_US = 20000, 1000000

def p32(v): return struct.pack('<I', v & 0xffffffff)
def read32(u, a): return struct.unpack('<I', bytes(u.mem_read(a, 4)))[0]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

class Native:
    def __init__(self, name):
        self.path = INPUT / 'nflasha15/lib' / name
        self.blob = self.path.read_bytes()
        assert hashlib.sha256(self.blob).hexdigest() == EXPECTED[name]
        self.elf = ELFFile(io.BytesIO(self.blob))
        assert self.elf['e_machine'] == 'EM_AARCH64'
        self.segments = [s for s in self.elf.iter_segments() if s['p_type'] == 'PT_LOAD']
        self.md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
        sym = self.elf.get_section_by_name('.dynsym')
        self.symbols = {s.name: {'va': s['st_value'], 'size': s['st_size']}
                        for s in sym.iter_symbols() if s.name and s['st_shndx'] != 'SHN_UNDEF'}
        ps, pr = self.elf.get_section_by_name('.plt'), self.elf.get_section_by_name('.rela.plt')
        self.plt = {ps['sh_addr'] + 32 + i*16: sym.get_symbol(r['r_info_sym']).name
                    for i, r in enumerate(pr.iter_relocations())} if ps and pr else {}
    def read(self, va, n):
        for s in self.segments:
            if s['p_vaddr'] <= va and va+n <= s['p_vaddr']+s['p_filesz']:
                offset = s['p_offset']+va-s['p_vaddr']
                return self.blob[offset:offset+n]
        raise ValueError(f'non-file memory {va:x}+{n:x}')
    def disasm(self, a, z):
        return [f'{i.address:08x}: {i.mnemonic} {i.op_str}'
                for i in self.md.disasm(self.read(a,z-a), a)]

class Micro:
    def __init__(self, native, ranges, stubs=None, resolve_local=False, patch=False):
        self.uc = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
        self.n, self.allowed = native, ranges
        self.stubs = stubs or {}
        self.reason, self.steps, self.calls, self.writes, self.packet_writes = None, 0, [], [], []
        self.resolved, pages = [], set()
        for s in native.segments:
            pages.update(range(s['p_vaddr'] & ~4095,
                         (s['p_vaddr']+s['p_memsz']+4095)&~4095,4096))
        assert len(pages)*4096 < 256*1024*1024
        assert not any(STACK_BASE <= a < STOP+4096 for a in pages)
        # Map contiguous runs in one operation; mapping thousands of individual
        # pages is needlessly expensive in Unicorn's region data structure.
        runs=[]
        for a in sorted(pages):
            if runs and runs[-1][1]==a: runs[-1][1]=a+4096
            else: runs.append([a,a+4096])
        for a,z in runs: self.uc.mem_map(a,z-a)
        for s in native.segments: self.uc.mem_write(s['p_vaddr'],s.data())
        if resolve_local:
            for sec in native.elf.iter_sections():
                if sec.name not in ('.rela.dyn','.rela.plt'): continue
                table = native.elf.get_section(sec['sh_link'])
                for r in sec.iter_relocations():
                    kind, value = r['r_info_type'], None
                    if kind == 1027: value = r['r_addend']
                    elif kind in (1025,1026):
                        sym = table.get_symbol(r['r_info_sym'])
                        if sym['st_shndx'] != 'SHN_UNDEF': value = sym['st_value']+r['r_addend']
                    if value is not None:
                        self.uc.mem_write(r['r_offset'],struct.pack('<Q',value))
                        self.resolved.append([r['r_offset'],value])
        if patch:
            assert native is APP and native.read(0x39895ae,1) == b'\x0a'
            self.uc.mem_write(0x39895ae,b'\x53')
        # ELF mapped bytes cannot be modified by guest code. Host patch above is
        # ephemeral and no mapped bytes are ever saved as a firmware artifact.
        for a,z in runs: self.uc.mem_protect(a,z-a,UC_PROT_READ|UC_PROT_EXEC)
        self.uc.mem_map(STACK_BASE,STACK_SIZE,UC_PROT_READ|UC_PROT_WRITE)
        self.uc.mem_map(SCRATCH,0x10000,UC_PROT_READ|UC_PROT_WRITE)
        self.uc.mem_map(STOP,4096,UC_PROT_READ|UC_PROT_EXEC)
        self.uc.reg_write(UC_ARM64_REG_SP,STACK)
        self.uc.reg_write(UC_ARM64_REG_LR,STOP)
        self.hooks=[self.uc.hook_add(UC_HOOK_CODE,self.code),
                    self.uc.hook_add(UC_HOOK_MEM_INVALID,self.invalid),
                    self.uc.hook_add(UC_HOOK_MEM_WRITE,self.write)]
    def abort(self,reason): self.reason=reason; self.uc.emu_stop()
    def ret(self,value=None):
        if value is not None: self.uc.reg_write(UC_ARM64_REG_X0,value)
        self.uc.reg_write(UC_ARM64_REG_PC,self.uc.reg_read(UC_ARM64_REG_LR))
    def invalid(self,u,access,a,n,value,user):
        self.reason=f'unmapped/protected memory access {access} {a:x}+{n:x}'
        return False
    def write(self,u,access,a,n,value,user):
        if not (STACK_BASE<=a and a+n<=STACK_BASE+STACK_SIZE or SCRATCH<=a and a+n<=SCRATCH+0x10000):
            self.abort(f'write outside stack/scratch {a:x}+{n:x}')
        if len(self.writes)<400: self.writes.append([a,n])
        if SCRATCH+0x2000<=a and a+n<=SCRATCH+0x3000:
            self.packet_writes.append({'pc':hex(u.reg_read(UC_ARM64_REG_PC)),
                'packet_offset':hex(a-(SCRATCH+0x2000)),'size':n,
                'value_hex':hex(value & ((1<<(8*n))-1))})
    def code(self,u,a,n,user):
        self.steps+=1
        if a==STOP: self.abort('returned'); return
        if a in self.stubs:
            self.calls.append({'stub':hex(a)}); self.stubs[a](self); return
        if a in self.n.plt:
            name=self.n.plt[a]; s=self.n.symbols.get(name)
            if s and any(b<=s['va']<z for b,z in self.allowed):
                self.calls.append({'PLT':hex(a),'symbol':name,'local_target':hex(s['va']),
                    'args_x0_x4':[hex(u.reg_read(UC_ARM64_REG_X0+i)) for i in range(5)]})
                u.reg_write(UC_ARM64_REG_PC,s['va']); return
            self.abort('unapproved PLT '+name); return
        if not any(b<=a and a+n<=z for b,z in self.allowed):
            self.abort(f'unapproved execution {a:x}'); return
        word=read32(u,a)
        if word==0xd65f03c0:
            self.calls.append({'return_instruction':hex(a),
                               'return_x0':hex(u.reg_read(UC_ARM64_REG_X0))})
        if word & 0xffe0001f in (0xd4000001,0xd4000002,0xd4000003):
            self.abort('SVC/HVC/SMC forbidden')
    def run(self,entry,args=()):
        for i,v in enumerate(args): self.uc.reg_write(UC_ARM64_REG_X0+i,v)
        start=time.monotonic()
        try: self.uc.emu_start(entry,STOP,timeout=TIMEOUT_US,count=COUNT_LIMIT)
        except UcError as e:
            if self.reason is None: self.reason='emulator error '+str(e)
        if self.reason is None:
            self.reason='returned' if self.uc.reg_read(UC_ARM64_REG_PC)==STOP else 'budget exhausted'
        # Drop callback cycles as soon as the bounded invocation finishes.
        for h in self.hooks: self.uc.hook_del(h)
        return {'reason':self.reason,'steps':self.steps,'return_u32':self.uc.reg_read(UC_ARM64_REG_X0)&0xffffffff,
                'calls':self.calls,'guest_write_count':len(self.writes),
                'elapsed_seconds':round(time.monotonic()-start,6)}

APP, MPR = Native('appFw.so'), Native('libmpr.so')
def log(m): m.ret(0)

def simple(name,entry,args,ranges,prepare=None,resolve=True):
    m=Micro(MPR,ranges,{0xc8c70:log},resolve_local=resolve)
    if prepare: prepare(m.uc)
    row={'test':name,'entry':hex(entry),'args':list(args),**m.run(entry,args)}
    return row,m

def converter(frame,quality,patch=False):
    lookups=[]
    def mode(m): m.ret(0)
    def lookup(m):
        key=read32(m.uc,m.uc.reg_read(UC_ARM64_REG_X1))
        if key not in LITERAL_MAP: m.abort('unmodelled map key '+str(key)); return
        m.uc.mem_write(SCRATCH+0x100c,p32(LITERAL_MAP[key])); m.ret(SCRATCH+0x1000)
        lookups.append({'Mbps':key,'quality':LITERAL_MAP[key]})
    def assertion(m): m.abort('firmware assertion reached')
    m=Micro(APP,[(0x2e68048,0x2e69ef0)],
            {0x2a4e798:mode,0x2e68010:lookup,0x2f6fe3c:assertion},patch=patch)
    for arg in (12,13,14): m.uc.mem_write(STACK+(arg-9)*8,struct.pack('<Q',quality))
    for a,p in [(0x210,SCRATCH),(0x218,SCRATCH+4),(0x220,SCRATCH+8)]:
        m.uc.mem_write(STACK+a,struct.pack('<Q',p))
    m.uc.mem_write(SCRATCH,p32(0xfeedf00d)*3)
    row={'input_frame_ordinal':frame,'input_record_setting_ordinal':quality,
         'candidate_memory_patch':patch,**m.run(0x2e68048,[0,6,0,frame,0,0,0,0])}
    row.update({'VideoParamComb':read32(m.uc,SCRATCH),'DefStruct_FrameRate':read32(m.uc,SCRATCH+4),
                'DefStruct_VQuality':read32(m.uc,SCRATCH+8),'lookup_adapter':lookups})
    return row

LITERAL_PAIRS=list(struct.iter_unpack('<II',APP.read(0x39898b0,0xd0)))
LITERAL_MAP=dict(LITERAL_PAIRS)
PACKET_NAMES=[
 '_ZN3mpr19GetCodecAudioFormatEjj',
 '_ZN3mpr24ConvertVideoCodecToCodecEN9DefStruct10VideoCodecENS0_12GopStructureE',
 '_ZN3mpr15GetAudioBitrateENS_14AudioParamCombE',
 '_ZN3mpr5pconv24ConvertFrameRateForCodecEN9DefStruct9FrameRateEPNS_11FramePerSecEPhS5_',
 '_ZN3mpr21GetAudioOutputChannelEh',
 '_ZN3mpr35ConvertPictureQualityDefStructToMprEj',
 '_ZN3mpr14GetVideoAspectENS_14VideoParamCombE',
 '_ZN3mpr32ConvertVideoAspectForAspectRatioEN9DefStruct11VideoAspectE',
 '_ZN3mpr15GetChromaFormatENS_14VideoParamCombE',
 '_ZN3mpr14GetVideoBitLenENS_14VideoParamCombE']
PACKET_RANGES=[(0xd13f8,0xd166c)]+[(MPR.symbols[n]['va'],MPR.symbols[n]['va']+MPR.symbols[n]['size']) for n in PACKET_NAMES]

def packet(vpc,frame,quality):
    def prep(u): u.mem_write(SCRATCH+0x764,struct.pack('<IIII',vpc,quality,frame,0))
    row,m=simple('SetEncOpenParam',0xd13f8,[SCRATCH,SCRATCH+0x2000],PACKET_RANGES,prep)
    raw=bytes(m.uc.mem_read(SCRATCH+0x2000,0x98))
    row.update({'VideoParamComb':vpc,'FrameRate':frame,'VQuality':quality,'packet_hex':raw.hex(),
                'input_buffer':hex(SCRATCH),'output_buffer':hex(SCRATCH+0x2000),
                'input_write':{'offset':'0x764','hex':struct.pack('<IIII',vpc,quality,frame,0).hex(),
                    'fields':['VideoParamComb','VQuality','FrameRate','AudioParamComb']},
                'initial_buffers':'Unicorn zero-filled scratch; only the stated input fields are host-written; output remains zero until guest writes',
                'guest_packet_write_trace':m.packet_writes,
                'fields':{'file_format_65':raw[0x65],'codec_66':raw[0x66],
                   'width':struct.unpack_from('<H',raw,0x68)[0],
                   'height':struct.unpack_from('<H',raw,0x6a)[0],
                   'frame_enum_80':raw[0x80],'ntsc_flag_81':raw[0x81],
                   'quality_enum_82':raw[0x82],'color_format_94':raw[0x94],'bit_depth_95':raw[0x95]}})
    return row

def main():
    assert sha(ZIP)=='785c3b3fdb5e879dd7acda3b782001f09e3dce8210c71d6104ce141d77ba4865'
    # Source hash checks happen before every run, and again at completion.
    quality=[]
    for mbps in (1,2,3,6,9,12,13,16,20,30,45,50,75,100,150,200,280):
        row,m=simple('GetVQuality',0xc9c04,[mbps],[(0xc9c04,0xc9e84)])
        row.update({'input_Mbps':mbps,'app_literal_value':LITERAL_MAP.get(mbps)})
        quality.append(row)
    converters=[converter(f,q,p) for p in (False,True)
                for f in (0,1,2,3,4,5,6,8) for q in (8,16,17,24,30)]
    with zipfile.ZipFile(ZIP) as z:
        original=json.loads(z.read('converter-emulation-results.json'))
    keys=['input_frame_ordinal','input_record_setting_ordinal','candidate_memory_patch',
          'reason','VideoParamComb','DefStruct_FrameRate','DefStruct_VQuality']
    comparisons=[{'case_index':i,'match':all(a[k]==b[k] for k in keys)}
                 for i,(a,b) in enumerate(zip(converters,original['cases']))]
    downstream=[]
    for vpc in (5,6,7,8):
        for frame,q in ((3,6),(7,6),(3,12),(12,6),(3,255)):
            def prep(u,vpc=vpc,frame=frame,q=q):
                u.mem_write(SCRATCH+0x170,struct.pack('<III',vpc,q,frame))
            row,m=simple('CheckMovieRecParam',0xcc4d4,[SCRATCH],[(0xcc4d4,0xcc824)],prep)
            row.update({'VideoParamComb':vpc,'FrameRate':frame,'VQuality':q,
                        'accepted':row['reason']=='returned' and row['return_u32']==0})
            downstream.append(row)
        for q in (6,12):
            row,m=simple('ConvertVPCToLevel',0x115e78,[0,vpc,q,3,SCRATCH],[(0x115e78,0x115fec)])
            row.update({'VideoParamComb':vpc,'FrameRate':3,'VQuality':q,'level':read32(m.uc,SCRATCH)})
            downstream.append(row)
        for stream in (0,1):
            row,m=simple('GetCodecInfoForCodec',0xcd40c,[vpc,stream],[(0xcd40c,0xcd4f8)])
            row.update({'VideoParamComb':vpc,'StreamType':stream});downstream.append(row)
    for q in (6,12,255):
        row,m=simple('GetVideoBitrate',0x2c0ce0,[q],[(0x2c0ce0,0x2c0d04)])
        row['VQuality']=q;downstream.append(row)
    for vpc in (5,6,7,8):
        for name,entry,end in [('GetChromaFormat',0xd11b0,0xd1274),
                               ('GetVideoBitLen',0xd1274,0xd1338)]:
            row,m=simple(name,entry,[vpc],[(entry,end)])
            row['VideoParamComb']=vpc;downstream.append(row)
    for q in (6,12,255):
        row,m=simple('ConvertPictureQualityDefStructToMpr',0xd0758,[q],[(0xd0758,0xd0800)])
        row['VQuality']=q;downstream.append(row)
    row,m=simple('ConvertFrameRateToNumerAndDenom',0x2c0de8,[3,SCRATCH,SCRATCH+4],[(0x2c0de8,0x2c0e98)])
    row.update({'FrameRate':3,'numerator':read32(m.uc,SCRATCH),'denominator':read32(m.uc,SCRATCH+4)})
    downstream.append(row)
    # Enumerate small legal enum domains and preserve raw observations. No input
    # is interpreted as a camera-supported mode merely because the helper returns.
    comb=[]
    for res in range(6):
        for color in (0,1):
            row,m=simple('GetVideoParamComb',0xc9e84,[1,res,color,1,0],[(0xc9e84,0xc9fcc)])
            row.update({'codec':1,'resolution_enum':res,'color_enum':color,'bit_depth_enum':1,'gop_enum':0})
            comb.append(row)
    packets=[packet(vpc,frame,q) for vpc in (5,6,7,8) for frame in (3,7) for q in (6,12)]
    tables={'literal_quality_pairs':LITERAL_PAIRS,
            'g_videoParamComb_raw':[list(struct.unpack('<6I',MPR.read(0x2cb108+i*24,24))) for i in range(13)],
            'packet_whitelist':[{'name':n,**MPR.symbols[n]} for n in PACKET_NAMES]}
    windows_quality_mbps=(30,45,50,75,100,150,200,280)
    checks={
      '80_converter_cases_match_received':len(comparisons)==80 and all(c['match'] for c in comparisons),
      'Windows_eight_quality_pairs_match_real_MPR':all(r['reason']=='returned' and r['return_u32']==r['app_literal_value'] for r in quality if r['input_Mbps'] in windows_quality_mbps),
      'expanded_16M_reverse_mapping_gap_reproduced':any(r['input_Mbps']==16 and r['reason']=='returned' and r['return_u32']==255 and r['app_literal_value']==6 for r in quality),
      'HD_16M_basic_validator_accepts':all(r['accepted'] for r in downstream if r['test']=='CheckMovieRecParam' and r['VideoParamComb'] in (6,8) and r['FrameRate']==3 and r['VQuality']==6),
      'invalid_basic_enum_controls_reject':all(not r['accepted'] for r in downstream if r['test']=='CheckMovieRecParam' and (r['FrameRate']==12 or r['VQuality']==255)),
      'HD420_16M_packet_fields_match_conversion':all(r['reason']=='returned' and all(r['fields'][k]==v for k,v in {'width':1920,'height':1080,'codec_66':15,'frame_enum_80':3,'ntsc_flag_81':1,'quality_enum_82':22,'color_format_94':0,'bit_depth_95':1}.items()) for r in packets if r['VideoParamComb']==6 and r['FrameRate']==3 and r['VQuality']==6),
      'HD422_packet_invalid_color_depth_reproduced':all(r['reason']=='returned' and r['fields']['color_format_94']==254 and r['fields']['bit_depth_95']==254 for r in packets if r['VideoParamComb']==8),
      'HD422_direct_helpers_return_invalid_254':all(r['reason']=='returned' and r['return_u32']==254 for r in downstream if r['test'] in ('GetChromaFormat','GetVideoBitLen') and r['VideoParamComb']==8),
      'q6_to_API22_and_16M_bitrate_confirmed':all(any(r['test']==name and r.get('VQuality')==6 and r['reason']=='returned' and r['return_u32']==value for r in downstream) for name,value in [('GetVideoBitrate',16000),('ConvertPictureQualityDefStructToMpr',22)]),
      'inputs_unchanged':all(sha(INPUT/'nflasha15/lib'/n)==h for n,h in EXPECTED.items())}
    result={'scope':'Bounded CPU helper execution only; synthetic zeroed structs except stated fields. NOT recording, bitstream, hardware, package/signing or flash validation.',
            'engine':unicorn.__version__,'python':sys.version,'count_limit_per_case':COUNT_LIMIT,
            'timeout_us_per_case':TIMEOUT_US,'OS_hardware_forwarding':False,
            'stubs':{'0xc8c70':'MPR log returns 0','0x2a4e798':'normal movie mode query returns 0',
                     '0x2e68010':'exact original app constant bitrate map lookup adapter',
                     '0x2f6fe3c':'stop at firmware assertion'},
            'quality':quality,'converter_cases':converters,'received_comparison':comparisons,
            'downstream_cases':downstream,'combination_cases':comb,'packet_cases':packets,
            'tables':tables,'checks':checks}
    (OUT/'offline-results.json').write_text(json.dumps(result,indent=2)+'\n')
    (OUT/'selected-disassembly.txt').write_text('\n'.join(MPR.disasm(0xc9e84,0xc9fcc)+MPR.disasm(0xcc4d4,0xcc824)+MPR.disasm(0xcd40c,0xcd4f8)+MPR.disasm(0xd13f8,0xd166c)+MPR.disasm(0x115e78,0x115fec))+'\n')
    print(json.dumps(checks,indent=2))
    for r in packets:
        if r['VideoParamComb'] in (6,8) and r['FrameRate']==3 and r['VQuality']==6:
            print(json.dumps({k:r[k] for k in ('VideoParamComb','FrameRate','VQuality','reason','steps','fields')}))
    if not all(checks.values()): raise SystemExit(1)

if __name__=='__main__': main()
