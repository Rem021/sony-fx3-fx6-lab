"""Static PowerOn event model; no ELF execution, native pointers, or firmware output."""
import struct
class Unproven(ValueError): pass
FX3_EVENT=0x1026
FX6_EVENT=0x102d
def translate(payload):
    if type(payload) is not bytes or len(payload)!=12:raise Unproven('requires exact immutable 12-byte PowerOn event')
    event,echo,result=struct.unpack('<III',payload)
    if event!=FX3_EVENT:raise Unproven('source event is not proven FX3 PowerOnFinished')
    if result!=0:raise Unproven('nonzero result domain not produced by pinned PowerOnMain; preserve failure by refusing')
    return struct.pack('<I',FX6_EVENT)+payload[4:]
def consume_fx6(payload,pending):
    """Abstract bytes/state only; explicit rejection for unproven object state.
    pending key/echo represent already-registered native context, not a forged context.
    """
    if type(payload) is not bytes or len(payload)!=12:raise Unproven('invalid record')
    event,echo,result=struct.unpack('<III',payload)
    if event!=FX6_EVENT or pending.get('key')!=event:raise Unproven('no matching pending key; original callback count branch does not notify')
    if pending.get('phase')!='pending':raise Unproven('missing/moved promise; duplicate not accepted')
    if result!=0:raise Unproven('result enum conversion unknown')
    # Preserve observed update then notification, and request-side echo comparison.
    out=dict(pending,object_3e4=echo,object_8=result,phase='notified',promise_moved=True)
    out['request_result']=0 if pending['request_echo']==echo else 0xbd
    return out
