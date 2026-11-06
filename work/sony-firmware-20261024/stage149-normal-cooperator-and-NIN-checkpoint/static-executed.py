"""Pinned original images and bounded static normal-cooperator audit, no device API."""
from pathlib import Path
from hashlib import sha256
import importlib.util
import json
import struct
from elftools.dwarf.callframe import FDE

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
ROOT=BASE.parents[1]
OBJ_SHA='c4681d209a7fe2ed63752be3b0be89ab7b7ce400679c00068c8c6e47d39f83ae'
CORE_SHA='a2907111c4a22314dcb12c25889e0e3142764c6a4a910a746e43908f76e7c410'
OBJ_ENTRIES=[0x57fec,0xe9ed8,0xe9ef8,0xe9f18,0xe9f24,0xe9f30,0xe9f34,
             0xea128,0xea660,0xea6b0,0xeb900,0xeb794,0xec570,0xec5bc,0xec3f4]
CORE_NAMES=['NinThread','_Z9CmdDecodePtPh','_Z9SerializePFiPhmEPvm','_Z5xxhopPhS_',
            '_Z6xxstepPhS_i','_Z6xxjumpPhS_','_Z6xxkickPhS_S_Pm',
            'SEN_SSL_GenerateDigestData','SEN_SSL_GenerateRandomData']


def images():
    prior=BASE/'stage148-initial-MSC-handler-inventory';raw=(prior/'final-receipt.json').read_bytes()
    assert sha256(raw).hexdigest()=='3e59ddb2f6b31e8164921e6857e82b666a9a7a56c17337139fe31969769649e1'
    original=prior/'work/originals/libObj.so'
    rec=next(x for x in json.loads(raw)['files'] if x['path']==original.relative_to(ROOT).as_posix())
    assert sha256(original.read_bytes()).hexdigest()==rec['sha256']==OBJ_SHA
    reader_dir=BASE/'stage134-backup-reader-scope-and-service-extension'
    raw=(reader_dir/'final-receipt.json').read_bytes()
    assert sha256(raw).hexdigest()=='5ece0e5dea69b1c88e812ae42e46a07abf95316a2a6f02c34a5784b7ff6eec1d'
    source=reader_dir/'audit_readers.py';pin=next(x for x in json.loads(raw)['files'] if x['path']==source.relative_to(ROOT).as_posix())
    assert sha256(source.read_bytes()).hexdigest()==pin['sha256']
    spec=importlib.util.spec_from_file_location('fixed_nin_cooperator_image',source)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    core=module.Image('libsencore.so',CORE_SHA);module.LIB=original.parent;obj=module.Image('libObj.so',OBJ_SHA)
    return obj,core


def spans(image,entries):
    frames={x['initial_location']:x['address_range'] for x in image.elf.get_dwarf_info().EH_CFI_entries() if isinstance(x,FDE)}
    return [{'VA':hex(a),'bytes':frames[a],'sha256':sha256(image.read(a,frames[a])).hexdigest(),
             'boundary_source':'original .eh_frame FDE','instructions':image.instructions(a,frames[a])} for a in entries]


def main():
    obj,core=images();of=spans(obj,OBJ_ENTRIES)
    cf=[core.function(n) for n in CORE_NAMES]+spans(core,[0x1590c,0x159cc])
    ins={int(i['pc'],16):i for f in of for i in f['instructions']}
    expected={0x58004:'add x19, x1, #0x108',0x58008:'add x0, x0, #0x10',
              0x5800c:'str x0, [x1, #0x108]',0x58034:'stp xzr, x0, [x19, #0x40]',
              0xe9f18:'adrp x0, #0xe9000',0xe9f1c:'add x0, x0, #0xed8',
              0xe9f28:'add x0, x0, #0xef8',0xe9f30:'ret ',0xe9f34:'mov w0, #0',
              0xe9edc:'ldr x2, [x2, #0x100]',0xe9ee0:'ldr x3, [x2]',0xe9ef4:'br x3',
              0xe9f00:'ldr x3, [x2, #8]',0xe9f14:'br x3',
              0xea6c0:'strb wzr, [x0, #0x50]',0xea6d0:'mov w1, #2',
              0xea6d8:'str w1, [x0]',0xea6e8:'bl #0xea660'}
    for pc,asm in expected.items():assert ins[pc]['asm']==asm,(hex(pc),ins[pc])
    assert ins[0xea67c]['PLT_symbol']=='_ZN3MWF8RsrcAcsr7AcquireEPNS_6ObjMsgENS0_8AcqAct_tE'
    reloc={r['r_offset']:r for r in obj.elf.get_section_by_name('.rela.dyn').iter_relocations()}
    expected_rel={0x261d48:0x252330,0x262c38:0x2ce0b0,0x262f58:0x2ce0ac,
        0x252300:0x1dbdb8,0x252310:0x1dbdc8,0x252320:0x2522f8,0x252338:0x252308,
        0x252340:0xe9fd4,0x252348:0xea008,0x252350:0xe9f18,0x252358:0xe9f24,
        0x252360:0xe9f30,0x252368:0xea6b0,0x252370:0xe9f34}
    for off,addend in expected_rel.items():
        r=reloc[off];assert r['r_info_type']==1027 and r['r_info_sym']==0 and r['r_addend']==addend
    assert 0x57fec in [a for a, in struct.iter_unpack('<Q',obj.elf.get_section_by_name('.init_array').data())]
    cin={int(i['pc'],16):i for f in cf for i in f['instructions']}
    assert cin[0xbf20]['asm']=='mov w1, w19' and cin[0xbf24]['asm']=='ldr x2, [x0, #0x28]'
    assert cin[0xbf2c]['asm']=='blr x2'
    assert cin[0xbf64]['asm']=='cmn w19, #1' and cin[0xbf68]['asm']=='b.eq #0xbc60'
    report={'status':'ORIGINAL_NORMAL_COOPERATOR_CONSTRUCTOR_VTABLE_IO_AND_RESULT_IGNORING_STATIC_ROUTE',
        'object_SHA256':OBJ_SHA,'core_SHA256':CORE_SHA,'object_functions':of,'core_functions':cf,
        'relative_relocations':{hex(a):hex(v) for a,v in expected_rel.items()},
        'normal_cooperator':{'RTTI_name':'N6Senser8SenUsbIfE','base_RTTI':'13NinCooperator',
            'object_VA':'0x2ce108','constructor':'0x57fec','vtable_address_point':'0x252340',
            'receive_getter':'0xe9f18','send_getter':'0xe9f24','receive_wrapper':'0xe9ed8','send_wrapper':'0xe9ef8',
            'callback_saved_transport_table_global':'0x2ce100','register_hasp_method_is_ret':True,
            'onComplete_ignores_incoming_result_and_requests_resource':True},
        'NinThread_callback_precedes_failed_round_loop_check':True,
        'physical_MSC_mapping_or_thread_completion_or_no_persistent_side_effects_proven':False,
        'new_host_USB_camera_driver_or_Windows_operations':0,'original_code_executed':False}
    with (HERE/'normal-cooperator-static.json').open('x') as f:json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
    (HERE/'static-executed.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps({'status':report['status'],'object_functions':len(of),'core_functions':len(cf),
        'normal_onComplete_ignores_result_static':True,'actual_MSC_or_thread_completion_proven':False}))


if __name__=='__main__':main()
