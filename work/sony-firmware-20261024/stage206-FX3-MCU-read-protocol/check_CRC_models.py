"""Host semantic models of two pinned software CRC forms; no native/guest firmware."""
from pathlib import Path
from hashlib import sha256
import json, struct
H=Path(__file__).resolve().parent
def official_bit_form(crc, byte):
    for _ in range(8):
        outgoing=crc>>15
        crc=(crc&0x7fff)<<1
        if outgoing!=(byte>>7): crc^=0x1021
        byte=(byte&0x7f)<<1
    return crc
def reference_xor_form(crc, byte):
    crc^=byte<<8
    for _ in range(8):
        crc=(crc<<1)^0x1021 if crc&0x8000 else crc<<1
    return crc&0xffff
checks=0
for state in [0,0xffff]+[1<<i for i in range(16)]:
    for byte in range(256):
        assert official_bit_form(state,byte)==reference_xor_form(state,byte)
        checks+=1
def crc(data, step):
    state=0xffff
    for byte in data: state=step(state,byte)
    return state
payloads=[bytes(126),bytes([255])*126,bytes(range(126))]
for address,length in [(0x200026fc,4),(0x2000003c,3)]:
    frame=bytearray(126)
    frame[0]=0x16
    struct.pack_into('<I',frame,1,address)
    frame[5]=length
    assert frame[5]&0x80==0 and 1<=frame[5]<=120
    payloads.append(bytes(frame))
vectors=[]
for data in payloads:
    left=crc(data,official_bit_form);right=crc(data,reference_xor_form)
    assert left==right
    vectors.append(dict(input_bytes=len(data),input_sha256=sha256(data).hexdigest(),CRC=left,
        sealed_frame_sha256=sha256(data+struct.pack('<H',left)).hexdigest()))
result=dict(status='PASS_HOST_SOFTWARE_SEMANTIC_MODELS',byte_state_cases=checks,
    input_states='0,FFFF and16 individual bit basis states',input_bytes_each_case='all256',
    full126B_vectors=vectors,
    model_source_relation='models transcribe pinned official AP ARM64 bit recurrence and public C xor recurrence; not execution of either program',
    proves_MCU_hardware_CRC_or_transport=False,strict_reply_freshness_proven=False,
    actual_device_packets_sent=0,original_or_guest_execution=False,root_or_device_operations=0)
(H/'CRC-semantic-model-results.json').open('x').write(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(byte_state_cases=checks,full_frame_vectors=len(vectors),hardware_CRC_proven=False,device_operations=0)))
