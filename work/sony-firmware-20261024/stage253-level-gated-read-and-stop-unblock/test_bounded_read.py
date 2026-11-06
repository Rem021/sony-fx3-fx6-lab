"""CPU wire guards, including the original command's reset branch exclusion."""
from pathlib import Path
from dataclasses import asdict
import json
import bounded_hasp_read as C
H=Path(__file__).resolve().parent
request=C.fixed_request(1)
assert len(request)==17 and request.hex()=='05000000100001000000000000001f0000'
C.validate_fixed_request(request,1)
bad=[]
for at,value in [(0,6),(4,0x40),(6,2),(10,1),(12,1),(14,0xf1),(16,0x80)]:
    b=bytearray(request);b[at]=value;bad.append(bytes(b))
bad += [request[:-1],request+b'\0']
for b in bad:
    try:C.validate_fixed_request(b,1)
    except C.Rejected:pass
    else:raise AssertionError('mutated/reset request accepted')
payload=b'PRIVATE_FIXTURE_ONLY'.ljust(88,b'X')
reply=C.HEADER.pack(88,0x10,1,0,0,0,1)+payload
out=C.decode_fixed_reply(reply,1,b'K'*32)
assert out.payload_bytes==88 and not out.authentication_verified and not out.thread_exit_verified
assert 'PRIVATE_FIXTURE_ONLY' not in json.dumps(asdict(out)) and not hasattr(out,'payload')
bad_replies=[reply[:-1],reply+b'X',C.HEADER.pack(89,0x10,1,0,0,0,1)+payload,
 C.HEADER.pack(88,0x10,2,0,0,0,1)+payload,C.HEADER.pack(88,0x10,1,0,0,0,0x82)+payload]
for b in bad_replies:
    try:C.decode_fixed_reply(b,1,b'K'*32)
    except C.Rejected:pass
    else:raise AssertionError('invalid reply accepted')
for n in [True,0,65536,-1]:
    try:C.fixed_request(n)
    except C.Rejected:pass
    else:raise AssertionError('invalid sequence accepted')
for key in [b'',bytes(32),b'K'*31]:
    try:C.decode_fixed_reply(reply,1,key)
    except C.Rejected:pass
    else:raise AssertionError('invalid privacy key accepted')
receipt=dict(status='PASS_FIXED_READ0_GUARDS_AND_OPAQUE_REPLY',request_bytes=len(request),max_reply_bytes=len(reply),
 request_rejections=len(bad),reply_rejections=len(bad_replies),sequence_rejections=4,key_rejections=3,
 response_payload_not_exposed=True,reset_branch_excluded=True,synthetic_payload_only=True,
 authentication_or_thread_exit_not_claimed=True,root_USB_or_camera_operations=0,live_release=False)
with(H/'bounded-read-test-receipt.json').open('x')as f:json.dump(receipt,f,indent=2);f.write('\n')
print(json.dumps(receipt))
