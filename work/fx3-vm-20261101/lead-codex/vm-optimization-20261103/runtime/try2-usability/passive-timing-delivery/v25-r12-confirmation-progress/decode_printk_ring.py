from pathlib import Path
import struct,json,hashlib,argparse
p=argparse.ArgumentParser();p.add_argument('run',type=Path);a=p.parse_args();r=a.run
pointer=(r/'printk-pointers.bin').read_bytes();indices=(r/'printk-indices.bin').read_bytes();b=(r/'printk-ring.bin').read_bytes()
assert len(pointer)==16 and len(indices)==32
size,addr=struct.unpack('<QQ',pointer);assert size==len(b)==0x20000
firstseq,nextseq,firstidx,nextidx=struct.unpack_from('<QQII',indices);assert nextseq>=firstseq and nextseq-firstseq<=2000
rows=[];off=firstidx
for seq in range(firstseq,nextseq):
 ts,ln,txt,di,fac,flags=struct.unpack_from('<QHHHBB',b,off)
 if ln==0:
  off=0;ts,ln,txt,di,fac,flags=struct.unpack_from('<QHHHBB',b,off)
 assert ln>=16 and ln%4==0 and off+ln<=len(b) and txt+di+16<=ln
 raw=b[off+16:off+16+txt]
 rows.append({'sequence':seq,'ring_offset':off,'timestamp_nsec':ts,'record_length':ln,'text_length':txt,'dictionary_length':di,'facility':fac,'level':flags>>5,'flags':flags&31,'text':raw.decode('utf-8',errors='replace')})
 off=(off+ln)%len(b)
assert off==nextidx
(r/'printk-decoded.txt').write_text(''.join(f"{v['sequence']} [{v['timestamp_nsec']/1e9:.6f}] {v['text']}\n" for v in rows))
(r/'printk-decoded.json').write_text(json.dumps({'scope':'Linux4.9 printk_log 16-byte header; seq/index/length-closed raw ring decode; not grep output','expected_ring_virtual':hex(addr),'first_seq':firstseq,'next_seq':nextseq,'first_idx':firstidx,'next_idx':nextidx,'records':rows,'raw_input_sha256':{n:hashlib.sha256((r/n).read_bytes()).hexdigest() for n in ['printk-pointers.bin','printk-indices.bin','printk-ring.bin']}},ensure_ascii=False,indent=2)+'\n')
print('records',len(rows),'first',firstidx,'next',nextidx)
