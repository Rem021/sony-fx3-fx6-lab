"""Versioned association packets only; never user/device authority issuance."""
import struct,zlib
from hashlib import sha256
MAGIC=b'FX3IPCGATEv2'.ljust(16,b'\0')
def packet(kind,hand,result=0):
 if kind not in (1,2,3,4) or len(hand)!=256 or not 0<=result<=255 or (kind!=4 and result):raise ValueError('IPC fields')
 out=bytearray(320);out[:16]=MAGIC;struct.pack_into('<IIII',out,16,kind,2,result,0);out[32:288]=hand;struct.pack_into('<I',out,316,zlib.crc32(out[:316]));return bytes(out)
def decode(raw):
 if len(raw)!=320 or raw[:16]!=MAGIC or zlib.crc32(raw[:316])!=struct.unpack_from('<I',raw,316)[0]:raise ValueError('IPC CRC/magic')
 k,v,r,f=struct.unpack_from('<IIII',raw,16)
 if k not in (1,2,3,4) or v!=2 or f or raw[288:316]!=bytes(28) or r>255 or (k!=4 and r):raise ValueError('IPC fields')
 return dict(kind=k,result=r,hand=raw[32:288])
def handoff(req,pid,ppid,now,keeper_digest,keeper_bytes,nonce='c'*64):
 out=bytearray(256);out[:16]=b'FX3HANDOFFv2'.ljust(16,b'\0');out[16:32]=req[16:32];out[32:64]=bytes.fromhex(nonce);out[64:96]=b'\xdd'*32;out[96:128]=sha256(req).digest()
 role,window=struct.unpack_from('<II',req,36);total=struct.unpack_from('<Q',req,48)[0];reqcrc=struct.unpack_from('<I',req,124)[0]
 struct.pack_into('<IIIIIIQQQIII',out,128,pid,ppid,role,window,1,3,now,now+120_000_000_000,total,reqcrc,1,1)
 out[188:220]=bytes.fromhex(keeper_digest);struct.pack_into('<I',out,220,keeper_bytes);struct.pack_into('<I',out,252,zlib.crc32(out[:252]));return bytes(out)
def job(req,seq,pid,now,keeper_digest,keeper_bytes,worker_digest,nonce='c'*64,finish=False):
 out=bytearray(512);out[:16]=b'FX3KEEPJOBv1'.ljust(16,b'\0');struct.pack_into('<IIII',out,16,1,2 if finish else 1,0,seq)
 if not finish:out[32:288]=handoff(req,0,pid,now,keeper_digest,keeper_bytes,nonce);out[288:416]=req
 out[416:448]=bytes.fromhex(keeper_digest);out[448:480]=bytes.fromhex(worker_digest);struct.pack_into('<I',out,508,zlib.crc32(out[:508]));return bytes(out)
def result(raw):
 if len(raw)!=512 or raw[:16]!=b'FX3KEEPRESv1'.ljust(16,b'\0') or zlib.crc32(raw[:508])!=struct.unpack_from('<I',raw,508)[0]:raise ValueError('keeper result CRC/magic')
 v,op,state,seq,pid,child,reason=struct.unpack_from('<IIIIIII',raw,16)
 if v!=1 or op not in (1,2) or state not in (0,1,2,3,4) or raw[44:48]!=bytes(4) or raw[416:508]!=bytes(92):raise ValueError('keeper result fields')
 return dict(operation=op,state=state,sequence=seq,keeper_pid=pid,child_pid=child,reason=reason,job_sha256=raw[96:128].hex(),keeper_sha256=raw[128:160].hex(),hand=raw[160:416],actual_keeper_exit_observed=False)
