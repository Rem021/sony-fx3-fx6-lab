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
HEADER_REASONS={
    0:'not_evaluated',1:'ok',2:'short_count',3:'size_mismatch',4:'pfunc_mismatch',
    5:'sequence_mismatch',6:'version_mismatch',7:'micon_mismatch',8:'offset_mismatch',
    9:'response_mismatch',10:'multiple_mismatch'}
HEADER_FIELDS=('size','pFunc','sequence','version','miconType','offsetType','response')

def sequence(n):
    if type(n)is not int or not 1<=n<=65535:raise Rejected('sequence must be1..65535')
    return n

def fixed_request(n):
    n=sequence(n)
    return HEADER.pack(5,0x10,n,0,0,0,0)+b'\0\0\x1f\0\0'

def validate_fixed_request(packet,n):
    if type(packet)is not bytes or packet!=fixed_request(n):
        raise Rejected('only exact ProductInfo001F/read0 packet permitted')

def classify_reply_header(header,n):
    """Classify a response header into bounded non-payload reason and field mask."""
    n=sequence(n)
    if type(header)is not bytes:raise Rejected('header bytes required')
    if len(header)!=12:
        return dict(reason=2,name=HEADER_REASONS[2],mask=0,fields=())
    actual=HEADER.unpack_from(header)
    expected=(88,0x10,n,3,0,0,1)
    mask=0;first=0
    for bit,(a,b) in enumerate(zip(actual,expected)):
        if a!=b:
            mask|=1<<bit
            if not first:first=bit+3
    reason=1 if not mask else (10 if (mask&(mask-1)) else first)
    fields=tuple(name for bit,name in enumerate(HEADER_FIELDS) if mask&(1<<bit))
    return dict(reason=reason,name=HEADER_REASONS[reason],mask=mask,fields=fields)

@dataclass(frozen=True)
class ReadObservation:
    sequence:int
    payload_bytes:int
    payload_hmac:str
    header_reason:int=1
    header_mask:int=0
    static_gate:str='stock levelA orB; not level3 proof'
    live_identity_verified:bool=False
    authentication_verified:bool=False
    thread_exit_verified:bool=False
    live_operation_authorized:bool=False

def decode_fixed_reply(packet,n,key):
    n=sequence(n)
    if type(key)is not bytes or len(key)!=32 or not any(key):raise Rejected('per-trial32B privacy key required')
    if type(packet)is not bytes or len(packet)!=MAX_REPLY:raise Rejected('exact100B reply required')
    verdict=classify_reply_header(packet[:12],n)
    if verdict['reason']!=1:raise Rejected('unexpected reply header: '+verdict['name'])
    tag=hmac.new(key,b'FX3-HASP-READ0-v1\0'+packet,sha256).hexdigest()
    return ReadObservation(n,88,tag,verdict['reason'],verdict['mask'])
