"""Pure transcript classification for future host reports, never USB/auth I/O.

Protocol responses alone never attest cryptographic acceptance, mode change,
camera-thread exit or absence of persistent writes. No launch/release API.
"""
from dataclasses import dataclass

class InvalidTranscript(ValueError):pass

@dataclass(frozen=True)
class Observation:
    protocol_state:str
    family:int
    authentication_verified:bool=False
    mode_transition_verified:bool=False
    camera_thread_exit_verified:bool=False
    persistent_effects_excluded:bool=False
    live_operation_authorized:bool=False

def decode_reply(frame):
    if type(frame)is not bytes or len(frame)!=516:raise InvalidTranscript('exact516 byte reply required')
    inverse=int.from_bytes(frame[:2],'big');salt=int.from_bytes(frame[2:4],'big')
    code=((~inverse)&0xffff)-salt
    if code not in (2,4,6,8):raise InvalidTranscript('unknown auth reply code')
    return code,frame[4:]

def classify_observed_codes(codes,final_byte=None):
    """Classify only observations actually collected; no trust upgrade."""
    if type(codes)not in (tuple,list) or any(type(n)is not int for n in codes):
        raise InvalidTranscript('typed response sequence required')
    if not codes:return Observation('NO_PROTOCOL_REPLY',0)
    family=codes[0]
    if family not in (2,8):raise InvalidTranscript('challenge must start sequence')
    expected=(family,4,family,4,family,4,6)
    if not 1<=len(codes)<=7 or tuple(codes)!=expected[:len(codes)]:
        raise InvalidTranscript('mixed family or unexpected response sequence')
    if len(codes)==7:
        if type(final_byte)is not int or final_byte!=1:raise InvalidTranscript('completion response byte is not1')
        return Observation('EXCHANGE_FINISHED_AUTHENTICATION_UNVERIFIED',family)
    if final_byte is not None:raise InvalidTranscript('unexpected final byte before completion')
    return Observation('CHALLENGE_OBSERVED' if len(codes)==1 else 'PARTIAL_EXCHANGE',family)

def classify_frames(frames):
    if type(frames)not in (tuple,list):raise InvalidTranscript('bounded reply frame list required')
    if len(frames)>7:raise InvalidTranscript('too many reply frames')
    replies=[decode_reply(f)for f in frames]
    return classify_observed_codes([x[0]for x in replies],replies[-1][1][0]if len(replies)==7 else None)
