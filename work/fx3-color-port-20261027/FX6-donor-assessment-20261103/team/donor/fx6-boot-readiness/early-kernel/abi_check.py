#!/usr/bin/env python3
"""Static FX3 CPIO module vs FX6 kernel export/vermagic/CRC precheck."""
import hashlib
import json
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[6]
sys.path.insert(0,str(HERE.parent))
from elf64 import ELF64
from closure import main as closure_check

FX6_IMAGE=HERE.parents[1]/'fat-files/nflasha3/vmlinux.bin'
FX6_SYMBOLS=HERE.parents[1]/'kernel-provider-binding/fx6-kernel-symbol-catalog.json'
FX6_EXPORTS=HERE.parents[1]/'kernel-provider-binding/export-crosscheck.json'
FX3_SYMBOLS=ROOT/'work/sony-firmware-20261024/stage146-original-kernel-symbol-and-vendor-route/work/kernel-symbol-catalog.json'
FX3_EXPORTS=ROOT/'work/sony-firmware-20261024/stage146-original-kernel-symbol-and-vendor-route/run-symbol-verification/export-crosscheck.json'
FX3_IMAGE=ROOT/'work/sony-firmware-20261024/stage47-runtime-provider-binding/official-files/nflasha3/vmlinux.bin'
PINS={
 'fx6_image':(FX6_IMAGE,'bc4925e701ae363c797f22ef28f29dc48fd17af7f25a3f64d7d0824312c0dab9'),
 'fx6_symbols':(FX6_SYMBOLS,'f81602bb6d754eccdd7b2c17af371ee2e03cc01fad86dff3552936bd1f9a6166'),
 'fx6_exports':(FX6_EXPORTS,'e9cd948f230d66b6e1aca689b5f96bf94e9ad98d91f10ee9bf72a018d4b133ad'),
 'fx3_image':(FX3_IMAGE,'da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c'),
 'fx3_symbols':(FX3_SYMBOLS,'b37c6b7d4315f65234cd6b64c3be4a3d7c6e0d2cca66204e27cb5c575000a51e'),
 'fx3_exports':(FX3_EXPORTS,'c3e33ad1d45276727dc7ee9c287bdbd3e440e32b1724816c74ba897641aae6f6'),
}
CRITICAL=['udif_driver_register','pcidma_transfer_async','__udif_request_irq','arch_phys_to_noncache']


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()


def main():
    for key,(path,pin) in PINS.items():
        if sha(path)!=pin:raise ValueError('pinned source changed '+key)
    c=closure_check()
    saved=json.loads((HERE/'liro-closure.json').read_text())
    if c!=saved:raise ValueError('closure receipt stale')
    sym3={v['name']:v for v in json.loads(FX3_SYMBOLS.read_text())}
    sym6={v['name']:v for v in json.loads(FX6_SYMBOLS.read_text())}
    exp3={v['name']:v for v in json.loads(FX3_EXPORTS.read_text())}
    exp6={v['name']:v for v in json.loads(FX6_EXPORTS.read_text())}
    image3=FX3_IMAGE.read_bytes();image6=FX6_IMAGE.read_bytes()
    vermagic={}
    for model,syms,image in [('fx3',sym3,image3),('fx6',sym6,image6)]:
        off=syms['vermagic']['file_offset']
        raw=image[off:off+128].split(b'\0',1)[0]
        vermagic[model]={'file_offset':off,'text':raw.decode('ascii'),'sha256':hashlib.sha256(raw+b'\0').hexdigest()}
    modules={}
    for name,details in c['closure_modules'].items():
        e=ELF64(Path(details['path']))
        attrs=[v.decode('ascii','replace') for v in e.section_bytes('.modinfo').split(b'\0') if v.startswith(b'vermagic=')]
        if len(attrs)!=1:raise ValueError('module vermagic missing '+name)
        modules[name]={'sha256':details['sha256'],'vermagic':attrs[0].split('=',1)[1],'has___versions':('__versions' in e.byname),'has___kcrctab':any('__kcrctab' in s['name'] for s in e.sections)}
    if any(v['vermagic']!=vermagic['fx6']['text'] for v in modules.values()):raise ValueError('module vermagic mismatch')
    crc_spans={}
    for model,sym in [('fx3',sym3),('fx6',sym6)]:
        crc_spans[model]={}
        for suffix in ('','_gpl','_gpl_future','_unused','_unused_gpl'):
            start=sym['__start___kcrctab'+suffix]['address'];end=sym['__stop___kcrctab'+suffix]['address']
            crc_spans[model][suffix or 'ordinary']={'start':hex(start),'end':hex(end),'bytes':end-start}
    imported=sorted({v['symbol'] for v in c['kernel_edges']})
    missing=[n for n in imported if n not in exp6]
    if missing:raise ValueError('FX6 kernel missing imported names: '+repr(missing))
    changed=[n for n in imported if int(exp6[n]['address'],0)!=exp3[n]['address']]
    critical={}
    for name in CRITICAL:
        if name not in exp3 or name not in exp6:raise ValueError('critical export missing '+name)
        one={}
        for model,sym,image,exp in [('fx3',sym3,image3,exp3),('fx6',sym6,image6,exp6)]:
            off=sym[name]['file_offset'];body=image[off:off+32]
            one[model]={'symbol_file_offset':off,'address':hex(int(exp[name]['address'],0) if isinstance(exp[name]['address'],str) else exp[name]['address']),'first32_sha256':hashlib.sha256(body).hexdigest(),'first32_hex':body.hex()}
        critical[name]=one
    return {'status':'PASS_STATIC_ABI_PRECHECK_ONLY','sources':{k:{'path':str(v[0]),'sha256':v[1]} for k,v in PINS.items()},'fx3_modules_in_fixed_cpio':modules,'module_count':len(modules),'vermagic':vermagic,'kernel_crc_table_spans':crc_spans,'module___versions_present_count':sum(v['has___versions'] for v in modules.values()),'unique_original_kernel_imports':len(imported),'fx6_export_name_present_count':len(imported)-len(missing),'fx6_missing_export_names':missing,'changed_export_target_address_count':len(changed),'changed_export_target_address_names':changed,'critical_export_code_prefixes':critical,'CONFIG_MODVERSIONS_exact_build_config_recovered':False,'ABI_layout_or_behavior_compatible_proven':False,'module_load_on_FX6_kernel_tested':False}


if __name__=='__main__':
    output=main();(HERE/'fx3-modules-vs-fx6-kernel.json').write_text(json.dumps(output,indent=2,ensure_ascii=False)+'\n');print(json.dumps({'status':output['status'],'modules':output['module_count'],'unique_kernel_imports':output['unique_original_kernel_imports'],'fx6_export_names_present':output['fx6_export_name_present_count'],'changed_export_addresses':output['changed_export_target_address_count'],'crc_sections_in_modules':output['module___versions_present_count']},indent=2))
