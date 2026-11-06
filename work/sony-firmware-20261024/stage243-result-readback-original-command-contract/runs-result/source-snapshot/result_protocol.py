"""Offline-only exact result envelope and decoder; no transport or shell.

The path is one immutable candidate for OUR RAM record, not a path API.
Original command allocation/mounting/global-path state remain unvalidated.
"""
from dataclasses import dataclass
from hashlib import sha256
import struct,zlib

SIZE=262144;PAGE=65536
RAM_RESULT='/tmp_wbshd/fx3-plan-preparation-v1/entry.local-result-v1.bin'
SELECTED_RESULT='/tmp/jiritsu/../../tmp_wbshd/fx3-plan-preparation-v1/entry.local-result-v1.bin'
def need(ok,why):
 if not ok:raise ValueError(why)
def fixed(value,size,name):
 need(type(value) is bytes and len(value)==size and any(value),name+' invalid');return value
def crc(raw):return zlib.crc32(raw[:252])
@dataclass(frozen=True)
class Expected:
 file_sha:bytes
 image_id:bytes
 nonce:bytes
 profile:bytes
 controller:bytes
 ttl:int
 @classmethod
 def from_artifact(cls,raw,*,pinned_file_sha,nonce,profile,controller):
  fixed(pinned_file_sha,32,'pinned file SHA');fixed(nonce,16,'nonce');fixed(profile,32,'profile');fixed(controller,32,'controller')
  need(type(raw) is bytes and len(raw)==SIZE and sha256(raw).digest()==pinned_file_sha,'artifact differs from externally pinned file')
  need(raw[:7]==b'\x7fELF\x02\x01\x01' and struct.unpack_from('<HHI',raw,16)==(3,183,1),'ELF identity')
  need(struct.unpack_from('<Q',raw,32)[0]==64 and struct.unpack_from('<HH',raw,54)==(56,6),'program headers')
  for i,flags in enumerate([4,5,4,6]):
   p=struct.unpack_from('<IIQQQQQQ',raw,64+i*56)
   need(p==(1,flags,i*PAGE,i*PAGE,i*PAGE,PAGE,PAGE,PAGE),'ELF LOAD layout')
  cfg=raw[4096:4352];need(cfg[:16]==b'FX3ENTRYCFGv2'.ljust(16,b'\0') and struct.unpack_from('<IIII',cfg,16)==(2,1,1,1),'configuration identity')
  need(cfg[32:48]==nonce and cfg[48:80]==profile and cfg[80:112]==controller,'configuration association differs')
  ttl,size,flags=struct.unpack_from('<QQI',cfg,144);need(0<ttl<=900_000_000_000 and size==SIZE and flags==1 and not any(cfg[164:252]) and crc(cfg)==struct.unpack_from('<I',cfg,252)[0],'configuration bounds/CRC')
  return cls(pinned_file_sha,sha256(raw[:3*PAGE]+bytes(PAGE)).digest(),nonce,profile,controller,ttl)
 def plan(self,issued,expires):
  need(type(issued) is int and type(expires) is int and 0<issued<expires<1<<64 and expires-issued==self.ttl,'target time window')
  p=bytearray(256);p[:16]=b'FX3ENTRYPLANv2'.ljust(16,b'\0');struct.pack_into('<III',p,16,2,1,1);p[32:48]=self.nonce;p[48:80]=self.profile;p[80:112]=self.controller;p[112:144]=self.image_id;struct.pack_into('<QQI',p,144,issued,expires,1);p[164:196]=self.file_sha;struct.pack_into('<Q',p,196,SIZE);struct.pack_into('<I',p,252,crc(p));return bytes(p)
def candidate_read_frames(expected):
 need(type(expected) is Expected,'pinned expectation required')
 # Inner ADJ bytes only; no Senser authentication, DMM session, send or retry.
 return (struct.pack('<HH',0x1001,0x000f)+b'\0'+SELECTED_RESULT.encode('ascii')+b'\0',
         struct.pack('<HH',0x1001,0x0011)+b'\0\xff\0')
def decode_native_body(body,expected):
 need(type(expected) is Expected,'pinned expectation required')
 need(type(body) is bytes and len(body)==260,'exact native status+256B record required')
 need(struct.unpack_from('<I',body)[0]==0,'native file reply error')
 p=body[4:];need(p[:16]==b'FX3LOCALRESULT1'.ljust(16,b'\0'),'not our local result')
 version,purpose,status,reason=struct.unpack_from('<IIII',p,16)
 need((version,purpose)==(1,1) and status in (2,4,11),'unsupported result')
 need(struct.unpack_from('<I',p,252)[0]==crc(p) and not any(p[244:252]),'record CRC/reserved')
 need(p[32:48]==expected.nonce and p[48:80]==expected.file_sha and p[80:112]==expected.image_id and p[144:176]==expected.profile and p[176:208]==expected.controller,'record binding differs')
 issued,expires,finished=struct.unpack_from('<QQQ',p,208)
 plan=expected.plan(issued,expires);need(sha256(plan).digest()==p[112:144],'whole plan SHA differs')
 pid,tid,phase=struct.unpack_from('<III',p,232);need(1<pid<=0x7fffffff and 1<tid<=0x7fffffff and phase==1 and finished>=issued,'process/time/phase')
 if status==11:need(reason==0 and finished<expires,'inconsistent local success')
 return dict(classification='LOCAL_OBSERVATION_ONLY',reported_core_status=status,reported_reason=reason,
             expected_artifact_and_plan_fields_consistent=True,record_phase='BEFORE_REPORT_PUBLICATION_CLEANUP',
             pid=pid,tid=tid,issued=issued,expires=expires,finished=finished,
             authenticated_camera_identity_or_actual_transport_verified=False,
             report_close_setter_return_USB_or_full_job_completion_proven=False,
             may_release_owner_or_flash=False)
