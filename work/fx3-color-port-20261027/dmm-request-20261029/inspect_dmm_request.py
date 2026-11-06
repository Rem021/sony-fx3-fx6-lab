#!/usr/bin/env python3
"""Pin DmmWrapper request source and separate static reply/cross-image hints."""
import hashlib,json,re,struct,sys
from pathlib import Path
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB
HERE=Path(__file__).resolve().parent
TASK=HERE.parent
sys.path.insert(0,str(HERE))
from dmm_request_guest import image,BASE,PIN,SPANS
PREVIOUS_PIN='4a899628f47fe3ca66c66d0d00fa39637427fd43a14aac57bc781cb665330cb6'
AV_PATH=TASK.parent/'sony-firmware-20261024/stage2/extraction/files/nflasha3/av-cam.bin'
AV_PIN='0cb7e03a59b4ec3d7633664ab0f7a9477892d1aaf442b9db83a7e9a62a49bdaf'

def literal(raw,va,base):
    at=va-base;b=raw[at:raw.index(0,at)+1]
    return dict(va=hex(va),bytes=len(b),text=b.decode().rstrip('\0'),sha256=hashlib.sha256(b).hexdigest())

def main():
    previous=TASK/'dynamic-id-20261029';receipt=previous/'final-receipt.json'
    assert hashlib.sha256(receipt.read_bytes()).hexdigest()==PREVIOUS_PIN
    old=json.loads(receipt.read_text())['files']
    for f in old:
        b=(previous/f['path']).read_bytes();assert len(b)==f['bytes'] and hashlib.sha256(b).hexdigest()==f['sha256'],f['path']
    raw=image();dest=HERE/'source-fragments';dest.mkdir(exist_ok=True);md=Cs(CS_ARCH_ARM,CS_MODE_THUMB);md.skipdata=True
    windows=SPANS+[(0x44d854,0x44d8b2),(0x4d7a84,0x4d7b40)]
    fragments=[]
    for a,z in windows:
        b=raw[a-BASE:z-BASE];p=dest/(f'{a:08x}-{z:08x}.txt')
        p.write_text('\n'.join(f'{i.address:08x} {i.mnemonic:10} {i.op_str}' for i in md.disasm(b,a))+'\n')
        fragments.append(dict(va=hex(a),bytes=z-a,sha256=hashlib.sha256(b).hexdigest(),listing=str(p.relative_to(HERE)),
                              scope='Pinned original static window. Reply and configuration-query windows are not guest completion/response evidence.'))
    names=[literal(raw,va,BASE) for va in [0xd8cda4,0xd8cdd8,0xd8ce0e,0xd8ce4a]]
    for r in names:
        assert r['text'].startswith('AllocNew:')
        at=int(r['va'],16)-BASE;start=raw.rfind(b'\0',0,at)+1
        r['enclosing_literal']=literal(raw,start+BASE,BASE)
        assert r['enclosing_literal']['text']=='[DmmWrapper]'+r['text']
    hints=[literal(raw,va,BASE) for va in [0x4d7b40,0x4dd7f0,0xe1fdc9]]
    assert [r['text'] for r in hints]==['dmm_module_GetConfigData','SaDmmUnitAllocNew','dmm_alloc']
    table=raw[0xff3c74-BASE:0xff3c74-BASE+24];assert struct.unpack_from('<I',table)[0]==0xe1fdc9
    av=AV_PATH.read_bytes();assert hashlib.sha256(av).hexdigest()==AV_PIN
    av_hints=[]
    for off in [0x426622,0x43f693]:
        r=literal(av,off,0);r['file_offset']=r.pop('va');r['scope']='File offset only; AV load VA and queue/provider binding are not inferred.';av_hints.append(r)
    inventories=[]
    for label,b in [('CP',raw),('AV',av)]:
        hits=[m for m in re.finditer(rb'[\x20-\x7e]{5,}',b) if re.search(rb'dmm|AllocNew',m.group(),re.I)]
        inventories.append(dict(image=label,ASCII_DMM_or_AllocNew_strings=len(hits),scope='String inventory/candidates only; not handlers, service identity or image compatibility.'))
    out=dict(cp_sha256=PIN,previous_receipt_sha256=PREVIOUS_PIN,previous_files_verified=len(old),source_fragments=fragments,
             function_identity=dict(entry='0x44d710',classification='DmmWrapper AllocNew client path, inferred from original diagnostic literals and their call sites; not recovered exported symbols.',literals=names),
             original_request_contract=dict(submission_entry='0xa878ca',destination='0x61003c',payload_bytes=216,
                                            fields=[dict(offset='0x0',bytes=2,value='0x20'),dict(offset='0x4',bytes=4,value='0x4af'),
                                                    dict(offset='0xc',bytes=4,value='0x0'),dict(offset='0x14',bytes=2,value='0x55'),dict(offset='0x16',bytes=2,value='0x1')],
                                            original_written_payload_bytes=14,remaining_fixture_fill_bytes=202,
                                            source_reply_ID='Original osal_dynamic_id output, stored by original0xa878d2 in message header at payload-0xc.'),
             static_reply_requirements=dict(executed=False,source='0x44d854..0x44d8b2',
                                            checks=['return from submission is zero','reply u16+2 is zero',
                                                    'reply u16+0 ==0x8020','reply u16+6 ==0x55','reply u32+0xc !=0xffffffff',
                                                    'when request r1==1: reply u16+8 !=0 and reply u32+0x20 !=0'],
                                            scope='Original static acceptance checks only. No reply fields, successful service return or image/extent data supplied.'),
             unbound_candidates=dict(cp_literals=hints,command_reference_window=dict(va='0xff3c74',bytes=24,sha256=hashlib.sha256(table).hexdigest(),words=[hex(v[0]) for v in struct.iter_unpack('<I',table)],
                                                                                   scope='Reference to debug command name, not normal queue registration or receiver proof.'),
                                     av_sha256=AV_PIN,av_file_hints=av_hints,string_inventories=inventories,
                                     scope='Candidates for later receiver/configuration tracing only; no QID0x3c consumer or unit0x4af layout established.'),
             public_search=dict(local_date='2026-10-29',queries=['"DmmWrapper" Sony','"InfraBB_DataFlowInfraWrapper"'],
                                result='No Sony source identified; an unrelated NI instrument DMM wrapper result was excluded.',scope='Not evidence that source/firmware is absent.'),
             scope='Original client message allocation and request fields, with static reply prerequisites kept separate. No real send/receive, complete packet semantic specification, physical image buffers, main recording, whole donor pipeline or modified firmware admission.')
    (HERE/'dmm-request-source-results.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(dict(previous_files_verified=len(old),source_windows=len(fragments),DmmWrapper_literal_pins=len(names),unbound_CP_hints=len(hints),unbound_AV_hints=len(av_hints))))

if __name__=='__main__':main()
