#!/usr/bin/env python3
"""Original frame construction/header and native geometry/crop reconciliation.

Fresh frame parameters stay unowned after the first reference-count boundary.
Numeric crop agreement is not a generated HEVC bitstream or hardware acceptance.
"""
from pathlib import Path
import argparse
import datetime
import json
import struct
import sys
import traceback

STAGE=Path(__file__).resolve().parent
BASE,ROOT=STAGE.parent,STAGE.parent.parents[1]
sys.path.insert(0,str(BASE/'stage92-native-geometry-builder-and-IRQ-scope'))
import geometry_builder as prev
old=prev.old
im,u,reg,cs,IMAGE=prev.im,prev.u,prev.reg,prev.cs,prev.IMAGE
PRIOR_SHA='f4ab27250570923bcd4e4eccd5e0de20636f851c186c9b51252006579111f69f'
SP_FRAME,SP_PREP,SP_CROP=[old.STACK+x for x in (0x2000,0x8000,0xe000)]
COMMON_PA,COMMON=0x01800000,0x81800000
CODEC_PA,CODEC=0x01900000,0x81900000
CONFIG_PA,CONFIG=0x01a00000,0x81a00000
STOPS={**prev.STOPS,
    0x131c20:'fresh_frame_handle_assigned_before_unexecuted_GP_reference_increment',
    0x1441e4:'frame_producer_and_wrapper_returned_before_unbound_virtual_table_lookup',
    0x18cdf4:'original_geometry_packed_before_chroma_body',
    0x18ce7c:'original_vertical_crop_result_stored_before_other_format_work'}
LIMITS=prev.LIMITS+((0x1f8550,0x1f87c0),(0x1f8bbc,0x1f8cf4),
    (0x1c27b8,0x1c28f4),(0x199258,0x199298),(0x67f08,0x67fa8),
    (0x131888,0x131b68),(0x131c18,0x131c20),(0x131cb8,0x131cfc),
    (0x131dbc,0x131dd0),(0x131e2c,0x131e34),(0x134644,0x1346c0),
    (0x1351c0,0x1351cc),(0x1441d8,0x1441e4),
    (0x18cd8c,0x18cdf4),(0x18ce40,0x18ce7c),(0x198478,0x198528))


def ins(value,field,lo,width):
    mask=((1<<width)-1)<<lo
    return ((value&~mask)|((field<<lo)&mask))&0xffffffff


class Guest(prev.Guest):
    def code(self,uc,pc,size,user):
        self.pcs.append(pc)
        if pc==old.TRAP:self.reason='returned_via_original_jr_ra';uc.emu_stop();return
        off=pc-IMAGE
        if off in self.stops:self.reason=self.stops[off];uc.emu_stop();return
        assert len(self.pcs)<20000
        assert any(lo<=off and off+size<=hi for lo,hi in LIMITS),(hex(pc),size)
        instruction=next(self.md.disasm(self.blob[off:off+size],pc),None)
        assert instruction is not None,(hex(pc),self.blob[off:off+size].hex())
        if instruction.mnemonic=='break':assert off in (0x13489c,0x198508)
        else:assert instruction.mnemonic not in {'syscall','cache','sync','mfc0','mtc0','eret',
            'wait','tlbwi','tlbwr','tlbr','tlbp','jalr'},(hex(pc),instruction.mnemonic)
        if off==0x66bb8:
            self.geometry_arguments.append({n:uc.reg_read(getattr(reg,'UC_MIPS_REG_'+n.upper())) for n in ('a0','a1','a2')})
        if off==0x198500:
            self.crop_divisions.append({'numerator':uc.reg_read(reg.UC_MIPS_REG_V1),
                'unit':uc.reg_read(reg.UC_MIPS_REG_T0)})

    def run(self,label,entry,sp=prev.SP_SEL,extra_stops=None,allow_interrupt=False,
            preserve=False,remove_stops=(),**regs):
        init={} if preserve else {'sp':sp,'ra':old.TRAP,'gp':old.GP,'fp':0,**{f's{i}':0 for i in range(8)}}
        for name,value in {**init,**regs}.items():self.uc.reg_write(getattr(reg,'UC_MIPS_REG_'+name.upper()),value)
        self.reason=None;self.pcs=[];self.interrupts=[];self.geometry_arguments=[];self.crop_divisions=[]
        self.stops={**STOPS,**(extra_stops or {})}
        for off in remove_stops:self.stops.pop(off)
        self.uc.emu_start(IMAGE+entry,0,timeout=1000000,count=0)
        assert not allow_interrupt
        assert self.reason in set(self.stops.values())|{'returned_via_original_jr_ra'} and not self.interrupts,self.reason
        assert bytes(self.uc.mem_read(0,len(self.blob)))==self.blob
        assert bytes(self.uc.mem_read(old.STACK_PA,65536))==self.stack
        assert bytes(self.uc.mem_read(old.TRAP_PA,4096))==bytes(4096)
        for at,raw in self.want.items():assert self.read(at)==bytes(raw),hex(at)
        return {'label':label,'entry':hex(IMAGE+entry),'stop':self.reason,
            'pc':hex(self.uc.reg_read(reg.UC_MIPS_REG_PC)),
            'SP':hex(self.uc.reg_read(reg.UC_MIPS_REG_SP)),'RA':hex(self.uc.reg_read(reg.UC_MIPS_REG_RA)),
            'V0':hex(self.uc.reg_read(reg.UC_MIPS_REG_V0)),
            'CODE_observed_PCs':[hex(x) for x in self.pcs],
            'native_geometry_helper_arguments':self.geometry_arguments,'native_crop_divisions':self.crop_divisions,
            'original_image_all_pages_and_entire_stack_exact_poststate_checked':True,
            'memory_read_write_hooks_installed':False,'native_interrupts':self.interrupts,
            'PC_observation_may_include_annulled_delay_slots':True,
            'MMIO_instruction_patch_or_fake_return':False}

    def construct_frame(self):
        f=self.want[old.FRAME_PA]
        for at in (0,1,2,0x14,0x38,0x39,0x3a,0x3b,0x3c,0x3d,0x44,0x58,0x6c,
                   0xd0,0xd1,0xd2,0xd3,0xd4,0xd5,0xd6,0x438,0x439,0x4c4,0x4d0,
                   0x4d8,0x4d9,0x4da,0x4db,0x4dc):f[at]=0
        f[4:0x14]=bytes(16);f[0xa4:0xb2]=bytes(14)
        for at in (0x18,0x1c,0x20,0x24,0x28,0x2c,0x30,0x34,0x40,0x48,0x4c,0x50,0x54,
                   0x5c,0x60,0x64,0x68,0x70,0x74,0x78,0x7c,0x80,0x84,0x88,0x8c,
                   0x90,0x94,0x98,0x9c,0xb4,0xb8,0xc0,0xdc,
                   0x3e8,0x3ec,0x3f0,0x3f4,0x3f8,0x3fc,0x400,0x404,
                   0x408,0x40c,0x410,0x414,0x418,0x41c,0x420,0x428,0x42c,0x430,0x434,
                   0x468,0x46c,0x478,0x47c,0x480,0x484,0x490,0x494,0x498,0x49c,
                   0x4a0,0x4a4,0x4a8,0x4ac,0x4b0,0x4b4,0x4b8,0x4bc,0x4c0,0x4c8,0x4cc,
                   0x4d4,0x4e8):struct.pack_into('<I',f,at,0)
        for at in (0xd8,0xe0,0x4e4):struct.pack_into('<H',f,at,0)
        for at in (0xa0,0xc8,0xcc):struct.pack_into('<I',f,at,0xffffffff)
        f[0xbc]=1;f[0x4e0:0x4e4]=bytes([15])*4
        # Original nested constructors/memsets retain their alignment holes.
        for lo,hi in ((0xe8,0x143),(0x144,0x27c),(0x280,0x3e8),(0x440,0x468)):
            f[lo:hi]=bytes(hi-lo)
        struct.pack_into('<I',f,0x43c,old.GP-0x5d58)
        for at in (0x470,0x474,0x488,0x48c):struct.pack_into('<I',f,at,1)
        base=SP_FRAME-0x20
        self.save(base+0x10,0);self.save(base+0x14,old.TRAP)
        nested=base-0x20
        for off,value in ((0x10,old.FRAME),(0x14,0),(0x18,0),(0x1c,IMAGE+0x1f8680)):
            self.save(nested+off,value)
        e=self.run('complete original frame constructor including nested constructors and memsets',
                   0x1f8550,sp=SP_FRAME,a0=old.FRAME)
        assert e['stop']=='returned_via_original_jr_ra' and e['SP']==hex(SP_FRAME)
        assert old.word(f,0x4c8)==0 and f[0x4c4]==0
        return e

    def prepare_geometry(self,units,mode):
        self.save(SP_PREP-0x10,old.TRAP);self.save(SP_PREP-0x30,IMAGE+0x134fa0)
        struct.pack_into('<HH',self.want[old.OWNER_PA],0x24,*units)
        data,classes,dimensions=self.expected_geometry(units,mode)
        self.geometry_stack(SP_PREP-0x40,old.OWNER+0x10,old.OWNER+8,0,0,0,IMAGE+0x131e68,classes)
        e=self.run('original geometry setter prepares existing dimensions for both update controls',
                   0x134f8c,sp=SP_PREP,a0=old.OWNER,a1=units[0]-1,a2=units[1]-1)
        assert e['stop']=='returned_via_original_jr_ra' and e['SP']==hex(SP_PREP)
        assert [(x['a0'],x['a1']) for x in e['native_geometry_helper_arguments']]==[dimensions]
        return e

    def header(self,flag):
        f=self.want[old.FRAME_PA];o=self.want[old.OWNER_PA];src=self.want[old.SRC_PA]
        initial_o=bytes(o);base=prev.SP_CALL-0x80
        self.save(base-0x20+0x10,old.FRAME);self.save(base-0x20+0x14,IMAGE+0x131898)
        f[0]=src[2];f[1]=0;f[2]=int(o[0x2a]!=0)
        w,h=struct.unpack_from('<HH',o,0x24)
        struct.pack_into('<4H',f,4,w,h,h,h)
        value=ins(old.word(f,0xc),1,18,2)&0xfffff
        value=ins(value,(struct.unpack_from('<H',o,0x98)[0]+1)&0xffffffff,16,2)
        struct.pack_into('<I',f,0xc,value)
        struct.pack_into('<HH',f,0x10,(w<<4)&0xffff,(h<<4)&0xffff)
        v=ins(old.word(f,0x2c),old.word(o,0x98),0,1)
        v=ins(v&0xffffff8f,0,29,3)
        table=self.blob[0x248cc4:0x248cc7]
        v=ins(v,table[o[8]],21,2);v=ins(v,table[o[9]],23,1)
        struct.pack_into('<I',f,0x2c,v)
        v=ins(old.word(f,0x30),o[0x31],30,1);v=ins(v,o[0x32],31,1)
        struct.pack_into('<I',f,0x30,ins(v,o[0xf],12,4))
        f[0x4d8]=f[0x4d9]=0
        f[0x38:0x3b]=o[0xa:0xd];f[0x3b]=(o[0xd]+o[0xe])&255
        f[0x3c]=f[0x39];f[0x3d]=f[0x3b]
        f[0x14:0x28]=initial_o[0x80:0x94]
        # The flag's three padding bytes come from the original current stack;
        # preserve them rather than assigning zero or naming them meaningful.
        before_flag=old.word(self.stack,base+0x10-old.STACK)
        flagword=(before_flag&0xffffff00)|1
        for off,value in ((0x10,flagword),(0x14,old.word(src,0x10)),
                          (0x18,old.word(src,0x14)),(0x1c,old.word(src,0x18)),(0x20,0)):
            self.save(base+off,value)
        struct.pack_into('<5I',f,0x6c,flagword,old.word(src,0x10),old.word(src,0x14),old.word(src,0x18),0)
        struct.pack_into('<5I',o,0x80,flagword,old.word(src,0x10),old.word(src,0x14),old.word(src,0x18),0)
        f[0x4da]=int(o[0x36]!=0);f[0x4db]=int(o[0x35]!=0)
        struct.pack_into('<I',o,0x98,(1-old.word(initial_o,0x98))&0xffffffff)
        if flag:
            f[0x4c4]=flag;struct.pack_into('<I',f,0x4c8,old.HANDLES+4)
        else:
            struct.pack_into('<H',f,0xc,struct.unpack_from('<H',o,0x28)[0])
            if o[0x37]:f[0x4d0]=1
        e=self.run('resume same native frame producer at first unexecuted header instruction',
                   0x131888,preserve=True,remove_stops=(0x131888,))
        assert e['stop']==STOPS[0x131c20 if flag else 0x1441e4]
        assert e['SP']==hex(base if flag else prev.SP_CALL)
        if not flag:assert e['V0']==hex(old.FRAME)
        return e,{'padding_flag_word_before_low_byte_store':hex(before_flag),
            'native_stored_flag_word':hex(flagword),
            'owner98_before':hex(old.word(initial_o,0x98)),
            'owner98_after':hex(old.word(o,0x98)),
            'owner80_90_before_hex':initial_o[0x80:0x94].hex(),
            'raw_source_and_partial_owner_fields_remain_declared_not_camera_values':True}


def frame_case(blob,seed,mode,flag):
    m=Guest(blob,seed,mode,flag,(120,68));es=[m.construct_frame(),m.defaults()]
    e,_=m.classify_and_build((120,68),mode);es.append(e)
    es.append(m.prepare_geometry((120,68),mode))
    es.append(m.caller((120,68),mode,flag))
    e,details=m.header(flag);es.append(e)
    f=m.read(old.FRAME_PA)
    return {'seed':seed,'declared_raw_mode0e':mode,'declared_update_byte50':flag,
        'native_frame_block_units':list(struct.unpack_from('<HH',f,4)),
        'native_frame_pixel_fields':list(struct.unpack_from('<HH',f,0x10)),
        'native_frame_parameter_handle':old.word(f,0x4c8),
        'new_parameter_reference_completed':False,
        'frame_producer_returned_to_actual_caller':not bool(flag),
        'details':details,'final_pages':{hex(at):m.read(at).hex() for at in m.want},'events':es,
        'real_MAIN_1080_crop_bitstream_hardware_or_recovery_proven':False}


def crop_case(blob,source,visible_height):
    seed=source['seed'];m=Guest(blob,seed,1,0x10,(120,68))
    common=bytearray.fromhex(source['common_input_hex']);codec=bytes.fromhex(source['codec_input_hex'])
    assert len(common)==64 and len(codec)==448 and codec[0]==2 and codec[0x22]==1
    assert sum(old.word(common,o) for o in (0xc,0x14,0x18))==1920
    assert old.word(common,0x1c)==old.word(common,0x20)==0
    original_height=old.word(common,0x10);assert original_height==1080
    struct.pack_into('<I',common,0x10,visible_height)
    for at,raw,prot in ((COMMON_PA,bytes(common)+bytes(4096-64),u.UC_PROT_READ),
        (CODEC_PA,codec+bytes(4096-448),u.UC_PROT_READ),
        (CONFIG_PA,bytes([seed])*4096,u.UC_PROT_READ|u.UC_PROT_WRITE)):
        m.uc.mem_map(at,4096,prot);m.uc.mem_write(at,raw);m.want[at]=bytearray(raw)
    cfg=m.want[CONFIG_PA];cfg[0x34:0x37]=codec[0x1f:0x22];cfg[0x37]=0
    struct.pack_into('<HH',cfg,0x38,119,67)
    es=[m.run('original HEVC geometry packing from declared visible dimensions',
              0x18cd8c,sp=SP_CROP,s1=CONFIG,s2=COMMON,s3=CODEC+0x18)]
    m.save(SP_CROP+0x10,0);m.save(SP_CROP+0x14,codec[0x3d])
    cfg[0x47]=(1088-visible_height)//2
    es.append(m.run('original vertical crop caller, native divide and result store',
        0x18ce40,sp=SP_CROP,s1=CONFIG,s2=COMMON,s3=CODEC+0x18))
    assert es[1]['native_crop_divisions']==[{'numerator':1088-visible_height,'unit':2}]
    result=m.read(CONFIG_PA)[0x47]
    assert 1088-result*2==visible_height
    return {'seed':seed,'source_kind':source['kind'],'source_label':source['source_label'],
        'declared_visible_width':1920,'declared_visible_height':visible_height,
        'original_height':original_height,'input_height_edit':visible_height!=original_height,
        'native_block_units':[120,68],'native_vertical_crop':result,'native_crop_unit':2,
        'reconciled_height':1088-result*2,'common_input_hex':common.hex(),'codec_input_hex':codec.hex(),
        'config_after_hex':m.read(CONFIG_PA).hex(),'events':es,
        'geometry_and_crop_entries_separate_from_full_HEVC_function':True,
        'SPS_or_actual_HEVC_bitstream_hardware_acceptance_proven':False}


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);out=Path(p.parse_args().output)
    im.volume();assert not out.exists()
    prior=BASE/'stage92-native-geometry-builder-and-IRQ-scope/final-receipt.json'
    assert im.sha(prior.read_bytes())==PRIOR_SHA
    for f in json.loads(prior.read_text())['files']:
        raw=(ROOT/f['path']).read_bytes();assert len(raw)==f['bytes'] and im.sha(raw)==f['sha256']
    assert (STAGE/'goal-status-before.json').read_bytes()==(BASE/'GOAL_STATUS.json').read_bytes()
    path=prev.prev.prev.prev.old.old.prev.a.prev.p.a.v.VCD_PATH
    blob=path.read_bytes();assert im.sha(blob)==im.PINS[str(path.relative_to(BASE))]
    assert old.app_gp(blob)==old.GP and blob[0x248cc4:0x248cc7]==bytes([0,1,0])
    source_path=BASE/'stage84-hevc-native-config-body/run-20261026/native-body-results.json'
    sources=json.loads(source_path.read_text())['cases']
    get=lambda seed:next(c for c in sources if c['seed']==seed and c['source_label']=='selected1_raw5' and c['kind']=='captured')
    out.mkdir();(out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    frames=[];crops=[]
    try:
        for seed in (0xa5,0xc3):
            for flag in (0,0x10):frames.append(frame_case(blob,seed,1,flag))
        for flag in (0,0x10):frames.append(frame_case(blob,0xa5,0,flag))
        for seed in (0xa5,0xc3):
            for height in (1080,1088):crops.append(crop_case(blob,get(seed),height))
    except Exception:
        im.write_json(out/'failed-attempt.json',{'traceback':traceback.format_exc(),
            'completed_frames':len(frames),'completed_crops':len(crops)})
        raise
    j={'status':'PASS_NATIVE_FRAME_CONSTRUCTOR_HEADER_REFERENCE_BOUNDARY_AND_CROP_RECONCILIATION',
        'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source_receipt':{'script_sha256':im.sha(Path(__file__).read_bytes()),'VCD_sha256':im.sha(blob),
            'prior_manifest_sha256':PRIOR_SHA,'stage84_result_sha256':im.sha(source_path.read_bytes())},
        'frame_cases':frames,'crop_cases':crops,'bounded_phases':sum(len(c['events']) for c in frames+crops),
        'scope':'Complete original fresh frame constructor and native header on declared partial owner/raw inputs. '
            'No-update producer returns; update assigns pointer then stops before reference increment. '
            'Independent native geometry/crop fragments reconcile1088-4*2=1080, not SPS, bitstream or hardware proof.',
        'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    im.write_json(out/'frame-crop-results.json',j)
    print(json.dumps({'status':j['status'],'frame_cases':len(frames),'crop_cases':len(crops),
        'bounded_phases':j['bounded_phases'],'output':str(out)}))


if __name__=='__main__':main()
