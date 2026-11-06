#!/usr/bin/env python3
"""Compose the selector prototype with the original EC guard's one-value extension."""
from hashlib import sha256
import json
import struct
from cp_look_route import image,BASE,HERE,branch_target
from ap_cp_message import cp_machine
from candidate_adapter import SHIM,GUEST_SHIM,extend_message
from capture_parameter_gate import machine as ec_machine,ENTRY as EC_ENTRY,PATCH


def main():
    b=image();selector,_=cp_machine(b,GUEST_SHIM,SHIM);ec,_=ec_machine(b,True)
    inputs=json.loads((HERE/'candidate-adapter-results.json').read_text())['new_cases']
    cases=[]
    for request in inputs:
        wire=extend_message(request['original_wire'],True)
        cp=selector(wire,1,0,0)
        fields=cp['cp_fields']
        ec_result=ec(fields['base_look'],fields['shooting_mode'],fields['color_gamut'])
        assert cp['selected_look']==22 and ec_result['output_fields'][0]==12 and ec_result['invalid_value_logs']==0
        cases.append(dict(original_wire=request['original_wire'],adapted_wire=wire,
                          selected_CP_profile=22,EC_base_look=ec_result['output_fields'][0]))
    assert len(cases)==30
    mask=0x32207;accepted=[i for i in range(18) if mask&(1<<i)]
    result=dict(status='PASS_OFFLINE_SELECTOR_AND_EC_PARAMETER_ADAPTER_V2',cases=cases,
                existing_behavior_evidence={'CP_message_cases':512,'EC_byte_inputs_unchanged_except_new_12':255},
                changes=[{'kind':'new Thumb wrapper','guest_address':hex(GUEST_SHIM),'bytes':SHIM.hex(),
                          'existing_function_unchanged':hex(BASE+0x3266ec)},
                         {'kind':'EC guard immediate','file_offset':hex(PATCH),'from':'0c29','to':'0d29',
                          'source_CP_sha256':sha256(b).hexdigest(),'applied_only_in_guest':True}],
                observed_EC_caller_gate={'call_file':'0x1c36d0','input_type_byte':'output object +0x8',
                                        'maximum_type':17,'mask':hex(mask),'accepted_type_IDs':accepted,
                                        'domain':'Camera::EC capture/exposure control; not an encoder identification',
                                        'MAIN_proxy_meanings':'not yet mapped'},
                remaining=['Menu/property integration and earlier IPC admission not implemented.',
                           'EC-type IDs and downstream field +0x794 consumer not mapped to actual MAIN/proxy/monitor output.',
                           'Three CP descriptor values reside in runtime RAM; no real runtime snapshot.',
                           'No deployment placement for the wrapper, no repack, signature or camera test.',
                           'This exposes an existing ACES look; it does not recreate sensor RAW/AWB/noise processing.'])
    (HERE/'candidate-adapter-v2-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result['status'],'new message shapes',len(cases),'EC type IDs',accepted)


if __name__=='__main__':main()
