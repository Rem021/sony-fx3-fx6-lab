#!/usr/bin/env python3
"""Original consumers of capture base-look: monitoring metadata, not pixels."""
import json,itertools,struct
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn import arm_const as R
from ec_mode_guest import image,BASE,PIN,STACK,DATA,STOP,setup,prepare,preserved,HERE


def main():
    b=image();u=setup(b);count=[0]
    spans=[(0x1cfbf4,0x1cfc5c),(0x66b256,0x66b2b4)]
    def code(u,pc,size,unused):
        if pc==STOP:u.emu_stop();return
        assert any(BASE+a<=pc<BASE+z for a,z in spans),hex(pc)
        count[0]+=1
    def write(u,access,address,size,value,unused):
        assert STACK<=address and address+size<=STACK+0x10000 or address==DATA+0x100 and size==4,hex(address)
    u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
    def call(entry,args):
        u.mem_write(DATA,b'\xa7'*0x200);u.mem_write(STACK+0xf000,struct.pack('<I',DATA+0x100))
        prepare(u)
        for i,x in enumerate(args):u.reg_write(getattr(R,f'UC_ARM_REG_R{i}'),x)
        u.emu_start((BASE+entry)|1,STOP+4,count=100)
        assert u.reg_read(R.UC_ARM_REG_PC)==STOP;preserved(u)
        raw=bytes(u.mem_read(DATA,0x200));assert raw[:0x100]==b'\xa7'*0x100 and raw[0x104:]==b'\xa7'*0xfc
        return struct.unpack_from('<I',raw,0x100)[0]
    rows=[]
    for pp,shooting,base,gamut in itertools.product([0,22,31,35,36],range(4),list(range(14))+[255],range(2)):
        args=[pp,shooting,base,gamut]
        rows.append(args+[call(spans[0][0],args),call(spans[1][0],args)])
    by={tuple(r[:4]):r[4:] for r in rows}
    assert by[(31,1,0,0)]==[83,83] and by[(31,1,0,1)]==[84,84]
    for shooting,gamut in itertools.product([1,2],range(2)):
        assert by[(31,shooting,12,gamut)]==[100,4]
        assert by[(31,shooting,13,gamut)]==[100,4]
        assert by[(31,shooting,255,gamut)]==[100,4]
    labels=[]
    for off,name in [(0xca8f73,'MonitoringBaseCurveMeta'),(0xca8fa6,'MonitoringCharacteristicsMeta')]:
        assert b[off:off+len(name)]==name.encode();labels.append(dict(file=hex(off),name=name))
    result=dict(status='PASS_ORIGINAL_METADATA_CONSUMERS_NEW_VALUE_FALLBACK',cp_sha256=PIN,
                columns=['pp_mode_raw','shooting_mode_raw','base_look_raw','color_gamut_raw',
                         'MonitoringBaseCurveMeta_raw','MonitoringCharacteristicsMeta_raw'],
                cases=rows,original_instructions=count[0],source_labels=labels,
                dataflow=[{'source_capture_field':'0x794','caller_load':'0x1cdbca','call':'0x1cdbde',
                           'function':'0x1cfbf4','output_field':'0x234','label_binding_log':'0x1ce158'},
                          {'source_capture_field':'0x794','caller_load':'0x1cdc34','call':'0x1cdc48',
                           'function':'0x66b256','output_field':'0x23c','label_binding_log':'0x1ce1a4'}],
                new_value_probe={'raw_inputs':[31,1,12,0],'raw_outputs':by[(31,1,12,0)],
                                 'meaning':'Both original consumers take their unhandled-base fallback; the V2 selector/gate prototype does not supply dedicated metadata handling.'},
                scope='Field/object identity is supported by caller loads, output stores and named metadata logs. These consumers build metadata; they are not a pixel/LUT application proof. Raw numeric outputs are not assigned new color-space meanings.')
    (HERE/'metadata-consumer-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result['status'],'paired cases',len(rows),'new base 12 outputs',by[(31,1,12,0)])


if __name__=='__main__':main()
