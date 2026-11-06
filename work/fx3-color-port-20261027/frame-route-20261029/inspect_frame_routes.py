#!/usr/bin/env python3
"""Pinned original MLUT caller gate, resource checker and direct call candidates."""
import hashlib,json,struct,sys
from pathlib import Path
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB
HERE=Path(__file__).resolve().parent
TASK=HERE.parent
sys.path.insert(0,str(TASK/'route-20261028'))
from cp_look_route import image,BASE,PIN
sys.path.insert(0,str(TASK/'scene-binding-20261029'))
from inspect_scene_vector import refs

def main():
    previous=TASK/'scene-binding-20261029';receipt=previous/'final-receipt.json'
    assert hashlib.sha256(receipt.read_bytes()).hexdigest()=='8692416fe7833eff1203ed3dee90c7926a9b7dfe868cee7a3e42edc88e1e26f5'
    manifest=json.loads(receipt.read_text())
    for row in manifest['files']:
        raw=(previous/row['path']).read_bytes();assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256']
    raw=image();md=Cs(CS_ARCH_ARM,CS_MODE_THUMB);dest=HERE/'source-fragments';dest.mkdir(exist_ok=True);fragments=[]
    windows=[(0x8cb454,0x8cb568,'mlut-caller'),(0x8cc1a8,0x8cc1ce,'caller-gate'),(0x8c7bac,0x8c7bda,'resource-mask-checker'),
             (0x8cc316,0x8cc360,'gate-after-submit'),(0x8d024c,0x8d025e,'optional-frame-path'),
             (0x302724,0x3027c6,'resource-request-caller'),(0x8d1308,0x8d1538,'resource-request-helper'),
             (0x300236,0x300242,'original-sync-clear'),(0x8cb266,0x8cb28e,'mlut-callback-registration'),
             (0x8cdf6c,0x8cdf7e,'registration-wrapper'),(0x37b078,0x37b1e0,'stp-allocator-boundary'),
             (0x320438,0x3205a8,'next-image-utility'),(0x3205c4,0x320608,'next-image-utility-wrapper')]
    for lo,hi,label in windows:
        body=raw[lo:hi];path=dest/(label+'.txt');path.write_text('\n'.join(f'{i.address:08x} {i.mnemonic:10} {i.op_str}' for i in md.disasm(body,BASE+lo))+'\n')
        fragments.append(dict(file_offset=hex(lo),bytes=len(body),sha256=hashlib.sha256(body).hexdigest(),label=label,listing=str(path.relative_to(HERE))))
    wanted={0x9d3454,0x9d357e,0x9d41a8,0x9cfbac};calls=[]
    for at in range(0,0x9c0000,2):
        a,z=struct.unpack_from('<HH',raw,at)
        if a&0xf800!=0xf000 or z&0xd000 not in [0xd000,0x9000]:continue
        sign=(a>>10)&1;j1=(z>>13)&1;j2=(z>>11)&1
        value=(sign<<24)|((1^(j1^sign))<<23)|((1^(j2^sign))<<22)|((a&0x3ff)<<12)|((z&0x7ff)<<1)
        if sign:value-=1<<25
        target=BASE+at+4+value
        if target not in wanted:continue
        ins=next(md.disasm(raw[at:at+4],BASE+at,count=1),None)
        if ins is None or ins.mnemonic not in ['bl','b.w'] or int(ins.op_str[1:],0)!=target:continue
        lo=max(0,at-32);hi=at+32
        calls.append(dict(file_offset=hex(at),target=hex(target),opcode=ins.mnemonic,span_file=hex(lo),span_bytes=hi-lo,span_sha256=hashlib.sha256(raw[lo:hi]).hexdigest(),listing=[f'{i.address:08x} {i.mnemonic:10} {i.op_str}' for i in md.disasm(raw[lo:hi],BASE+lo)]))
    pointers=refs(raw,{0x9d3455:'original MLUT-calling function pointer',0x9d357f:'second MLUT-calling function pointer'})
    source_names=[]
    for va in [0xdf3e20,0xdf2829]:
        at=va-BASE;value=raw[at:raw.index(0,at)]
        source_names.append(dict(va=hex(va),value=value.decode(),sha256=hashlib.sha256(value+b'\0').hexdigest()))
    result=dict(cp_sha256=PIN,previous_checkpoint_files_verified=len(manifest['files']),source_fragments=fragments,direct_branch_candidates=calls,callback_pointer_candidates=pointers,diagnostic_source_names=source_names,
                scope='Pinned explicit original Thumb windows and Capstone-confirmed 32-bit direct branch candidates. No claim of complete indirect call coverage, function identity by proximity, real resource state, MAIN pixel routing, native target execution or device access.')
    (HERE/'frame-route-source-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(previous_files_verified=len(manifest['files']),fragments=len(fragments),direct_branch_candidates=len(calls),callback_pointer_candidates=len(pointers))))

if __name__=='__main__':main()
