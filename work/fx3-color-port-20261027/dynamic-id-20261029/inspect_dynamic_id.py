#!/usr/bin/env python3
"""Pin dynamic-ID source, literal identity, initial banks and predecessor seal."""
import hashlib,json,struct,sys
from pathlib import Path
from capstone import Cs,CS_ARCH_ARM,CS_MODE_ARM,CS_MODE_THUMB
HERE=Path(__file__).resolve().parent
TASK=HERE.parent
sys.path.insert(0,str(HERE))
from dynamic_id_guest import image,BASE,PIN,THUMB,ARM
PREVIOUS_PIN='9d224c3b33220bb20930e89d9579f161ad7a76cbf5d4586402688d1e0079def9'

def main():
    prev=TASK/'controller-route-20261029';receipt=prev/'final-receipt.json'
    assert hashlib.sha256(receipt.read_bytes()).hexdigest()==PREVIOUS_PIN
    old=json.loads(receipt.read_text())['files']
    for f in old:
        b=(prev/f['path']).read_bytes();assert len(b)==f['bytes'] and hashlib.sha256(b).hexdigest()==f['sha256'],f['path']
    raw=image();dest=HERE/'source-fragments';dest.mkdir(exist_ok=True);fragments=[]
    spans=[(a,z,'Thumb') for a,z in THUMB]+[(a,z,'ARM') for a,z in ARM]+[
        (0x52c474,0x52c4a8,'ARM'),(0x53fea0,0x53ffe0,'ARM'),(0x53ffec,0x540124,'ARM'),(0x49e0ac,0x49e0e4,'Thumb')]
    for a,z,mode in spans:
        b=raw[a-BASE:z-BASE];md=Cs(CS_ARCH_ARM,CS_MODE_ARM if mode=='ARM' else CS_MODE_THUMB);md.skipdata=True
        path=dest/(f'{a:08x}-{z:08x}-{mode}.txt')
        path.write_text('\n'.join(f'{i.address:08x} {i.mnemonic:10} {i.op_str}' for i in md.disasm(b,a))+'\n')
        fragments.append(dict(va=hex(a),bytes=z-a,mode=mode,sha256=hashlib.sha256(b).hexdigest(),listing=str(path.relative_to(HERE)),
                              scope='Pinned original window; listings can include assert opcodes/literals. Executed bounds and declared adapters are separate evidence.'))
    literals=[]
    for va,text in [(0x4a07ec,'osal_dynamic_id'),(0x4a07c4,'free_dynamic_msgq_id'),
                    (0xe12c11,'**UIPC ERROR** %s: Parameter error OSAL_ID_TYPE[%x]\n'),
                    (0xe12d0c,'**UIPC ERROR** %s: double free detected. 0x%08x\n')]:
        b=(text+'\0').encode();assert raw[va-BASE:va-BASE+len(b)]==b
        literals.append(dict(va=hex(va),bytes=len(b),text=text,sha256=hashlib.sha256(b).hexdigest()))
    assert 0x4a035c+4+0x48c==0x4a07ec
    banks=[]
    for va,expected in [(0xee5540,[0,0,0x6000,0x2000,0x1921680]),(0xee5580,[0,0,0x7000,0x1000,0x1921c80]),(0xee55c0,[0,0,0x6000,0x1000,0x1921a80])]:
        b=raw[va-BASE:va-BASE+20];ws=list(struct.unpack('<5I',b));assert ws==expected
        banks.append(dict(va=hex(va),bytes=20,words=[hex(v) for v in ws],sha256=hashlib.sha256(b).hexdigest(),scope='Initial file bytes, not live lock/bitmap/runtime state.'))
    out=dict(cp_sha256=PIN,previous_receipt_sha256=PREVIOUS_PIN,previous_files_verified=len(old),source_fragments=fragments,literals=literals,initial_ID_banks=banks,
             function_identity=dict(entry='0x4a032c',literal='0x4a07ec',logger_name_argument_PC='0x4a035c',identity='osal_dynamic_id',
                                    implication='Software dynamic OSAL IDs and queue-context metadata; not a sensor pixel lookup or physical cache-chip interface.'),
             allocation_dependency=dict(metadata_initializer='0xa87206',fixed_metadata_block_bytes=64,metadata_pop='0x49eaf8',
                                        sparse_context_lookup_or_create='0xa87248',lock='0xa8708a',unlock='0xa870e6',
                                        real_context_query='0x52c474',first_MP_affinity_read='0x52c488',
                                        next_message_buffer_allocator='0x49f80c',observed_original_request_QID='0x61003c',observed_original_request_payload_bytes='0xd8'),
             public_search=dict(local_date='2026-10-29',queries=['"osal_dynamic_id"','"UIPC" "Sony" "alloc_msg"'],result='Empty web search results',
                                scope='No public match found in these two queries only; not proof source is absent or firmware cannot exist. All private-path conclusions here are from pinned original bytes.'),
             public_register_reference=dict(url='https://arm-software.github.io/CMSIS_5/Core_A/html/group__CMSIS__MPIDR.html',
                                            source_url='https://raw.githubusercontent.com/ARM-software/CMSIS_5/develop/CMSIS/Core_A/Include/cmsis_cp15.h',
                                            retrieved_local_date='2026-10-29',relevance='Arm CMSIS identifies CP15(15,0,c0,c0,5) as MPIDR. This identifies the strict stop instruction only; no FX3 register value or current CPU/runtime state is established.'),
             scope='Static function identity and dependency with independent RAM guest receipts. No source CMOS, physical buffering, service response, complete donor chain or modified firmware admission.')
    (HERE/'dynamic-id-source-results.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(dict(previous_files_verified=len(old),source_windows=len(fragments),literal_pins=len(literals),bank_pins=len(banks))))

if __name__=='__main__':main()
