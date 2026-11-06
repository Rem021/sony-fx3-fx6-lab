#!/usr/bin/env python3
"""Static FX6 CP/AV mapping and MLUT comparison against pinned FX3 7.02."""
import hashlib,json,pathlib,re,struct,subprocess
from capstone import Cs,CS_ARCH_ARM,CS_ARCH_ARM64,CS_MODE_ARM,CS_MODE_LITTLE_ENDIAN

OUT=pathlib.Path(__file__).resolve().parent
DONOR=OUT.parent
FX3=OUT.parents[3]  # work/fx3-color-port-20261027
assert FX3.name=='fx3-color-port-20261027'
FX3_AV=FX3.parent/'sony-firmware-20261024/stage2/extraction/files/nflasha3/av-cam.bin'
FX3_CP=FX3.parent/'sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin'
PINS={
 'fx6_cp':'60de0ab5544749dd50d8245f573c0994573fef349186efe20b502c42e3289668',
 'fx6_av':'56684d830eab1e304868548746d8275188a925f9e4ab9354560180c31b4a93cf',
 'fx3_av':'0cb7e03a59b4ec3d7633664ab0f7a9477892d1aaf442b9db83a7e9a62a49bdaf',
 'fx3_cp':'c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba',
 'fx3_extraction':'8c1763c54f8e4313017990e846b5b225d190f1b3a0a0817d2be693ba45561827',
 'fx3_index':'fd767391c0811c74af68ead7d9c0d5bccaa9f1f77239abdedd4513dc67cac3db',
 'fx3_initializer':'29c76396ae58e8caca2bd96e0eb0408854c163e60556b5d27b4da9d6bd76ab95',
 'fx3_look':'6443be58aaa2a547aa7488a7551452ab4ce995bc108e8cb9244f7892b7b84a4f'}
CONFIG_PINS={'partinf':'e05b53d1f739968510dd24d62cd38426772fe3e50fe463a3d260c5f113e17ec9',
             'tomco':'36566d47fe61e9560f4ce7f1b579bc2404b330bb7940b54e462abcff9c360140'}

def pinned(p,key):
 b=p.read_bytes();assert hashlib.sha256(b).hexdigest()==PINS[key],(p,key)
 return b
def hx(n):return hex(n)
def decode(cs,b,start,length):
 return [{'offset':hx(i.address),'bytes':i.bytes.hex(),'mnemonic':i.mnemonic,'op_str':i.op_str}
         for i in cs.disasm(b[start:start+length],start)]
def cstr(b,o):
 assert 0<=o<len(b);e=b.index(0,o);return b[o:e].decode('ascii')

def descriptors(b,base):
 d={}
 for m in re.finditer(rb'MLUT_[A-Z0-9_]+\0',b):
  off=m.start()-20
  if off<0 or off%8:continue
  ptr,reg,words=struct.unpack_from('<QQI',b,off);data=ptr-base
  if not(0<=data<len(b) and reg<65536 and 0<words<10000 and data+4*words<=len(b)):continue
  if b[m.end():off+148]!=bytes(off+148-m.end()):continue
  name=m.group()[:-1].decode();raw=b[data:data+4*words]
  assert name not in d
  d[name]={'name':name,'descriptor_offset':off,'data_pointer':ptr,'data_offset':data,
           'register_offset':reg,'word_count':words,'sha256':hashlib.sha256(raw).hexdigest()}
 return d

def main():
 cp=pinned(DONOR/'fat-files/nflasha8/cpapp-b.bin','fx6_cp')
 av=pinned(DONOR/'fat-files/nflasha3/av-cam.bin','fx6_av')
 old=pinned(FX3_AV,'fx3_av')
 old_cp=pinned(FX3_CP,'fx3_cp')
 old_ex=json.loads(pinned(FX3/'extraction-results.json','fx3_extraction'))
 old_idx={x['name']:x for x in json.loads(pinned(FX3/'descriptor-index.json','fx3_index'))}
 old_init=json.loads(pinned(FX3/'initializer-guest-results.json','fx3_initializer'))
 old_look=json.loads(pinned(FX3/'look-consumer-guest-results.json','fx3_look'))
 part_path=DONOR/'tree/0300_partconf/partinf.conf'
 tomco_path=DONOR/'fat-files/nflasha8/tomco.txt'
 part_text=part_path.read_bytes();tomco_text=tomco_path.read_bytes()
 assert hashlib.sha256(part_text).hexdigest()==CONFIG_PINS['partinf']
 assert hashlib.sha256(tomco_text).hexdigest()==CONFIG_PINS['tomco']
 part_lines=part_text.decode('latin1').splitlines();tomco_lines=tomco_text.decode('latin1').splitlines()
 cp_header=next(i for i,x in enumerate(part_lines) if '/dev/nflasha8' in x and 'CP Data' in x)
 assert part_lines[cp_header+1].strip()=='0x000EC000,0x00020000,0x00000005,0xFFFFFFFF'
 memcfg=[x.strip() for x in tomco_lines if x.startswith('memcfg=')]
 assert len(memcfg)==4 and 'tmon_addr=0x03400000' in tomco_lines
 config_evidence={'partinf_sha256':CONFIG_PINS['partinf'],'cp_partition_comment':part_lines[cp_header].strip(),
                  'cp_partition_record':part_lines[cp_header+1].strip(),'tomco_sha256':CONFIG_PINS['tomco'],
                  'tomco_memcfg':memcfg,'tomco_tmon_addr':'0x03400000',
                  'scope':'flash partition and CP memory configuration text; neither states the cpapp load address or runtime mapping'}
 assert old_ex['sha256']==PINS['fx3_av']
 # Derive independently: the AV header's first pointer is to file offset 0x58;
 # CP startup loads literal at 0x0c, adds four, then branches to file offset 0x10.
 avbase=struct.unpack_from('<Q',av,0)[0]-0x58
 cp_literal=struct.unpack_from('<I',cp,0x0c)[0];cpbase=cp_literal-0x0c
 assert av[8:12]==b'ORIL' and avbase==0xffffffc001000000
 assert cp[:12].hex()=='04109fe5041081e201f0a0e1' and cpbase==0x108000
 cp_cs=Cs(CS_ARCH_ARM,CS_MODE_ARM|CS_MODE_LITTLE_ENDIAN)
 av_cs=Cs(CS_ARCH_ARM64,CS_MODE_ARM)
 cp_start=decode(cp_cs,cp,0,0x70);av_start=decode(av_cs,av,0x58,0x50)
 assert cp_start[0]['op_str']=='r1, [pc, #4]' and cp_start[1]['op_str']=='r1, r1, #4' and cp_start[2]['op_str']=='pc, r1'
 assert any(x['mnemonic']=='bl' for x in av_start)
 mapping={'cp':{'sha256':PINS['fx6_cp'],'bytes':len(cp),'format':'flat ARM32 little-endian code, no ELF header',
                 'file_offset_zero_load_address':hx(cpbase),'first_literal_file_offset':'0xc',
                 'first_literal_value':hx(cp_literal),'jump_target':hx(cp_literal+4),
                 'boot_code':cp_start,'extra_embedded_addresses':[(hx(o),hx(struct.unpack_from('<I',cp,o)[0])) for o in range(0x380,0x394,4)],
                 'limitation':'self-referential startup mapping; CP runtime memory layout and IPC ABI remain unverified'},
          'av':{'sha256':PINS['fx6_av'],'bytes':len(av),'format':'ORIL flat AArch64 little-endian image, no ELF header',
                'magic_offset':'0x8','header_first_pointer':hx(struct.unpack_from('<Q',av)[0]),
                'file_offset_zero_load_address':hx(avbase),'startup_code':av_start,
                'limitation':'image-internal pointer mapping; active runtime load and DSP route unverified'},
          'fx3_av_reference':{'sha256':PINS['fx3_av'],'bytes':len(old),'base':old_ex['image_base'],
                              'first_differing_file_offset':'0x84'},
          'fx3_cp_reference':{'sha256':PINS['fx3_cp'],'bytes':len(old_cp),
                              'identical_prefix_bytes':131072,'first_differing_file_offset':'0x20000'}}
 assert cp[:131072]==old_cp[:131072] and cp[131072]!=old_cp[131072]
 assert av[:0x84]==old[:0x84] and av[0x84]!=old[0x84]
 d=descriptors(av,avbase)
 assert len(d)==612 and len(old_idx)==612
 common=sorted(d.keys()&old_idx.keys());only6=sorted(d.keys()-old_idx.keys());only3=sorted(old_idx.keys()-d.keys())
 assert len(common)==583 and len(only6)==len(only3)==29
 assert all(d[n]['sha256']==old_idx[n]['sha256'] and d[n]['word_count']==old_idx[n]['word_count'] and d[n]['register_offset']==old_idx[n]['register_offset'] for n in common)
 paired=[]
 for n in only6:
  counterpart=n+'_V1_1';assert counterpart in old_idx
  x=d[n];y=old_idx[counterpart]
  paired.append({'fx6_name':n,'fx3_name':counterpart,'fx6_descriptor_offset':hx(x['descriptor_offset']),
                 'fx6_data_offset':hx(x['data_offset']),'fx6_sha256':x['sha256'],
                 'fx3_data_offset':hx(y['data_offset']),'fx3_sha256':y['sha256'],
                 'word_count':x['word_count'],'same_bytes':x['sha256']==y['sha256']})
 assert all(not x['same_bytes'] for x in paired)
 matrix=d['MLUT_MTX_A_REG_VENICE_LMX0_SLOG3_SGAMUT3_ACES'];raw=list(struct.unpack_from('<13I',av,matrix['data_offset']))
 assert raw==old_ex['matrix']['raw_words']
 assert d['MLUT_MTX_A_REG_SG3TOAP1_0']['sha256']==matrix['sha256']
 look_name=b'MLUT_LOOKNAME_SL3SG3C_THRU';nameoff=av.find(look_name);assert nameoff>=0
 nameptr=avbase+nameoff;ref=av.find(struct.pack('<Q',nameptr));assert ref>=24
 table=ref-24
 assert table==0x36fdf8
 looks=[]
 for i in range(29):
  idx,ptr,count,name=struct.unpack_from('<4Q',av,table+i*32)
  assert idx==i+1 and avbase<=ptr<avbase+len(av) and avbase<=name<avbase+len(av)
  nm=cstr(av,name-avbase)
  looks.append({'index':idx,'record_offset':hx(table+i*32),'descriptor_array_offset':hx(ptr-avbase),
                'descriptor_count':count,'name':nm,'name_offset':hx(name-avbase)})
 old_look_valid=[x for x in old_look['lookup'] if 1<=x['input']<=29]
 assert len(old_look_valid)==29
 assert all(looks[i]['name']==old_look_valid[i]['name'] and looks[i]['descriptor_count']==old_look_valid[i]['descriptor_count'] for i in range(29))
 lookup_off=av.find(old[0x2c3334:0x2c3334+32]);assert lookup_off==0x2a650c
 code=decode(av_cs,av,lookup_off,0x90)
 lookup_code=[x for x in code if int(x['offset'],16)<lookup_off+0x90]
 assert lookup_code[12]['mnemonic']=='adrp' and lookup_code[13]['mnemonic']=='add'
 assert lookup_code[12]['op_str']=='x21, #0x36f000' and lookup_code[13]['op_str']=='x21, x21, #0xdf8'
 assert any(x['offset']=='0x2a6548' and x['mnemonic']=='ldr' and x['op_str']=='w9, [x21]' for x in lookup_code)
 assert any(x['offset']=='0x2a656c' and x['mnemonic']=='ldr' and x['op_str']=='x8, [x21, #0x18]' for x in lookup_code)
 edge={'entry_file_offset':hx(lookup_off),'entry_va':hx(avbase+lookup_off),'instruction_bytes_sha256':hashlib.sha256(av[lookup_off:lookup_off+0x90]).hexdigest(),
       'instructions':lookup_code,'table_offset':hx(table),'table_va':hx(avbase+table),
       'record22':looks[21],'record22_raw':av[table+21*32:table+22*32].hex(),
       'proof':'ADRP+ADD forms table address; LDR compares index; four LDR/STR pairs copy exact 32-byte record',
       'scope':'AV look descriptor lookup, not pixel conversion or DMA submission'}
 differences={'fx6_descriptor_count':len(d),'fx3_descriptor_count':len(old_idx),'same_name_and_payload_count':len(common),
              'same_name_and_payload':common,'fx6_only_names':only6,'fx3_only_names':only3,
              'vintage_renamed_and_changed':paired,
              'venice_descriptor_count':sum('VENICE' in x for x in d),
              'venice_all_payloads_match_fx3':all(d[n]['sha256']==old_idx[n]['sha256'] for n in d if 'VENICE' in n),
              'venice_matrix':{'fx6_descriptor_offset':hx(matrix['descriptor_offset']),'fx6_data_offset':hx(matrix['data_offset']),
                               'raw_words':raw,'signed_q16':old_ex['matrix']['signed_q16'],'same_as_fx3':True},
              'look_table_count':len(looks),'look_names_and_counts_match_fx3':True,'looks':looks,
              'fx3_initializer_scope':old_init['scope'],'fx3_look_scope':old_look['scope'],
              'limitations':['MLUT descriptors are post-sensor table/control data, not video RAW pixel transform proof',
                             'FX3 initializer/lookup CPU results are not FX6 runtime or FX6 DMA results',
                             'RawInfo/stillrecord AP symbols belong to still-photo branch; not video RAW/ISP evidence']}
 # Three static original-code paths copy the same SG3TOAP1_0 descriptor
 # into ACESCCT, ACESPROXY and ACESREC709 look arrays, respectively.
 copy_specs=[
  (0x2a2ca8,0x2a2cac,0x2a2ddc,0x2a2de0,0x2a2de4,0x2a2de8,0x2a2dec,0xaa1280,0x8e8,20),
  (0x2a2e6c,0x2a2e70,0x2a2f90,0x2a2f98,0x2a2f9c,0x2a2f94,0x2a2fa0,0xaa1f90,0x8e8,21),
  (0x2a300c,0x2a3010,0x2a35cc,0x2a35d8,0x2a35dc,0x2a35d4,0x2a35e0,0xaa2ca0,0x2568,22)]
 copy_edges=[]
 for adrp_base,add_base,mov_dest,adrp_src,add_src,len_ins,call,dest_base,delta,look_index in copy_specs:
  base_ops=decode(av_cs,av,adrp_base,8);src_ops=decode(av_cs,av,adrp_src,8)
  assert base_ops[0]['mnemonic']=='adrp' and base_ops[1]['mnemonic']=='add'
  assert base_ops[0]['op_str'].startswith('x23, ') and base_ops[1]['op_str'].startswith('x23, x23, ')
  assert int(base_ops[0]['op_str'].split('#')[1],16)+int(base_ops[1]['op_str'].split('#')[1],16)==dest_base
  assert src_ops[0]['op_str']=='x1, #0xb83000' and src_ops[1]['op_str']=='x1, x1, #0x218'
  assert 0xb83000+0x218==d['MLUT_MTX_A_REG_SG3TOAP1_0']['descriptor_offset']
  call_op=decode(av_cs,av,call,4)[0];assert call_op['mnemonic']=='bl' and call_op['op_str']=='#0xd80'
  length_op=decode(av_cs,av,len_ins,4)[0];assert length_op['op_str']=='w2, #0x98'
  dest_ops=decode(av_cs,av,mov_dest,8 if look_index==22 else 4)
  if look_index==22:
   assert dest_ops[0]['op_str']=='w8, #0x2568' and dest_ops[1]['op_str']=='x0, x23, x8'
  else:assert dest_ops[0]['op_str']==f'x0, x23, #0x{delta:x}'
  dest=dest_base+delta;look=looks[look_index-1];start=int(look['descriptor_array_offset'],16)
  assert start<=dest<start+look['descriptor_count']*152 and (dest-start)%152==0
  copy_edges.append({'look_index':look_index,'look_name':look['name'],
   'destination_base_offset':hx(dest_base),'destination_offset':hx(dest),
   'destination_descriptor_index':(dest-start)//152,
   'source_descriptor_name':'MLUT_MTX_A_REG_SG3TOAP1_0','source_offset':hx(d['MLUT_MTX_A_REG_SG3TOAP1_0']['descriptor_offset']),
   'source_data_offset':hx(d['MLUT_MTX_A_REG_SG3TOAP1_0']['data_offset']),
   'source_data_sha256':d['MLUT_MTX_A_REG_SG3TOAP1_0']['sha256'],
   'base_setup':base_ops,'source_setup':src_ops,'destination_setup':dest_ops,
   'length_setup':length_op,'call':call_op,'copy_bytes':152})
 fx3_copies=[x for x in old_init['copies'] if x['name']=='MLUT_MTX_A_REG_SG3TOAP1_0']
 assert len(fx3_copies)==3
 init_edges={'fx6_copy_edges':copy_edges,'fx3_cpu_replay_copies':fx3_copies,
  'fx6_evidence':'static original AArch64 instructions and table-relative destinations; no FX6 initializer execution',
  'fx3_evidence':'prior CPU-only initializer replay from pinned JSON; no camera DSP proof',
  'named_venice_matrix_not_direct_source':'FX6 code sources SG3TOAP1_0 record; its 13 matrix words equal VENICE-labelled record'}
 fx6_init_starts=[0x29e0d8,0x29f2d8,0x29f508]
 fx3_init_starts=[int(x,16) for x in old_init['initializer_offsets']]
 assert all(av[a:a+16]==old[b:b+16] for a,b in zip(fx6_init_starts,fx3_init_starts))
 init_edges['initializer_entry_candidates']=[{'fx6_offset':hx(a),'fx3_offset':hx(b),
  'same_first_16_bytes_sha256':hashlib.sha256(av[a:a+16]).hexdigest(),
  'fx6_first_32_instructions':decode(av_cs,av,a,32)} for a,b in zip(fx6_init_starts,fx3_init_starts)]
 config_setup=decode(av_cs,av,0x29f2e4,0x24)
 assert config_setup[0]['op_str']=='w8, #2'
 assert config_setup[1]['op_str']=='x19, #0xa87000'
 assert config_setup[2]['op_str']=='x19, x19, #0xff0'
 assert config_setup[3]['op_str']=='w8, [x19]'
 init_edges['configuration_static_edge']={'file_offset':'0x29f2e4','stored_value':2,'destination_offset':'0xa87ff0',
  'instructions':config_setup,'scope':'single static write path, not full FX6 configuration execution'}
 for name,obj in [('mapping.json',mapping),('config-evidence.json',config_evidence),('descriptor-diff.json',differences),('consumer-edge.json',edge),('initializer-edges.json',init_edges)]:
  (OUT/name).write_text(json.dumps(obj,indent=2)+'\n')
 print(json.dumps({'cp_base':hx(cpbase),'av_base':hx(avbase),'descriptors':len(d),'common_identical':len(common),'vintage_changed':len(paired),'lookup_offset':hx(lookup_off),'table_offset':hx(table)}))
if __name__=='__main__':main()
