#!/usr/bin/env python3
"""Pinned cross-image ORIL ABI, FX6 AP load edge and full look-22 payload comparison."""
import hashlib
import json
import pathlib
import struct

from capstone import CS_ARCH_ARM64, CS_MODE_ARM, Cs
from elftools.elf.elffile import ELFFile

ROOT = pathlib.Path(__file__).resolve().parent
MAC = ROOT.parents[5]
FX6 = ROOT.parent
FX6_AV = FX6 / 'fat-files/nflasha3/av-cam.bin'
FX3_AV = MAC / 'work/sony-firmware-20261024/stage2/extraction/files/nflasha3/av-cam.bin'
IM = FX6 / 'nflasha15-files/bin/im.elf'
KERNEL = FX6 / 'fat-files/nflasha3/vmlinux.bin'
WBI = FX6 / 'tree/0700_part_image/dev/nflasha5'
KMODS = {name: FX6 / 'nflasha15-files/kmod' / name
         for name in ('grm_ma.ko', 'osal_uipc.ko', 'stream.ko', 'stream2.ko')}
FX6_INIT = FX6 / 'cp-av-analysis/init-routing/init-trace.json'
FX3_INIT = MAC / 'work/fx3-color-port-20261027/initializer-guest-results.json'
PRIOR_CALLER = FX6 / 'cp-av-analysis/init-routing/caller-selection'
PINS = {
    'fx6_av': '56684d830eab1e304868548746d8275188a925f9e4ab9354560180c31b4a93cf',
    'fx3_av': '0cb7e03a59b4ec3d7633664ab0f7a9477892d1aaf442b9db83a7e9a62a49bdaf',
    'fx6_im': '87d672bd6abbcf695c0a773cb096d72d18429e5107846a2f0d3e8add87e400ec',
    'fx6_kernel': 'bc4925e701ae363c797f22ef28f29dc48fd17af7f25a3f64d7d0824312c0dab9',
    'fx6_wbi': 'd33f0bd9c305cd9217815cd1e1a4fd86ea48b28ddbbbe6c581c8665dc5fde2d1',
    'fx6_prior_init': '7bad0475d6d02adffc51e508f5189e398639d30eae72d82a210a3ccf1a09a9fd',
    'fx3_prior_init': '29c76396ae58e8caca2bd96e0eb0408854c163e60556b5d27b4da9d6bd76ab95',
    'grm_ma': '81e0bf8754a898d4b70d3c1d46f7a6da4728a449bf575eaa6a6c9b2493f33a33',
    'osal_uipc': '07bafe9c7cf0cba42de4e7c8f62229d298881552b144e0ee43ff3b404ca379ee',
    'stream': 'd00cab4072b5b4752e5811a40c4b42db5ac548fc2c9c8c09c7051893ecdc6015',
    'stream2': '754f43addf601ec8342fc8cf2460761e5abf47df4f993c934072bd47d03bb0f4',
    'prior_caller_static': '9db38bfaa4f21b34d1501818001118cf71560287d53dd1d94e6a76c1e35c4c0a',
    'prior_caller_replay': 'ea43f9e1ba8f7825312e583dbf3b826fc84e9ffd8e718b9311f523ed154d8cda',
}
BASE = 0xffffffc001000000
MODELS = {
    'FX6_6.01': {'thunk_event':0x2ede0,'thunk_release':0x2ee44,'thunk_word':0x2efd4,
                 'event_loop':(0x2a72b8,0x2a7374),'update':(0x29b290,0x29b308),
                 'dispatch':(0x2a7374,0x2a74f4),'flag':0xb45884,'mode':0xbb0bfc,
                 'look_table':0x36fdf8,'look22':0x370098,'descriptors':0xaa2ca0,'builder_call':0x2a74e4},
    'FX3_7.02': {'thunk_event':0x2efd8,'thunk_release':0x2f03c,'thunk_word':0x2f1cc,
                'event_loop':(0x2c40d4,0x2c4190),'update':(0x2b80b8,0x2b8130),
                'dispatch':(0x2c4190,0x2c4310),'flag':0xba81ec,'mode':0xc148b8,
                'look_table':0x38ada8,'look22':0x38b048,'descriptors':0xb05638,'builder_call':0x2c4300},
}


def sha(data): return hashlib.sha256(data).hexdigest()


def lines(data,start,end,base):
    md=Cs(CS_ARCH_ARM64,CS_MODE_ARM)
    return [{'file_offset':hex(i.address-base),'va':hex(i.address),'bytes_le':i.bytes.hex(),
             'instruction':(i.mnemonic+' '+i.op_str).strip()}
            for i in md.disasm(data[start:end],base+start)]


def source(path,pin):
    data=path.read_bytes();assert sha(data)==pin,(path,sha(data));return data


def model(data,cfg,copies):
    assert struct.unpack_from('<Q',data,0)[0]==BASE+0x58 and data[8:12]==b'ORIL'
    assert struct.unpack_from('<Q',data,0x20)[0]==BASE+0x1a4
    # +0x1a4 starts with one zero qword, followed immediately by image metadata.
    assert struct.unpack_from('<Q',data,0x1a4)[0]==0
    assert struct.unpack_from('<Q',data,0x1ac)[0]!=0
    thunks=[]
    for kind,off,slot in [('event',cfg['thunk_event'],0x3c0),
                          ('release',cfg['thunk_release'],0x3e8),
                          ('word',cfg['thunk_word'],0x4c0)]:
        inst=lines(data,off,off+20,BASE)
        assert len(inst)==5 and '[x8, #'+hex(slot)+']' in inst[3]['instruction']
        assert inst[2]['instruction']=='ldr x8, [x8, #0x20]' and inst[4]['instruction'].startswith('br x')
        thunks.append({'kind':kind,'file_offset':hex(off),'va':hex(BASE+off),'slot':hex(slot),
                       'sha256':sha(data[off:off+20]),'instructions':inst})
    look=cfg['look22'];key,ptr,count,name=struct.unpack_from('<4Q',data,look)
    assert key==22 and ptr==BASE+cfg['descriptors'] and count==70
    norm=[];rows=[]
    by_dst={}
    for copy in copies:
        dst=int(copy.get('dst',copy.get('dst_offset')),16)
        if cfg['descriptors']<=dst<cfg['descriptors']+70*152:
            assert dst not in by_dst
            by_dst[dst]=copy
    assert len(by_dst)==70
    for i in range(count):
        off=cfg['descriptors']+i*152
        copy=by_dst[off]
        source_descriptor_offset=int(copy.get('src',copy.get('src_offset')),16)
        assert copy.get('size',copy.get('bytes'))==152
        assert data[off:off+152]==bytes(152)  # file is pre-initialization BSS
        src,reg,words=struct.unpack_from('<QQI',data,source_descriptor_offset)
        assert BASE<=src<BASE+len(data) and words>0 and words<=0x40000
        source_offset=src-BASE;length=words*4
        assert source_offset+length<=len(data)
        payload_hash=sha(data[source_offset:source_offset+length])
        name=data[source_descriptor_offset+20:source_descriptor_offset+152].split(b'\0',1)[0].decode('ascii')
        assert name.startswith('MLUT_')
        norm.append(name.encode()+b'\0'+struct.pack('<QI',reg,words)+bytes.fromhex(payload_hash))
        rows.append({'index':i,'destination_descriptor_offset':hex(off),
                     'source_descriptor_offset':hex(source_descriptor_offset),
                     'source_descriptor_sha256':sha(data[source_descriptor_offset:source_descriptor_offset+152]),
                     'name':name,'data_offset':hex(source_offset),'register_offset':hex(reg),
                     'word_count':words,'payload_sha256':payload_hash})
    regions={}
    for name,(start,end) in {'mode_update':cfg['update'],
                             'event_consumer_loop':cfg['event_loop'],
                             'look_dispatch_to_builder':cfg['dispatch']}.items():
        regions[name]={'start':hex(start),'end_exclusive':hex(end),'sha256':sha(data[start:end]),
                       'instructions':lines(data,start,end,BASE)}
    return {'header':{'first_pointer':hex(BASE+0x58),'magic':'ORIL','provider_field_offset':'0x20',
                      'provider_field_file_value':hex(BASE+0x1a4),'pointed_first_qword_file_value':'0x0',
                      'next_qword_at_0x1ac':hex(struct.unpack_from('<Q',data,0x1ac)[0]),
                      'interpretation':'file value points to a zero qword adjacent to image metadata, not a serialized 0x4c8-byte callback table'},
            'thunks':thunks,'mode_update':regions['mode_update'],
            'event_consumer_loop':regions['event_consumer_loop'],
            'dispatch':regions['look_dispatch_to_builder'],
            'snapshot_flag':data[cfg['flag']],'snapshot_mode':struct.unpack_from('<I',data,cfg['mode'])[0],
            'flag_offset':hex(cfg['flag']),'mode_offset':hex(cfg['mode']),
            'look22':{'record_offset':hex(look),'record_sha256':sha(data[look:look+32]),
                      'descriptor_array_offset':hex(cfg['descriptors']),'count':count,
                      'normalized_70_payloads_sha256':sha(b''.join(norm)),'source':'pinned original-memcpy CPU trace plus original source descriptor bytes; not raw pre-init destination bytes',
                      'rows':rows},
            'builder_call_offset':hex(cfg['builder_call'])}


def im_loader(data):
    with IM.open('rb') as f:
        elf=ELFFile(f)
        assert elf.header['e_machine']=='EM_AARCH64' and elf.header['e_type']=='ET_EXEC'
        text=elf.get_section_by_name('.text');assert text['sh_offset']==0x2490 and text['sh_addr']==0x402490
        rela=elf.get_section_by_name('.rela.plt');dyn=elf.get_section(rela['sh_link'])
        plt={hex(0x401f70+i*16):dyn.get_symbol(r['r_info_sym']).name for i,r in enumerate(rela.iter_relocations())}
    for va,name in [('0x402050','open'),('0x402080','dlsym'),('0x402150','dlopen'),('0x402180','syscall'),
                    ('0x402200','mmap'),('0x402260','munmap'),('0x4022c0','snprintf')]:
        assert plt[va]==name,(va,plt.get(va))
    strings={s.decode():hex(data.find(s)) for s in (b'fn=/system/av-cam.bin load=1 debug=1',b'/usr/lib/libObj.so')}
    assert strings['fn=/system/av-cam.bin load=1 debug=1']=='0x7df6'
    assert strings['/usr/lib/libObj.so']=='0x7e2e'
    regions={}
    for name,(a,z) in {'dlopen_path':(0x5f5c,0x5fa0),'module_load':(0x6040,0x6134),
                       'command_build':(0x6178,0x61d8)}.items():
        regions[name]={'file_offset':hex(a),'elf_va':hex(0x400000+a),'end_exclusive':hex(0x400000+z),
                       'sha256':sha(data[a:z]),'instructions':lines(data,a,z,0x400000)}
    return {'sha256':PINS['fx6_im'],'size':len(data),'type':'AArch64 ET_EXEC',
            'string_file_offsets':strings,'plt':{k:plt[k] for k in ['0x402050','0x402080','0x402150','0x402180','0x402200','0x402260','0x4022c0']},
            'regions':regions,'load_edge_scope':'im.elf contains av-cam command literal, open/mmap/syscall(105) load path; exact runtime invocation and kernel ORIL callback-table mutation unobserved'}


def module_inventory():
    inventory={}
    for filename,path in KMODS.items():
        data=source(path,PINS[filename[:-3]])
        with path.open('rb') as f:
            elf=ELFFile(f)
            assert elf.header['e_machine']=='EM_AARCH64' and elf.header['e_type']=='ET_REL'
            sym=elf.get_section_by_name('.symtab')
            symbols=[s for s in sym.iter_symbols() if s.name=='init_module']
            assert len(symbols)==1
            undefined=[s.name for s in sym.iter_symbols()
                       if s['st_shndx']=='SHN_UNDEF' and s.name]
        inventory[filename]={'sha256':sha(data),'size':len(data),'type':'AArch64 ET_REL',
                             'init_module_symbol_value':hex(symbols[0]['st_value']),
                             'init_module_section_index':str(symbols[0]['st_shndx']),
                             'oril_literal_count':data.count(b'ORIL'),
                             'av_cam_literal_count':data.count(b'av-cam.bin'),
                             'undefined_symbol_sample':sorted(undefined)[:16],
                             'scope':'module init_module and symbol/relocation boundary inventoried; no call or data edge to ORIL table established'}
    return inventory


def main():
    binaries={'fx6_av':source(FX6_AV,PINS['fx6_av']),'fx3_av':source(FX3_AV,PINS['fx3_av']),
              'fx6_im':source(IM,PINS['fx6_im'])}
    init6=json.loads(source(FX6_INIT,PINS['fx6_prior_init']))
    init3=json.loads(source(FX3_INIT,PINS['fx3_prior_init']))
    source(PRIOR_CALLER/'static-evidence.json',PINS['prior_caller_static'])
    source(PRIOR_CALLER/'caller-replay.json',PINS['prior_caller_replay'])
    # Rehash the extracted kernel and WBI2 as cross-image search boundaries, not provider proof.
    assert sha(KERNEL.read_bytes())==PINS['fx6_kernel']
    wbi=WBI.read_bytes();assert sha(wbi)==PINS['fx6_wbi'] and wbi[:4]==b'WBI2'
    models={'FX6_6.01':model(binaries['fx6_av'],MODELS['FX6_6.01'],init6['copies']),
            'FX3_7.02':model(binaries['fx3_av'],MODELS['FX3_7.02'],init3['copies'])}
    assert models['FX6_6.01']['look22']['normalized_70_payloads_sha256']==models['FX3_7.02']['look22']['normalized_70_payloads_sha256']
    assert all((a['name'],a['register_offset'],a['word_count'],a['payload_sha256'])==
               (b['name'],b['register_offset'],b['word_count'],b['payload_sha256'])
               for a,b in zip(models['FX6_6.01']['look22']['rows'],models['FX3_7.02']['look22']['rows']))
    output={'pins':PINS,'va_rule':'AV VA = 0xffffffc001000000 + file offset; AP im.elf ELF VA = file offset + 0x400000 for cited text/rodata',
            'models':models,'fx6_im_loader':im_loader(binaries['fx6_im']),
            'fx6_ap_kernel_module_boundary':{'kernel_type':'ARM64 Linux Image (not ELF); no ELF relocation/export table in extracted file',
                'kernel_size':KERNEL.stat().st_size,'kernel_oril_literal_count':KERNEL.read_bytes().count(b'ORIL'),
                'modules':module_inventory(),
                'scope':'examined im ELF PLT relocations, ARM64 kernel image, and four named AArch64 ET_REL modules; literal absence and generic module init symbols cannot identify provider implementation'},
            'fx6_kernel_wbi_inventory':{'kernel_sha256':PINS['fx6_kernel'],'wbi_sha256':PINS['fx6_wbi'],
                'wbi_section_count':struct.unpack_from('<Q',wbi,8)[0],
                'wbi_im_text_file_offset':hex(wbi.find(binaries['fx6_im'][0x2490:0x24b0])),
                'wbi_oril_literal_count':wbi.count(b'ORIL'),
                'scope':'WBI2 raw boot-memory sections contain an im.elf text copy; no ORIL literal is not proof of absent proprietary loader'},
            'provider_implementation':'not recovered: original header field is a pointer-to-zero placeholder; +0x3c0/+0x4c0 thunks are imports; im/kernel edge is a registration candidate, not a resolved callback address',
            'linux_syscall_reference':'https://github.com/torvalds/linux/blob/master/include/uapi/asm-generic/unistd.h'}
    assert output['fx6_kernel_wbi_inventory']['wbi_section_count']==1197
    (ROOT/'binding-evidence.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps({'pins_checked':len(PINS),'thunks_per_model':3,'look22_descriptors_equal':70,
                      'im_syscall':output['fx6_im_loader']['plt']['0x402180'],
                      'provider_implementation':output['provider_implementation']}))


if __name__=='__main__':main()
