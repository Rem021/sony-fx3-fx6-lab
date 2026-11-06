"""Local IPC packet encoder/independent decoder, never an authority issuer."""
from hashlib import sha256
import struct,zlib
MAGIC=b'FX3IPCGATEv1'.ljust(16,b'\0')
def packet(kind,hand,result=0):
    if kind not in (1,2,3,4) or type(hand) is not bytes or len(hand)!=256 or type(result) is not int or not 0<=result<=255 or (kind!=4 and result):raise ValueError('packet fields')
    out=bytearray(320);out[:16]=MAGIC;struct.pack_into('<IIII',out,16,kind,1,result,0);out[32:288]=hand
    struct.pack_into('<I',out,316,zlib.crc32(out[:316]));return bytes(out)
def decode(raw):
    if type(raw) is not bytes or len(raw)!=320 or raw[:16]!=MAGIC or zlib.crc32(raw[:316])!=struct.unpack_from('<I',raw,316)[0]:raise ValueError('IPC packet CRC/size/magic')
    kind,version,result,flags=struct.unpack_from('<IIII',raw,16)
    if kind not in (1,2,3,4) or version!=1 or flags or raw[288:316]!=bytes(28) or not 0<=result<=255 or (kind!=4 and result):raise ValueError('IPC packet fields')
    return dict(kind=kind,result=result,hand=raw[32:288],handoff_sha256=sha256(raw[32:288]).hexdigest(),trusted_launcher_or_global_owner_attested=False)
