from pathlib import Path
import struct,tempfile,json
import osd_ring85_v3 as m
R=Path(__file__).resolve().parent;D=Path(tempfile.mkdtemp(prefix='osd-ring-v3-host-check-',dir=R));memory=bytearray(0x1000000);struct.pack_into('<16Q',memory,0,m.MAGIC,1,123,1,1,1,1,0,0,0,0,8,m.STRIDE,m.HEADER,0,0);pixels=(b'\x0f\xf0'+b'\xff\xff')*2;v=[1,1,1,0x1003,1,123,0x43feb5100,0,2,2,2,len(pixels),m.fnv(pixels),100,200,300,545,123,1,74,44,1,0x1100,0x1000,0x2000,0x43feb5000];struct.pack_into('<26Q',memory,m.HEADER,*v);memory[m.HEADER+256:m.HEADER+256+len(pixels)]=pixels
class Test(m.RingReader):
 def read(self,a,n,name):return bytes(memory[a-m.BASE:a-m.BASE+n])
x=Test(D,None);x.poll();assert x.first_nonuniform and len(x.records)==1 and len(x.records[0]['views'])==2 and x.records[0]['native_bitmap_format']==1;x.poll(final=True);assert len(x.records)==1;struct.pack_into('<Q',memory,m.HEADER,2);struct.pack_into('<Q',memory,32,2);x.poll();assert x.rejects;(R/'helpers/osd-ring-v3-host-check.json').write_text(json.dumps({'passed':True,'scope':'Synthetic host-only ring26word parsing/hash/bounds/native_and_alternative_PNG/duplicate/torn_header; not guest pixel acceptance','directory':str(D)},indent=2)+'\n');print('OSD_RING_V3_HOST_PASS')
