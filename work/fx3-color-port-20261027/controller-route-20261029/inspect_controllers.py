#!/usr/bin/env python3
"""Pin original output-wrapper RTTI, pointer producers and NRV acquisition source."""
import hashlib,json,struct,sys
from pathlib import Path
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB
HERE=Path(__file__).resolve().parent
TASK=HERE.parent
sys.path.insert(0,str(HERE))
from controller_guest import image,BASE,PIN,SPANS
from nrv_acquire_guest import SPANS as NRV_SPANS
PREVIOUS_PIN='e28d5ae72a65d7e71f34a026569e914900ed4228edb003659228bea03ec453d4'

def main():
    prev=TASK/'image-lifecycle-20261029';receipt=prev/'final-receipt.json'
    assert hashlib.sha256(receipt.read_bytes()).hexdigest()==PREVIOUS_PIN
    manifest=json.loads(receipt.read_text())
    for f in manifest['files']:
        b=(prev/f['path']).read_bytes();assert len(b)==f['bytes'] and hashlib.sha256(b).hexdigest()==f['sha256'],f['path']
    raw=image();md=Cs(CS_ARCH_ARM,CS_MODE_THUMB);md.skipdata=True;dest=HERE/'source-fragments';dest.mkdir(exist_ok=True)
    spans=SPANS+NRV_SPANS+[(0x4ec038,0x4ec0ec),(0x40a55a,0x40a58c),(0x40575a,0x4057e2),(0x40423a,0x404252),(0x4044be,0x4044d8),
                         (0x69e746,0x69e782),(0x23db58,0x23dcbc)]
    fragments=[]
    for a,z in spans:
        b=raw[a-BASE:z-BASE];path=dest/(hex(a)[2:]+'.txt')
        path.write_text('\n'.join(f'{i.address:08x} {i.mnemonic:10} {i.op_str}' for i in md.disasm(b,a))+'\n')
        fragments.append(dict(va=hex(a),bytes=z-a,sha256=hashlib.sha256(b).hexdigest(),listing=str(path.relative_to(HERE)),
                              listing_scope='Static source window, may contain embedded diagnostic switch data. Actual instruction execution is established separately by bounded guests.'))
    rtti=[]
    for va,name,base in [(0xbadc28,'N6Camera7CamCore14CoreControllerE',None),(0xbaddc8,'N6Camera7CamCore12EEControllerE',0xbadc28),(0xbae48c,'N6Camera7CamCore17SplitEEControllerE',0xbaddc8)]:
        n=8 if base is None else 12;b=raw[va-BASE:va-BASE+n];words=list(struct.unpack('<'+'I'*(n//4),b))
        p=words[1];at=p-BASE;string=raw[at:raw.index(0,at)+1];assert string.decode().rstrip('\0')==name
        if base is not None:assert words[2]==base
        rtti.append(dict(typeinfo_va=hex(va),bytes=n,sha256=hashlib.sha256(b).hexdigest(),words=[hex(v) for v in words],
                         name_va=hex(p),mangled_name=name,name_bytes=len(string),name_sha256=hashlib.sha256(string).hexdigest(),
                         base_typeinfo=None if base is None else hex(base)))
    selection=json.loads((TASK/'binding-20261028/resource-binding-results.json').read_text());maps=[]
    for row in selection['selector_cases']:
        if row['context'] in [1,5,7] and row['kind']==3:
            ids=[v for v in row['resource_ids'] if v!=0xfe]
            maps.append(dict(context=row['context'],kind=3,resource_ids=ids,names=[selection['resource_names'][i] for i in ids],origin='Previously sealed original-selector result; initial selection input is declared, not a normal scene readback.'))
    out=dict(cp_sha256=PIN,previous_receipt_sha256=PREVIOUS_PIN,previous_files_verified=len(manifest['files']),source_fragments=fragments,rtti=rtti,
             kind3_context_maps=maps,
             normal_allocation_gaps=dict(object_8e4_original_producer='Kind3 broker output at original caller0x40a55a..0x40a58c; not produced to completion in this stage.',
                                         original_nrv_entry='0x4056f4',first_buffer_descriptor='0x117adf0',first_buffer_key='0x4af',
                                         original_controller_open_after_two_buffers='0x69e746',original_open_not_executed=True,
                                         static_registration_chain='0x69e746 -> 0x23db58 -> concrete creation branches -> 0x69e4f0; static only, no construction success supplied'),
             classification=dict(target='0x4ec038',interpretation='Dynamic-cast style runtime from CoreController to EEController/SplitEEController.',
                                 basis='Original arguments match sub/src/dst/src2dst_offset; body reads vptr[-2/-1] and dispatches RTTI. No complete execution or symbol-name recovery claimed.'),
             public_references=[dict(url='https://itanium-cxx-abi.github.io/cxx-abi/abi.html#rtti-dynamic_cast',retrieved_local_date='2026-10-29',
                                     relevance='Generic __dynamic_cast argument contract and RTTI layout; not Sony platform conformance or controller routing proof.'),
                                dict(url='https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000888936.html',retrieved_local_date='2026-10-29',
                                     relevance='Display LUT preview is documented; the page does not identify private EEController classes or prove main recording routing.')],
             scope='Static source, typeinfo/name pins and allocation dependency, without equating type names with a physical MAIN/monitor route, CMOS RAW path, full donor ISP or modified firmware acceptance.')
    (HERE/'controller-source-results.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(dict(previous_files_verified=len(manifest['files']),source_windows=len(fragments),rtti_records=len(rtti),kind3_context_maps=len(maps))))

if __name__=='__main__':main()
