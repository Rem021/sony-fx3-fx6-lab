"""Prospective service-only read codec. No IO, device handles or live release.

Same command supports reset0x80; this codec emits/accepts only read argument0.
An88B reply is capability data, not highest-level auth or thread-exit proof.
"""
from dataclasses import dataclass
from hashlib import sha256
import hmac,struct

class Rejected(ValueError):pass
HEADER=struct.Struct('<IHHBBBB')
EXPECTED_USB_ID=(0x054c,0x0336) # A prospective transport must bind this separately.
MAX_REPLY=100

def sequence(n):
    if type(n)is not int or not 1<=n<=65535:raise Rejected('sequence must be1..65535')
    return n

def fixed_request(n):
    n=sequence(n)
    return HEADER.pack(5,0x10,n,0,0,0,0)+b'\0\0\x1f\0\0'

def validate_fixed_request(packet,n):
    if type(packet)is not bytes or packet!=fixed_request(n):
        raise Rejected('only exact ProductInfo001F/read0 packet permitted')

@dataclass(frozen=True)
class ReadObservation:
    sequence:int
    payload_bytes:int
    payload_hmac:str
    static_gate:str='stock levelA orB; not level3 proof'
    live_identity_verified:bool=False
    authentication_verified:bool=False
    thread_exit_verified:bool=False
    live_operation_authorized:bool=False

def decode_fixed_reply(packet,n,key):
    n=sequence(n)
    if type(key)is not bytes or len(key)!=32 or not any(key):raise Rejected('per-trial32B privacy key required')
    if type(packet)is not bytes or len(packet)!=MAX_REPLY:raise Rejected('exact100B reply required')
    if HEADER.unpack_from(packet)!=(88,0x10,n,3,0,0,1):raise Rejected('unexpected reply header, identity or status')
    tag=hmac.new(key,b'FX3-HASP-READ0-v1\0'+packet,sha256).hexdigest()
    return ReadObservation(n,88,tag)
