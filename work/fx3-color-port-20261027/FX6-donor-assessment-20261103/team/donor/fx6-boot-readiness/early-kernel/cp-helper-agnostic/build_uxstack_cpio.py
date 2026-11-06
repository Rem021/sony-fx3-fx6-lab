#!/usr/bin/env python3
import hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
SRC=ROOT/'guest-hybrid-fx6kernel-capid-grmreal21.cpio'
HELPER=ROOT/'grm-fbinit'/'read-ux-stack'
OUT=ROOT/'guest-hybrid-fx6kernel-capid-grmreal25.cpio'
FIXED=453184500
NEW='simulation/read-ux-stack'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def parse(data):
    m=[];o=0
    while o+110<=len(data):
        h=data[o:o+110]
        if h[:6]!=b'070701':raise SystemExit('magic')
        v=[int(h[6+i*8:14+i*8],16) for i in range(13)]
        fs=v[6];ns=v[11];name=data[o+110:o+110+ns-1].decode();p=o+110+ns;p+=(-p)%4
        payload=data[p:p+fs];e=p+fs;e+=(-e)%4
        m.append({'name':name,'hdr':h,'data':payload,'fs':fs})
        o=e
        if name=='TRAILER!!!':break
    return m
def header(name,mode,data):
    nb=name.encode()+b'\0';vals=[0,mode,0,0,1,0,len(data),0,0,0,0,len(nb),0]
    h=b'070701'+b''.join(b'%08x'%v for v in vals);o=h+nb;o+=b'\0'*((-len(o))%4);return o+data+b'\0'*((-len(o+data))%4)
def main():
    members=parse(SRC.read_bytes());init=next(m for m in members if m['name']=='init')
    old=b"  echo FX3_AP_IM_ENDMAPS_${im_pid}_END\n  done\n  /bin/busybox sleep 1\n"
    new=b"  echo FX3_AP_IM_ENDMAPS_${im_pid}_END\n  done\n  /simulation/read-ux-stack\n  /bin/busybox sleep 1\n"
    cnt=init['data'].count(old)
    if cnt<1:raise SystemExit('observer block not found')
    init['data']=init['data'].replace(old,new);init['fs']=len(init['data'])
    hdr=bytearray(init['hdr']);hdr[6+6*8:14+6*8]=b'%08x'%init['fs'];init['hdr']=bytes(hdr)
    helper=HELPER.read_bytes();out=bytearray()
    for m in members:
        if m['name']=='TRAILER!!!':
            out+=header(NEW,0o100755,helper)
        out+=m['hdr']+m['name'].encode()+b'\0';out+=b'\0'*((-len(out))%4)
        out+=m['data'];out+=b'\0'*((-len(out))%4)
    if len(out)>FIXED:raise SystemExit('too big')
    out+=b'\0'*(FIXED-len(out));OUT.write_bytes(out)
    print(json.dumps({'schema':'fx6-hybrid-uxstack-cpio-v1','source':str(SRC),'source_sha256':sha(SRC),'output':str(OUT),'output_sha256':sha(OUT),'output_bytes':OUT.stat().st_size,'init_replacements':cnt,'helper':{'bytes':len(helper),'sha256':hashlib.sha256(helper).hexdigest()}},indent=2))
if __name__=='__main__':main()
