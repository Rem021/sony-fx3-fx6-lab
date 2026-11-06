#!/usr/bin/env python3
"""Bounded original FX3 7.02 name/StopCmp/clip-info flow, entirely offline.

Original libc/libstdc++ are partial-linked at declared guest bases. No host
syscalls, allocator, log/lock, return/output stubs, native host execution or
device access. Tree/vector storage, owners and independent post-lock/lookup
entries are explicit fixtures, never a claim of full native writer execution.
"""
from pathlib import Path
import argparse
import datetime
import io
import json
import struct
import sys
import traceback
from elftools.elf.elffile import ELFFile

STAGE=Path(__file__).resolve().parent
BASE=STAGE.parent
sys.path.insert(0,str(BASE/'stage55-native-mux-identity'))
import mux_identity as prev
im,pp,r,MPR=prev.im,prev.pp,prev.r,prev.MPR
ROOT=prev.ROOT
S=pp.SCRATCH
PAIR,LITERAL,NOTIFY,REC,CLIP,WRITER=S+0x7000,S+0x7100,S+0x8000,S+0x9000,S+0xa000,S+0xb000
NAME_VECTOR=0x3b4b98
PRIOR_SHA='9d3122d7c42b808b0833571f1579de0aed740185f0b311ba06031679768f0da1'
PREFIX='_ZNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEE'
CPP_NAMES=[PREFIX+'6appendERKS4_',PREFIX+'9_M_appendEPKcm',PREFIX+'aSEOS4_',
  PREFIX+'9_M_assignERKS4_',PREFIX+'13_S_copy_charsEPcPKcS7_',PREFIX+'10_M_disposeEv']
C_NAMES=['strlen','strnlen','strncpy','memset','memcpy','memmove']
EXTRA_RANGES=[(0x117b20,0x117bc0),(0x2428a4,0x24292c),(0x243a10,0x243b44),
  (0xd6080,0xd60a8),(0xd60dc,0xd60f8),(0x1197d0,0x1197e8),
  (0x120b24,0x120b44),(0xda760,0xda7c8),(0xda7c8,0xda808),
  (0xda3b4,0xda420),(0xda4b0,0xda6ac),(0xd52bc,0xd52cc)]


class Runtime:
    def __init__(self,path,pin,base,names):
        self.path=path;self.blob=path.read_bytes();assert im.sha(self.blob)==pin
        self.elf=ELFFile(io.BytesIO(self.blob));self.base=base
        assert self.elf['e_machine']=='EM_AARCH64' and self.elf['e_type']=='ET_DYN'
        self.segments=[s for s in self.elf.iter_segments() if s['p_type']=='PT_LOAD']
        dyn=self.elf.get_section_by_name('.dynsym')
        self.symbols={s.name:{'va':base+s['st_value'],'relative_va':s['st_value'],
          'size':s['st_size'],'type':s['st_info']['type']} for s in dyn.iter_symbols()
          if s.name and s['st_shndx']!='SHN_UNDEF'}
        for n in names:assert self.symbols[n]['type']=='STT_FUNC' and self.symbols[n]['size']>0
        self.allowed_names=names
        self.ranges=[(self.symbols[n]['va'],self.symbols[n]['va']+self.symbols[n]['size']) for n in names]
        pl=self.elf.get_section_by_name('.plt');rl=self.elf.get_section_by_name('.rela.plt')
        self.plt={base+pl['sh_addr']+32+i*16:dyn.get_symbol(x['r_info_sym']).name
          for i,x in enumerate(rl.iter_relocations())}

    def map(self,u):
        pages=set()
        for s in self.segments:
            pages.update(range((self.base+s['p_vaddr'])&~4095,
              (self.base+s['p_vaddr']+s['p_memsz']+4095)&~4095,4096))
        runs=[]
        for a in sorted(pages):
            if runs and runs[-1][1]==a:runs[-1][1]=a+4096
            else:runs.append([a,a+4096])
        for a,z in runs:u.mem_map(a,z-a)
        for s in self.segments:u.mem_write(self.base+s['p_vaddr'],s.data())
        # No runtime imports, constructors, CPU feature resolver, TLS or syscalls
        # are fabricated. Only file-defined symbols/relative relocations resolve.
        for sec in self.elf.iter_sections():
            if sec.name not in ('.rela.dyn','.rela.plt'):continue
            table=self.elf.get_section(sec['sh_link'])
            for x in sec.iter_relocations():
                kind=x['r_info_type'];value=None
                if kind==1027:value=self.base+x['r_addend']
                elif kind in (1025,1026):
                    sy=table.get_symbol(x['r_info_sym'])
                    if sy['st_shndx']!='SHN_UNDEF':value=self.base+sy['st_value']+x['r_addend']
                if value is not None:u.mem_write(self.base+x['r_offset'],struct.pack('<Q',value))
        for a,z in runs:u.mem_protect(a,z-a,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_EXEC)

    def receipt(self):
        return {'file':str(self.path.relative_to(ROOT)),'sha256':im.sha(self.blob),
          'guest_base_not_camera_load_address':hex(self.base),
          'approved_original_functions':{n:self.symbols[n] for n in self.allowed_names}}


LIBC=Runtime(STAGE/'official-files/nflasha7/lib/libc-2.25.so',
  'f9104526eb7e5d2ea533c1a209bb0b83e69367f569e4c966895c8e106e6382c9',0x14000000,C_NAMES)
CPP=Runtime(STAGE/'official-files/nflasha15/lib/libstdc++.so.6.0.22',
  '28f2d082aea5206c42ba15664f39e2eaf7febed8f6264305e7e16aa44c878389',0x16000000,CPP_NAMES)


class Guest(prev.Guest):
    def __init__(self):
        super().__init__();self.allowed+=EXTRA_RANGES
        for lib in (LIBC,CPP):lib.map(self.uc)
        self.boundaries.update({0xc8c70:'before_original_diagnostic',
          0xd60a8:'before_factory_allocation',0xd60f8:'before_full_registration',
          0x1197e8:'after_registration_before_allocation',
          0xda560:'after_selected_StopCmp_copy_before_completion_logic',
          0xda6ac:'before_unrecognized_writer_diagnostic',
          0xd52cc:'after_65byte_clip_name_copy'})
        self.entry_observations=[]

    def code(self,u,address,size,user):
        # Read-only observations. This hook never creates caller outputs.
        if address in (0xda760,0xda3b4):
            self.entry_observations.append({'entry':hex(address),
              'arguments_x0_x5':[hex(u.reg_read(getattr(r.reg,'UC_ARM64_REG_X'+str(i)))) for i in range(6)]})
        for lib in (LIBC,CPP):
            name=(MPR.plt.get(address) if address in MPR.plt else lib.plt.get(address))
            if name and name in lib.allowed_names:
                target=lib.symbols[name]['va'];self.pcs.append(hex(address));self.steps+=1
                self.calls.append({'PLT':hex(address),'symbol':name,'original_library_target':hex(target),
                  'library_sha256':im.sha(lib.blob),'partial_link_only_no_synthesized_return':True})
                u.reg_write(r.reg.UC_ARM64_REG_PC,target);return
        for lib in (LIBC,CPP):
            if any(a<=address and address+size<=z for a,z in lib.ranges):
                self.pcs.append(hex(address));self.steps+=1
                word=int.from_bytes(u.mem_read(address,4),'little')
                if word & 0xffe0001f in (0xd4000001,0xd4000002,0xd4000003):
                    self.abort('SVC/HVC/SMC forbidden');return
                if word==0xd65f03c0:
                    self.calls.append({'return_instruction':hex(address),
                      'return_x0':hex(u.reg_read(r.reg.UC_ARM64_REG_X0))})
                return
        return super().code(u,address,size,user)


def reg(m,index,value):
    m.uc.reg_write(getattr(r.reg,'UC_ARM64_REG_X'+str(index)),value)


def phase(m,label,entry,args=(),registers=None):
    for index,value in (registers or {}).items():reg(m,index,value)
    m.entry_observations=[]
    e=prev.phase(m,label,entry,args)
    e['native_named_entries']=list(m.entry_observations)
    e['original_runtime_functions_not_host_string_adapters']=True
    return e


def assert_code(m):
    prev.assert_code(m)
    for lib in (LIBC,CPP):
        for seg in lib.segments:
            if seg['p_flags']&1:
                assert bytes(m.uc.mem_read(lib.base+seg['p_vaddr'],seg['p_filesz']))==seg.data()


def metadata(m,events,pairs,seed):
    data=bytearray(0x200);struct.pack_into('<5I',data,0x11c,3,6,6,0,0)
    m.uc.mem_write(prev.INPUT,bytes(data));m.uc.mem_write(prev.VIDEO,bytes([seed])*0x48)
    m.uc.mem_write(prev.AUDIO,bytes([seed])*0x64)
    for a,p,n in ((0x115e18,prev.VIDEO,'video'),(0x115e54,prev.AUDIO,'audio')):
        e=phase(m,'original '+n+' initializer',a,[p]);assert e['reason']=='returned';events.append(e)
    e=phase(m,'original full metadata converter',0x115fec,[0,prev.INPUT,prev.VIDEO,prev.AUDIO])
    assert e['reason']=='returned' and e['return_u64']==0;events.append(e)
    raw=bytes(m.uc.mem_read(prev.VIDEO,0x48));f=prev.fields(raw)
    assert f['width_height_3c_3e']==[1920,1080] and f['bitrate_raw40']==16000
    assert f['rate_2c_30']==[30000,1001]
    prev.fixture_map(m,pairs)
    return raw,f


def one_case(label,seed,pairs,control_name=None,vector_key=0x97):
    m=Guest();events=[];raw,fields=metadata(m,events,pairs,seed)
    literal=0x2cfb4f
    if control_name is not None:
        assert len(control_name)<=15 and b'\0' not in control_name
        literal=LITERAL;m.uc.mem_write(LITERAL,control_name+b'\0')
    else:assert MPR.read(literal,1)==b'\0'
    m.uc.mem_write(PAIR,bytes([seed])*0x28)
    m.uc.mem_write(PAIR,struct.pack('<I',vector_key))
    e=phase(m,'original std::string constructor from '+('official empty literal' if control_name is None else 'artificial short-name control'),
      0x2428a4,[PAIR+8,literal])
    assert e['reason']=='returned';events.append(e)
    obj=bytes(m.uc.mem_read(PAIR+8,0x20))
    expected=control_name or b''
    assert struct.unpack_from('<2Q',obj)==(PAIR+0x18,len(expected))
    assert bytes(m.uc.mem_read(PAIR+0x18,len(expected)+1))==expected+b'\0'
    # One-entry vector fixture, not a full global ctor or actual camera vector.
    m.uc.mem_write(NAME_VECTOR,struct.pack('<3Q',PAIR,PAIR+0x28,PAIR+0x28))
    m.uc.mem_write(NOTIFY,bytes([seed])*0x100)
    e=phase(m,'complete original ConvertVideoCodecTypeName',0x117b20,
      [WRITER,prev.VIDEO,0,NOTIFY+0x64]);events.append(e)
    assert e['reason']=='returned' and e['return_u64']==0
    name=expected if vector_key==0x97 else b''
    actual=bytes(m.uc.mem_read(NOTIFY+0x64,0x80))
    assert actual==name+bytes(0x80-len(name))
    assert bytes(m.uc.mem_read(prev.VIDEO,0x48))==raw
    assert hex(0x24d79c) in e['pcs'] and hex(0x243a10) in e['pcs']
    assert any(x.get('symbol')=='strncpy' for x in e['calls'])
    # Observe real formatter -> receiver data, with independent post-lookup
    # record-owner fixtures. No source name editing after native production.
    ownership=[]
    for owner,uid,proxy in (('MAIN',1,False),('PROXY',5,True),('wrong UID',2,False)):
        record=bytearray([seed])*0x400
        struct.pack_into('<I',record,8,1);record[0x140]=int(proxy)
        struct.pack_into('<I',record,0x148,5)
        m.uc.mem_write(REC,bytes(record))
        e=phase(m,'independent post-lookup StopCmp '+owner,0xda4b0,
          registers={19:REC,20:NOTIFY,24:1,25:0,26:uid})
        events.append(e)
        if owner=='wrong UID':
            assert e['reason']=='boundary: before_unrecognized_writer_diagnostic'
            assert bytes(m.uc.mem_read(REC,len(record)))==bytes(record)
            ownership.append({'owner':owner,'uid':uid,'record_unchanged':True,'copied':False});continue
        assert e['reason']=='boundary: after_selected_StopCmp_copy_before_completion_logic'
        offset=0x1c0 if proxy else 0x80;flag=0x15c if proxy else 0x1c
        copied=bytes(m.uc.mem_read(REC+offset,0x80))
        assert copied[:0x7f]==name+bytes(0x7f-len(name)) and copied[0x7f]==seed
        assert bytes(m.uc.mem_read(REC+flag,1))==b'\x01'
        other=0x80 if proxy else 0x1c0
        assert bytes(m.uc.mem_read(REC+other,0x80))==bytes([seed])*0x80
        clip_result=None
        if not proxy:
            clip=bytes([seed])*0x800;m.uc.mem_write(CLIP,clip)
            e2=phase(m,'independent MAIN clip-info name copy suffix',0xd52bc,
              registers={19:CLIP,20:REC});events.append(e2)
            assert e2['reason']=='boundary: after_65byte_clip_name_copy'
            output=bytes(m.uc.mem_read(CLIP,0x800))
            assert output[0x6ac:0x6ed]==copied[:0x41]
            assert output[:0x6ac]==clip[:0x6ac] and output[0x6ed:]==clip[0x6ed:]
            clip_result={'65byte_name_hex':output[0x6ac:0x6ed].hex(),
              'separate_codec_scalar_6a8_unchanged':output[0x6a8:0x6ac]==clip[0x6a8:0x6ac],
              'codec_scalar_producer_not_executed':True}
        ownership.append({'owner':owner,'uid':uid,'copied':True,'name_offset':hex(offset),
          'copied_name_128_hex':copied.hex(),'byte127_outside_native_strncpy127_retains_seed':seed,
          'other_name_field_unchanged':True,'native_completion_flag_set':True,'clip_info_suffix':clip_result})
    assert bytes(m.uc.mem_read(NOTIFY+0x64,0x80))==actual
    assert_code(m)
    return {'label':label,'prior_seed':seed,'original_video_metadata_hex':raw.hex(),
      'metadata_fields':fields,'classification_expected_from_original_default_map':0x97,
      'vector_fixture_key':vector_key,'vector_entries':1,'native_constructed_string_object_hex':obj.hex(),
      'artificial_name_control':control_name is not None,'official_empty_literal':hex(0x2cfb4f),
      'native_name_output_128_hex':actual.hex(),'native_name_ascii':name.decode('ascii'),
      'owner_copy_controls':ownership,'events':events,
      'full_global_constructors_log_lock_record_lookup_clip_codec_or_actual_Stop_executed':False}


def callback_binding():
    m=Guest();events=[];frame=pp.STACK-0x1000
    e=phase(m,'native factory callback pointer load before allocation',0xd6080,registers={29:frame})
    assert e['reason']=='boundary: before_factory_allocation';events.append(e)
    callback=m.uc.reg_read(r.reg.UC_ARM64_REG_X23);sequence=m.uc.reg_read(r.reg.UC_ARM64_REG_X26)
    assert callback==0xda760
    # Native factory allocation/constructor is unexecuted. This one pointer is
    # a declared owner fixture, not a returned allocator/constructor result.
    m.uc.mem_write(sequence+8,struct.pack('<Q',WRITER))
    e=phase(m,'native factory callback parameter packing independent suffix',0xd60dc,
      registers={29:frame,26:sequence,23:callback,28:1,24:0x2710,27:0x64,25:0})
    assert e['reason']=='boundary: before_full_registration';events.append(e)
    params=frame+0x88
    assert bytes(m.uc.mem_read(params,24))==struct.pack('<3Q',callback,1,0)
    e=phase(m,'native registration storage independent fragment',0x1197d0,
      registers={19:WRITER,20:params})
    assert e['reason']=='boundary: after_registration_before_allocation';events.append(e)
    assert bytes(m.uc.mem_read(WRITER+0x38,24))==struct.pack('<3Q',callback,1,0)
    m.uc.mem_write(NOTIFY,bytes(0x100))
    e=phase(m,'original producer event and indirect registered callback',0x120b24,
      registers={25:WRITER,27:NOTIFY})
    assert e['reason']=='boundary: before_original_diagnostic';events.append(e)
    assert e['native_named_entries']==[{'entry':'0xda760',
      'arguments_x0_x5':[hex(x) for x in (1,0x40000001,0,NOTIFY,0,0)]}]
    callback_frame=m.uc.reg_read(r.reg.UC_ARM64_REG_X29)
    # This is expressly an independent post-lock input: log/lock were NOT
    # executed or made to return. Native prefix-produced argument bytes reused.
    e=phase(m,'independent callback post-lock event dispatch',0xda7c8,
      registers={29:callback_frame,19:0x40000001,21:1})
    assert e['reason']=='boundary: before_original_diagnostic';events.append(e)
    assert e['native_named_entries']==[{'entry':'0xda3b4',
      'arguments_x0_x5':[hex(x) for x in (1,0x40000001,0,NOTIFY,0,0)]}]
    assert_code(m)
    return {'callback_va':hex(callback),'event':hex(0x40000001),
      'native_named_receiver':'_ZN3mpr20RecvWriterEvtStopCmpEmjiPvjS0_',
      'registration_parameters_callback_uid_userdata':[hex(callback),1,0],
      'factory_owner_pointer_is_fixture':True,'producer_full_Stop_and_locks_not_executed':True,
      'independent_post_lock_dispatch_not_resume_or_lock_success_adapter':True,'events':events}


def allocation_denied():
    m=Guest();text=b'LONG_NAME_ALLOCATION_CONTROL'
    m.uc.mem_write(LITERAL,text+b'\0')
    e=phase(m,'deliberately too-long fixture denied before allocator',0x2428a4,[PAIR+8,LITERAL])
    assert e['reason']=='unapproved PLT '+PREFIX+'9_M_createERmm'
    assert_code(m)
    return e


def run(out):
    prior=prev.STAGE/'final-receipt.json';assert im.sha(prior.read_bytes())==PRIOR_SHA
    for row in json.loads(prior.read_text())['files']:
        assert im.sha((ROOT/row['path']).read_bytes())==row['sha256']
    assert (BASE/'GOAL_STATUS.json').read_bytes()==(STAGE/'goal-status-before.json').read_bytes()
    pairs,key_events=prev.original_map_pairs()
    cases=[one_case('original empty fallback priorA5',0xa5,pairs),
      one_case('original empty fallback priorC3',0xc3,pairs),
      one_case('artificial short name control',0xa5,pairs,b'CONTROL'),
      one_case('artificial missing vector key control',0xa5,pairs,b'CONTROL',0x96)]
    binding=callback_binding();denied=allocation_denied()
    regions=[('original fallback name vector initialization',0x8ef38,0x8ef78),
      ('complete name formatter',0x117b20,0x117bc0),
      ('optional completion record gating and name destination',0x1205e4,0x120624),
      ('formatter caller ignores scalar return',0x120760,0x1207a0),
      ('producer callback handoff',0x120b24,0x120b44),
      ('native callback event dispatch',0xda7c8,0xda818),
      ('MAIN StopCmp copy',0xda4b0,0xda560),('proxy StopCmp copy',0xda5ec,0xda6ac),
      ('clip codec scalar precedes name copy',0xd52b4,0xd52d0)]
    proof={'status':'PASS_ORIGINAL_EMPTY_NAME_STOP_AND_CLIP_SUFFIX_WITH_EXPLICIT_BOUNDARIES',
      'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'original_fragments':len(key_events)+sum(len(c['events']) for c in cases)+len(binding['events'])+1,
      'original_default_map_key_events':key_events,'runtime_libraries':[LIBC.receipt(),CPP.receipt()],
      'cases':cases,'callback_binding':binding,'allocation_denial_control':denied,
      'original_regions':[{'name':name,'instructions':prev.instructions(a,z)} for name,a,z in regions],
      'scope':{'raw16000_metadata_is_not_measured_encoded_bitrate':True,
        'empty_name_reaches_MAIN_record_and_clip_info_name_suffix':True,
        'record_format_classifier_caller_is_Stop_completion_metadata_not_Open_admission':True,
        'empty_name_is_globally_harmless_or_only_cosmetic_proven':False,
        'full_formatter_native_original_runtime_no_result_adapters':True,
        'map_vector_and_owner_inputs_are_fixtures':True,
        'full_record_lookup_log_lock_MP4_close_commit_or_complete_Stop':False,
        'resource_FH_quality_alignment_full_Open_Start_Hal_real_file_audio_longrun':False,
        'camera_USB_UU_Windows_file_protocol_auth_module_WBI_or_flash':False,
        'healthy_same_body_backup_restore_coldboot_or_independent_rescue':False,
        'goal_complete':False,'persistent_write_release':False}}
    im.write_json(out/'stop-name-flow-results.json',proof)
    (out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    im.write_json(out/'source-receipt.json',{'script_sha256':im.sha(Path(__file__).read_bytes()),
      'MPR_sha256':im.sha(MPR.blob),'runtime_libraries':proof['runtime_libraries'],
      'prior_manifest_sha256':PRIOR_SHA,
      'extraction_receipt_sha256':im.sha((STAGE/'official-extraction-receipt.json').read_bytes()),
      'volume_uuid':im.VOLUME})
    print(json.dumps({'status':proof['status'],'original_fragments':proof['original_fragments'],
      'name_cases':[(x['label'],x['native_name_ascii']) for x in cases],
      'original_callback':binding['native_named_receiver'],'goal_complete':False}))


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',required=True)
    args=ap.parse_args();im.volume();out=Path(args.output).resolve()
    assert STAGE in out.parents and not out.exists();out.mkdir()
    try:run(out)
    except Exception:
        (out/'attempt-source.py').write_bytes(Path(__file__).read_bytes())
        if 'LAST_PHASE' in vars(prev):im.write_json(out/'last-phase-at-failure.json',prev.LAST_PHASE)
        im.write_json(out/'attempt-failure.json',{'traceback':traceback.format_exc(),'passing_result':False})
        raise


if __name__=='__main__':main()
