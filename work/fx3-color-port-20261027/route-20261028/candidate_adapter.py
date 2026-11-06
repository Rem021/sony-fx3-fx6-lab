#!/usr/bin/env python3
"""Offline control prototype: explicit new request -> CP base-look 12 -> profile 22.

This is not a camera patch: no code-cave address, linkage, menu or IPC deployment
is established. The Thumb shim executes only at a declared guest address.
"""
import json
import struct
from hashlib import sha256
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB
from cp_look_route import image,BASE,ENTRY,HERE
from ap_cp_message import cp_machine

GUEST_SHIM=0x52000000
# cmp r1,#12; bne delegate; movs r0,#22; bx lr;
# delegate: ldr.w pc,[pc,#0]; .word original_Thumb_entry
SHIM=bytes.fromhex('0c2901d116207047dff800f0')+struct.pack('<I',(BASE+ENTRY)|1)


def extend_message(wire,request_aces_rec709=False):
    result=list(wire)
    if not request_aces_rec709:return result
    if wire[1]==3:
        raise ValueError('Original CP converter overrides base look when shooting_mode=3')
    if wire[3]!=0:
        raise ValueError('Prototype restricted to raw CP color_gamut=0 domain')
    # This is a new wire-domain value, not an existing Select LUT slot number.
    result[0]=12
    return result


def main():
    b=image();candidate,counter=cp_machine(b,GUEST_SHIM,SHIM)
    prior=json.loads((HERE/'ap-cp-message-results.json').read_text())
    preserved=[]
    for old in prior['cp_cases']:
        result=candidate(extend_message(old['wire']),old['previous_color_gamut_fixture'],old['field78_fixture'],old['field7c_fixture'])
        assert result==old
        preserved.append(result['selected_look'])
    new=[];rejected=0
    wires=sorted({tuple(x['wire']) for x in prior['ap_samples']})
    for wire in wires:
        try:extended=extend_message(wire,True)
        except ValueError:rejected+=1;continue
        assert extended[1:]==list(wire[1:]) and extended[0]==12
        result=candidate(extended,1,0,0)
        assert result['adjusted_base_look']==12 and result['selected_look']==22
        new.append(dict(original_wire=list(wire),adapted_wire=extended,selected_look=22))
    assert len(preserved)==512 and new and rejected
    # Explicitly cover that this does not steal existing user LUT model index 12.
    assert all(x['wire'][0]<=11 for x in prior['ap_samples'])
    md=Cs(CS_ARCH_ARM,CS_MODE_THUMB)
    listing='\n'.join(f'{i.address:08x}: {i.mnemonic} {i.op_str}' for i in md.disasm(SHIM[:12],GUEST_SHIM))
    (HERE/'candidate-selector-thumb.bin').write_bytes(SHIM)
    (HERE/'candidate-selector-thumb.txt').write_text(listing+f'\n.word 0x{(BASE+ENTRY)|1:08x}\n')
    result=dict(status='PASS_OFFLINE_NEW_MODE_ADAPTER',shim_guest_address=hex(GUEST_SHIM),
                shim_bytes=SHIM.hex(),shim_sha256=sha256(SHIM).hexdigest(),
                unchanged_existing_CP_message_cases=len(preserved),new_cases=new,
                rejected_unique_message_shapes=rejected,instructions=counter[0],
                limits=['No camera firmware changed. Guest shim address is not an available camera code cave.',
                        'No menu property, message admission, IPC or normal pipeline binding is deployed.',
                        'Input pixel domain, live MAIN/monitor routing and complete VENICE ISP remain unverified.',
                        'New request is an explicit adapter option; CP base-look 12 is not Select LUT model index 12.'])
    (HERE/'candidate-adapter-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result['status'],'existing preserved',len(preserved),'new shapes',len(new),'rejected',rejected)
    print(listing)


if __name__=='__main__':main()
