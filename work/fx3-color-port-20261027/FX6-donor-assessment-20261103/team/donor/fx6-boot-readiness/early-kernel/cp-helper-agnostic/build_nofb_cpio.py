#!/usr/bin/env python3
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent;SRC=ROOT/'guest-hybrid-fx6kernel-capid-grmreal46.cpio';OUT=ROOT/'guest-hybrid-fx6kernel-capid-grmreal52.cpio';FIXED=453184500
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def parse(data):
 m=[];o=0
 while o+110<=len(data):
  h=data[o:o+110]
  if h[:6]!=b'070701':raise SystemExit('magic')
  v=[int(h[6+i*8:14+i*8],16) for i in range(13)];fs=v[6];ns=v[11];name=data[o+110:o+110+ns-1].decode();p=o+110+ns;p+=(-p)%4
  m.append({'name':name,'hdr':h,'data':data[p:p+fs],'fs':fs});o=p+fs;o+=(-o)%4
  if name=='TRAILER!!!':break
 return m
def main():
 members=parse(SRC.read_bytes());init=next(m for m in members if m['name']=='init')
 old=b'LD_PRELOAD=/usr/lib/libgrm-fbinit9.so:';new=b'LD_PRELOAD='
 assert init['data'].count(old)==1
 init['data']=init['data'].replace(old,new);init['fs']=len(init['data'])
 h=bytearray(init['hdr']);h[6+6*8:14+6*8]=b'%08x'%init['fs'];init['hdr']=bytes(h)
 out=bytearray()
 for m in members:
  out+=m['hdr']+m['name'].encode()+b'\0';out+=b'\0'*((-len(out))%4);out+=m['data'];out+=b'\0'*((-len(out))%4)
 if len(out)>FIXED:raise SystemExit('too big')
 out+=b'\0'*(FIXED-len(out));OUT.write_bytes(out)
 print(json.dumps({'schema':'fx6-hybrid-nofb-cpio-v1','source':str(SRC),'output':str(OUT),'sha':sha(OUT)},indent=2))
if __name__=='__main__':main()
