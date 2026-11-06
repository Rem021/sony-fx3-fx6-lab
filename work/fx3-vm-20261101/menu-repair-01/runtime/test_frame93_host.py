from pathlib import Path
import struct,json,hashlib,shlex
from osd_ring93_v4 import RingReader,BASE,TOTAL,HEADER,STRIDE,MAGIC,fnv
from key_readback93_v2_frame import capture_frame
R=Path(__file__).resolve().parent;D=R/'ap93-frame-host-fixture';assert not D.exists();D.mkdir();width=640;height=480;span=width*height*2;blob=bytearray(TOTAL);head=[0]*16;head[0]=MAGIC;head[1]=2;head[3]=1;head[4]=3;head[11:14]=[8,STRIDE,HEADER];struct.pack_into('<16Q',blob,0,*head);raws={}
for seq,kind,base,token,epoch in [(1,1,0x43feb5000,0x402,0x8c),(2,2,0x512340000,0x401,2),(3,2,0x512340000,0x401,0)]:
 phys=base+0x100;raw=(b'\xff\xff' if seq==1 else b'\x0f\xf0')*(span//2);v=[0]*36;v[0:13]=[seq,1,seq,0x1003,seq,token,phys,0,width,height,width,span,fnv(raw)];v[13:26]=[1,seq+10,seq+20,token,token,1,0x1234,0,1,0x200000100,0x200000000,0x200140000,base];v[26:36]=[1,kind,0 if kind==1 else 0x123456,epoch,0 if kind==1 else 0xabcdef,base,0x140000,token,0 if kind==1 else 0x90001000,phys];start=HEADER+(seq-1)*STRIDE;struct.pack_into('<36Q',blob,start,*v);blob[start+0x180:start+0x1a4]=bytes(range(36));blob[start+0x200:start+0x200+span]=raw;raws[phys]=raw
class Reader(RingReader):
 def read(self,address,n,name):assert address==BASE;return bytes(blob[:n])
r=Reader(D,None);r.poll();assert len(r.records)==2 and len(r.rejects)==1 and r.records[-1]['physical']=='0x512340100';assert r.records[0]['native_identity']['map_end']=='0x200140000' and r.records[-1]['registered_target']['epoch']==2;assert r.records[0]['descriptor']==bytes(range(36)).hex()
def qmp(cmd,args):
 words=shlex.split(args['command-line']);assert words[0]=='pmemsave';addr=int(words[1],0);n=int(words[2],0);assert n==span;Path(words[3]).write_bytes(raws[addr]);return {'return':''}
x=capture_frame(qmp,D,'switch-to-native',1,0x30,0);assert not x.get('error') and x['matches_committed_ring'] and x['physical']=='0x512340100' and x['registered_target']['epoch']==2
raws[0x512340100]=b'\0'*span;y=capture_frame(qmp,D,'stale-physical-content',2,3,0);assert y.get('error') and not(D/'ap93-stale-physical-content.png').exists();p=R/'ap93-frame-export-host-check.json';v=json.loads(p.read_text());v['host_parser_test']={'FB545_to_arbitrary_registered_native_target':True,'zero_epoch_rejected':True,'separate_mapping_and_descriptor_fields_no_overlap':True,'QMP_physical_matches_native_committed_snapshot':True,'mismatching_current_physical_pixels_rejected':True,'no_physical_address_allowlist':True};p.write_text(json.dumps(v,indent=2)+'\n');print('FRAME HOST PASS metadata/FB545_native_switch/zeroepoch/physicalSHA/stalecontent/descriptorlayout')
