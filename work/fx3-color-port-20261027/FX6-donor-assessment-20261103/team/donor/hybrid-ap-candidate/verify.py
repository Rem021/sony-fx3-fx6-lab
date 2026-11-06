#!/usr/bin/env python3
"""Independent member, byte, identity and frozen-DTB audit; no guest execution."""
import hashlib
import json
import plistlib
import struct
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAC = HERE.parents[5]
DONOR = HERE.parent
SRC = DONOR/'hybrid-entry-candidate/guest-two-entry.cpio'
OUT = HERE/'guest-three-entry.cpio'
AP = DONOR/'nflasha15-files/lib/appFw.so'
BASE_DIR = MAC/'work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability'
BASELINE = BASE_DIR/'fx3-platform-frozen-baseline.json'
FX3 = BASE_DIR/'vmopt-20261103-try2-long-media-gap-v2/guest.cpio'
IDENTITY = MAC/'outputs/fx3-vm/share/fx3-original-app-loader-probe.cpio'
PINS = {SRC:'ff2f927de24b801d334ce9111fb486fb2af85d24c509ab20c43eda0a69ffdc40',
        AP:'a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067',
        FX3:'eaef24b2fe9405fb48bc7823069ad16162cd67c46e004ed6660f761fc16d230d',
        BASELINE:'854e58f0485537e4644f81daa51d532eea5fa1f5e30887c684e9356e542b9669',
        IDENTITY:'7d151d8f1e363c66a947724fd65c5b818e8037347c886d8b0f133c970ad1f862'}
EXPECTED = {
 'usr/bin/bootin.elf': ('dab3ce4b6c28a6c9ffd9f0b893dce1d08f3ee7302a09df87e518409e728be2f2','72480247f8d2a1eeaab076b880c35279c6c94284649e267066f5ea10de6622a6'),
 'usr/bin/im.elf': ('5171f576d8b76cfbf15581389183b390c445bd6ff9dd97fd6668c5f64e77dc91','87d672bd6abbcf695c0a773cb096d72d18429e5107846a2f0d3e8add87e400ec'),
 'usr/lib/appFw.so': ('545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f','a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067')}

def sha(path):
    with path.open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()

def scan(path):
    members=[]; seen=set(); offset=0
    with path.open('rb') as f:
        while True:
            f.seek(offset); h=f.read(110)
            assert len(h)==110 and h[:6]==b'070701', (path,offset)
            vals=[int(h[6+i*8:14+i*8],16) for i in range(13)]
            size,nsize=vals[6],vals[11]
            assert 1<=nsize<=4096
            raw=f.read(nsize);assert raw.endswith(b'\0')
            name=raw[:-1].decode('utf-8')
            data=(offset+110+nsize+3)&~3
            end=(data+size+3)&~3
            assert end<=path.stat().st_size and (name=='TRAILER!!!' or name not in seen)
            if name!='TRAILER!!!': seen.add(name)
            f.seek(offset+110); headname=f.read(data-offset-110)
            f.seek(data+size); pad=f.read(end-data-size)
            assert not any(pad), ('nonzero member padding',name)
            members.append({'name':name,'header':h,'headname':headname,'offset':offset,
                            'data':data,'size':size,'end':end,'mode':vals[1], 'pad':pad})
            if name=='TRAILER!!!': break
            offset=end
        f.seek(end)
        while b:=f.read(1<<20): assert not any(b), 'nonzero post-trailer bytes'
    return members,end

def equal_ranges(a,b,x,y,size):
    a.seek(x);b.seek(y)
    while size:
        n=min(size,1<<20); aa=a.read(n);bb=b.read(n)
        assert len(aa)==len(bb)==n and aa==bb,(x,y,size)
        size-=n

def hash_member(path,item):
    h=hashlib.sha256()
    with path.open('rb') as f:
        f.seek(item['data']); left=item['size']
        while left:
            part=f.read(min(left,1<<20));assert part
            h.update(part);left-=len(part)
    return h.hexdigest()

def dtb_chosen(path):
    b=path.read_bytes()
    magic,total,off_s,off_str,off_rsv,ver,last,boot,size_str,size_s=struct.unpack_from('>10I',b)
    assert magic==0xd00dfeed and total==len(b)
    pos=off_s; stack=[]; found={}
    while pos<off_s+size_s:
        tag=struct.unpack_from('>I',b,pos)[0];pos+=4
        if tag==1:
            end=b.index(0,pos);stack.append(b[pos:end].decode());pos=(end+4)&~3
        elif tag==2:stack.pop()
        elif tag==3:
            size,idx=struct.unpack_from('>II',b,pos);pos+=8
            val=b[pos:pos+size];pos=(pos+size+3)&~3
            end=b.index(0,off_str+idx);key=b[off_str+idx:end].decode()
            if stack==['','chosen'] and key in ('linux,initrd-start','linux,initrd-end'):
                found[key]=int.from_bytes(val,'big')
        elif tag==9:break
        elif tag!=4:raise ValueError(f'FDT tag {tag}')
    return found

def main():
    disk=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
    assert disk['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
    for p,h in PINS.items(): assert sha(p)==h,p
    frozen=json.loads(BASELINE.read_text())
    fixed={}
    for key,v in frozen['sha256'].items():
        assert sha(Path(v['path']))==v['sha256'] and Path(v['path']).stat().st_size==v['bytes'],key
        fixed[key]={'sha256':v['sha256'],'bytes':v['bytes']}
    sm,se=scan(SRC);om,oe=scan(OUT);fm,fe=scan(FX3);im,ie=scan(IDENTITY)
    assert len(sm)==len(om)==len(fm)==1141
    assert [x['name'] for x in sm]==[x['name'] for x in om]==[x['name'] for x in fm]
    assert OUT.stat().st_size==SRC.stat().st_size==FX3.stat().st_size==453184500
    assert se==453184500 and oe==se-28495288
    delta=[]; identity=[]; offsets=[]
    with SRC.open('rb') as a,OUT.open('rb') as b,FX3.open('rb') as c:
        for old,new,fx3 in zip(sm,om,fm):
            name=old['name']; assert old['mode']==new['mode']==fx3['mode']
            assert new['headname']==old['headname']
            assert new['pad']==old['pad']
            assert new['offset']-old['offset'] in (0,-28495288)
            if name=='usr/lib/appFw.so':
                assert old['size']==79015712 and new['size']==50520424
                assert new['header']==old['header'][:54]+f'{new["size"]:08x}'.encode()+old['header'][62:]
                assert hash_member(OUT,new)==PINS[AP]
                with AP.open('rb') as ap: equal_ranges(ap,b,0,new['data'],new['size'])
                delta.append({'name':name,'source_offset':old['offset'],'candidate_offset':new['offset'],
                              'source_size':old['size'],'candidate_size':new['size'],
                              'source_sha256':hash_member(SRC,old),'candidate_sha256':hash_member(OUT,new)})
            else:
                assert new['header']==old['header'] and new['size']==old['size'],name
                equal_ranges(a,b,old['data'],new['data'],old['size'])
            if name in EXPECTED:
                before,after=EXPECTED[name]
                assert hash_member(FX3,fx3)==before and hash_member(OUT,new)==after
                identity.append({'name':name,'fx3_sha256':before,'candidate_sha256':after,
                                 'fx3_bytes':fx3['size'],'candidate_bytes':new['size']})
            else:
                equal_ranges(c,b,fx3['data'],new['data'],fx3['size'])
                assert new['header']==fx3['header'] and new['headname']==fx3['headname'],name
            if old['offset']!=new['offset']:offsets.append(name)
    assert len(delta)==1 and len(identity)==3
    by_name={x['name']:x for x in om[:-1]}
    original_elf=[]
    with IDENTITY.open('rb') as baseline_elf:
        for item in im[:-1]:
            baseline_elf.seek(item['data'])
            if baseline_elf.read(4)==b'\x7fELF': original_elf.append(item)
    assert len(original_elf)==20
    rejected=[]
    for item in original_elf:
        name=item['name']
        if name not in by_name or hash_member(IDENTITY,item)!=hash_member(OUT,by_name[name]):
            rejected.append(name)
    # Historical 38-member ELF gate does not contain appFw.so. Keep its two
    # precise exceptions; apply a third independent check against full FX3 CPIO.
    assert set(rejected)=={'usr/bin/bootin.elf','usr/bin/im.elf'}, rejected
    present_dirs={'.'};parent_errors=[]
    for item in om[:-1]:
        name=item['name'];parent=str(Path(name).parent)
        if parent not in present_dirs:parent_errors.append({'name':name,'parent':parent})
        if item['mode'] & 0o170000 == 0o040000:present_dirs.add(name)
    assert not parent_errors
    # /init and all helpers, Backup, libraries, link targets, metadata and order covered above.
    dtb=Path(frozen['sha256']['fx3_dtb_full_binary']['path']);chosen=dtb_chosen(dtb)
    load=int(frozen['platform_parameters']['initrd_load_address'],16)
    assert chosen['linux,initrd-start']==load
    assert chosen['linux,initrd-end']==load+OUT.stat().st_size
    listing=subprocess.run(['/usr/bin/bsdtar','-tf',str(OUT)],capture_output=True,text=True,check=True)
    names=listing.stdout.splitlines()
    assert names==[x['name'] for x in om[:-1]], ('bsdtar name/order mismatch',len(names))
    (HERE/'bsdtar-list.txt').write_text(listing.stdout)
    receipt={'status':'BUILT_AND_INDEPENDENTLY_STATIC_VERIFIED_NOT_RUN','candidate_sha256':sha(OUT),
             'source_sha256':PINS[SRC],'fx3_baseline_cpio_sha256':PINS[FX3],
             'bytes':OUT.stat().st_size,'members':len(om)-1,'trailer_end':oe,
             'post_trailer_zero_bytes':OUT.stat().st_size-oe,'AP_delta':delta[0],
             'expected_exact_identity_exceptions':identity,'other_members_header_and_payload_equal':True,
             'original_identity_cpio_sha256':PINS[IDENTITY],'original_identity_elf_count':len(original_elf),
             'original_identity_gate_rejections':rejected,'parent_order_errors':parent_errors,
             'shifted_member_count':len(offsets),'first_shifted_member':offsets[0] if offsets else None,
             'bsdtar_names_equal':True,'frozen_artifacts':fixed,'frozen_initrd_load':hex(load),
             'dtb_chosen':{k:hex(v) for k,v in chosen.items()},'qemu_started':False}
    (HERE/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    manifest={'state':'STATIC_CANDIDATE_DO_NOT_DEPLOY','candidate_path':str(OUT),
              'candidate_sha256':receipt['candidate_sha256'],'candidate_bytes':receipt['bytes'],
              'source_path':str(SRC),'source_sha256':PINS[SRC],
              'exact_three_member_allowlist':identity,
              'historical_20_ELF_gate_exact_rejections':rejected,
              'all_other_member_header_payload_and_order_fixed':True,
              'frozen_platform_sha256':{k:v['sha256'] for k,v in fixed.items()},
              'frozen_dtb_initrd_range':receipt['dtb_chosen'],
              'runtime_unknowns':['47 immediate relocation symbols and actual global link-map order',
                                  'FX3 diagnostic guards 48/60 word mismatch with FX6 AP',
                                  '182 unresolved delayed imports plus 15 FX6-libmpr-only candidates',
                                  'first natural FX6 AP IPC, hardware and user-visible behavior'],
              'runtime_policy':'Only existing runtime owner may schedule one read-only load observation; no guest changes or guard bypass.'}
    (HERE/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:receipt[k] for k in ('status','candidate_sha256','bytes','members','post_trailer_zero_bytes','shifted_member_count','bsdtar_names_equal','dtb_chosen')},indent=2))

if __name__=='__main__':main()
