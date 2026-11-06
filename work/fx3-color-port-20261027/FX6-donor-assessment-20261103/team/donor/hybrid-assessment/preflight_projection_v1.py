#!/usr/bin/env python3
"""Read-only ELF64/AArch64 dependency and symbol-version preflight.

No target code is executed.  Missing files and weak/ambiguous resolution stay
explicit; this is not an ld.so or module-loader emulator.
"""
import hashlib
import json
import struct
from pathlib import Path

HERE = Path(__file__).resolve().parent
DONOR = HERE.parent
MAC = HERE.parents[5]
FX6 = DONOR / 'nflasha15-files'
FX6_BOOT = DONOR / 'nested-files/nflasha3-initrd'
FX3 = MAC / 'work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files'
BASELINE = MAC / 'work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/fx3-platform-frozen-baseline.json'
CPIO = MAC / 'work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/vmopt-20261103-try2-long-media-gap-v2/guest.cpio'
CPIO_AUDIT = CPIO.with_name('cpio-audit.json')
FX3_IMAGE = MAC / 'work/sony-firmware-20261024/stage47-runtime-provider-binding/official-files/nflasha3/vmlinux.bin'
PINS = {
    BASELINE:'854e58f0485537e4644f81daa51d532eea5fa1f5e30887c684e9356e542b9669',
    CPIO:'eaef24b2fe9405fb48bc7823069ad16162cd67c46e004ed6660f761fc16d230d',
    CPIO_AUDIT:'cc0b3c5b1925aa4bb0cb14aab275f2831833c7378490ca5408789f3824eb4847',
    FX3_IMAGE:'da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c',
    FX6/'bin/bootin.elf':'72480247f8d2a1eeaab076b880c35279c6c94284649e267066f5ea10de6622a6',
    FX6/'bin/im.elf':'87d672bd6abbcf695c0a773cb096d72d18429e5107846a2f0d3e8add87e400ec',
    FX6/'lib/appFw.so':'a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067',
    FX6/'lib/libmpr.so':'814dfff34cac6517d71f659fce8d1ead0bb7ee52b8a9ac1a4e25aa9f83ac2d4e',
    FX6/'lib/libstdc++.so.6.0.22':'60857b39f0c34a09a889d937683bd8dae68200b6f10335fe94dee130a770247c',
    DONOR/'fat-files/nflasha3/av-cam.bin':'56684d830eab1e304868548746d8275188a925f9e4ab9354560180c31b4a93cf',
    DONOR/'nflasha15-files/kmod/liro.ko':'8a7cfcaef07ad18ca2a97847d44d31bb9152f57c0fcbccd96056ad683649f2e1',
    DONOR/'fat-files/nflasha8/cpapp-b.bin':'60de0ab5544749dd50d8245f573c0994573fef349186efe20b502c42e3289668',
}

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

class Elf:
    def __init__(self, p):
        self.p, self.d = p, p.read_bytes()
        d = self.d
        if d[:6] != b'\x7fELF\x02\x01': raise ValueError('not ELF64 LE')
        self.machine = struct.unpack_from('<H', d, 18)[0]
        self.ph, self.sh = [], []
        po, pe, pn = struct.unpack_from('<Qxx', d, 32)[0], *struct.unpack_from('<HH', d, 54)
        so = struct.unpack_from('<Q', d, 40)[0]
        se, sn = struct.unpack_from('<HH', d, 58)
        for i in range(pn):
            t, flags, off, va, pa, sz, mem, align = struct.unpack_from('<IIQQQQQQ', d, po+i*pe)
            self.ph.append((t,off,va,sz,mem))
        for i in range(sn):
            name,t,flags,va,off,sz,link,info,align,entsz = struct.unpack_from('<IIQQQQIIQQ', d, so+i*se)
            self.sh.append((t,off,sz,link,entsz))
        self.dynamic = []
        for t,off,va,sz,mem in self.ph:
            if t == 2:
                for j in range(off,off+sz,16):
                    tag,val = struct.unpack_from('<QQ',d,j)
                    if tag == 0: break
                    self.dynamic.append((tag,val))
        tags = {}
        for tag,val in self.dynamic: tags.setdefault(tag,[]).append(val)
        self.tags=tags
        if 5 not in tags: self.needed=[]; self.soname=None; self.imports=[]; self.exports=[]; self.versions=[]; return
        str_off=self.vaoff(tags[5][0]); str_sz=tags[10][0]
        strs=d[str_off:str_off+str_sz]
        def cstr(n):
            if n >= len(strs): raise ValueError('dynstr offset')
            end=strs.find(b'\0',n)
            if end < 0: raise ValueError('dynstr end')
            return strs[n:end].decode('utf-8','replace')
        self.needed=[cstr(v) for v in tags.get(1,[])]
        self.soname=cstr(tags[14][0]) if 14 in tags else None
        self.interp=None
        for t,off,va,sz,mem in self.ph:
            if t == 3: self.interp=d[off:off+sz].rstrip(b'\0').decode()
        self.imports=[]; self.weak_imports=[]; self.exports=[]; self.versions=[]; self.version_definitions=[]
        for t,off,sz,link,entsz in self.sh:
            if t==0x6ffffffd: # GNU verdef
                cursor=off
                while cursor < off+sz:
                    v,fl,ndx,count,h,aux,nxt=struct.unpack_from('<HHHHIII',d,cursor)
                    name,_=struct.unpack_from('<II',d,cursor+aux)
                    self.version_definitions.append(cstr(name))
                    if not nxt: break
                    cursor+=nxt
            if t==0x6ffffffe: # GNU verneed, records and aux chains
                cursor=off
                while cursor < off+sz:
                    v, count, file, aux, nxt=struct.unpack_from('<HHIII',d,cursor)
                    an=cursor+aux
                    for _ in range(count):
                        h,fl,other,name,anext=struct.unpack_from('<IHHII',d,an)
                        self.versions.append({'library':cstr(file),'version':cstr(name)})
                        if not anext: break
                        an += anext
                    if not nxt: break
                    cursor += nxt
            if t==11 and entsz>=24:
                for pos in range(off,off+sz,entsz):
                    name,info,other,ndx,value,size=struct.unpack_from('<IBBHQQ',d,pos)
                    if not name: continue
                    sym=cstr(name)
                    if ndx==0 and info>>4==1: self.imports.append(sym)
                    elif ndx==0 and info>>4==2: self.weak_imports.append(sym)
                    elif ndx and info>>4 in (1,2): self.exports.append(sym)
    def vaoff(self,va):
        for t,off,start,sz,mem in self.ph:
            if t==1 and start<=va<start+sz: return off+va-start
        raise ValueError('unmapped VA '+hex(va))

def index(paths):
    d={}
    for root in paths:
        if not root.exists(): continue
        for p in root.iterdir():
            if p.is_file(): d[p.name]=p
    return d

def main():
    pins={str(p):{'expected':s,'actual':sha(p),'match':sha(p)==s} for p,s in PINS.items()}
    if not all(x['match'] for x in pins.values()): raise SystemExit('pinned source mismatch')
    roots=[FX6/'bin/bootin.elf',FX6/'bin/im.elf',FX6/'lib/appFw.so',FX6/'lib/libmpr.so']
    donor=index([FX6/'lib',FX6_BOOT/'lib'])
    guest=index([FX3/'usr/lib',FX3/'lib'])
    def find(name,idx):
        if name in idx: return idx[name]
        alias={'libc.so.6':'libc-2.25.so','libm.so.6':'libm-2.25.so',
               'libdl.so.2':'libdl-2.25.so','libpthread.so.0':'libpthread-2.25.so',
               'librt.so.1':'librt-2.25.so','ld-linux-aarch64.so.1':'ld-2.25.so'}
        if alias.get(name) in idx: return idx[alias[name]]
        # Extracted FAT images may have lost symlinks.  Suffix match is an
        # explicit inference, recorded separately from exact-name resolution.
        hits=[v for k,v in idx.items() if k.startswith(name+'.')]
        return hits[0] if len(hits)==1 else None
    seen={}; queue=list(roots); missing=[]
    while queue:
        p=queue.pop(0)
        if str(p) in seen: continue
        try: e=Elf(p)
        except Exception as ex:
            seen[str(p)]={'error':str(ex),'sha256':sha(p)}; continue
        row={'sha256':sha(p),'bytes':p.stat().st_size,'machine':e.machine,'interpreter':e.interp,'soname':e.soname,'needed':[],'version_requirements':e.versions,'version_definitions':e.version_definitions,'undefined_strong_count':len(set(e.imports)),'undefined_weak_count':len(set(e.weak_imports)),'export_count':len(set(e.exports))}
        seen[str(p)]=row
        for n in e.needed:
            dp, gp=find(n,donor),find(n,guest)
            binding={'name':n,'fx6':str(dp) if dp else None,'fx3':str(gp) if gp else None,'fx6_sha256':sha(dp) if dp else None,'fx3_sha256':sha(gp) if gp else None,'resolution':'exact' if n in donor or n in guest else 'alias_suffix_or_missing'}
            if dp and gp: binding['same_bytes']=binding['fx6_sha256']==binding['fx3_sha256']
            if dp and gp:
                fe,ge=Elf(dp),Elf(gp)
                binding['fx6_exports_missing_in_fx3_count']=len(set(fe.exports)-set(ge.exports))
                binding['fx6_exports_missing_in_fx3_sample']=sorted(set(fe.exports)-set(ge.exports))[:12]
                binding['fx6_versions_missing_in_fx3']=sorted(set(fe.version_definitions)-set(ge.version_definitions))
                required={v['version'] for v in e.versions if v['library']==n}
                binding['required_versions_missing_in_fx3']=sorted(required-set(ge.version_definitions))
            row['needed'].append(binding)
            if dp: queue.append(dp)
            else: missing.append({'from':str(p),'name':n})
        guest_exports=set()
        for b in row['needed']:
            if b['fx3']: guest_exports.update(Elf(Path(b['fx3'])).exports)
        row['strong_imports_missing_from_fx3_declared_needed']=sorted(set(e.imports)-guest_exports)
    out={'status':'STATIC_ONLY','pins':pins,'roots':[str(p) for p in roots],'sources':{'fx6_library_roots':[str(FX6/'lib'),str(FX6_BOOT/'lib')],'fx3_guest_roots':[str(FX3/'usr/lib'),str(FX3/'lib')]},'files':seen,'missing_fx6':missing}
    im=FX6/'bin/im.elf'; imbytes=im.read_bytes()
    obj=FX3/'usr/lib/libObj.so'
    out['dynamic_path_boundary']={'im_sha256':sha(im),'av_command_file_offset':imbytes.find(b'fn=/system/av-cam.bin load=1 debug=1'),'libobj_path_file_offset':imbytes.find(b'/usr/lib/libObj.so'),'fx6_donor_libobj_present':(FX6/'lib/libObj.so').exists(),'fx3_guest_libobj_path':str(obj),'fx3_guest_libobj_sha256':sha(obj) if obj.exists() else None,'fx3_guest_libobj_needed':Elf(obj).needed if obj.exists() else None}
    cm=json.loads(CPIO_AUDIT.read_text())['members']
    cpio_hashes={v['path']:v['sha256'] for v in cm}
    guest_libraries={}
    for row in seen.values():
        for b in row.get('needed',[]):
            if b['fx3']:
                rel=str(Path(b['fx3']).relative_to(FX3))
                guest_libraries[rel]={'projection_sha256':b['fx3_sha256'],'frozen_cpio_sha256':cpio_hashes.get(rel),'match':cpio_hashes.get(rel)==b['fx3_sha256']}
    out['fx3_cpio_library_crosscheck']=guest_libraries
    if not all(v['match'] for v in guest_libraries.values()): raise SystemExit('FX3 projection differs from frozen CPIO')
    out['loader_boundary']={'interpreter':'/lib/ld-linux-aarch64.so.1','fx3_guest_cpio_entries':[v for v in cm if v['path'] in ('lib/ld-linux-aarch64.so.1','lib/ld-2.25.so')],'fx6_loader_sha256':sha(FX6_BOOT/'lib/ld-2.25.so'),'fx3_loader_sha256':sha(FX3/'lib/ld-2.25.so'),'same_bytes':sha(FX6_BOOT/'lib/ld-2.25.so')==sha(FX3/'lib/ld-2.25.so')}
    out['fx3_guest_missing_direct_fx6_ap_libraries']=[n for n in ('libopus.so.0','libSoundTouch.so.1') if not find(n,guest) and not any(v.startswith('usr/lib/'+n) for v in cpio_hashes)]
    fw=FX6/'lib/appFw.so'; fwbytes=fw.read_bytes()
    resources={}
    for n in ('area_check_data.dat','global.xdb'):
        a,b=FX6/'share/app'/n,FX3/'usr/share/app'/n
        resources[n]={'fx6_path':str(a),'fx6_sha256':sha(a),'fx3_path':str(b),'fx3_sha256':sha(b),'same_bytes':sha(a)==sha(b)}
    out['ap_resource_boundary']={'appfw_sha256':sha(fw),'share_app_path_file_offset':fwbytes.find(b'/usr/share/app/'),'area_check_path_file_offset':fwbytes.find(b'/usr/share/app/area_check_data.dat'),'global_xdb_name_file_offset':fwbytes.find(b'global.xdb'),'resources':resources}
    (HERE/'preflight-receipt.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    paths=[('00-fx3-platform',BASELINE,'retain'),('01-fx3-kernel',FX3_IMAGE,'retain'),('02-fx3-cpio',CPIO,'retain'),('10-fx6-bootin',FX6/'bin/bootin.elf','software-delta-proposal'),('11-fx6-im',FX6/'bin/im.elf','software-delta-proposal'),('12-fx6-libstdc',FX6/'lib/libstdc++.so.6.0.22','dependency-evaluate'),('13-fx6-appfw',FX6/'lib/appFw.so','later-ap-phase'),('14-fx6-libmpr',FX6/'lib/libmpr.so','later-ap-phase'),('20-fx6-liro',DONOR/'nflasha15-files/kmod/liro.ko','later-provider-phase'),('21-fx6-av',DONOR/'fat-files/nflasha3/av-cam.bin','later-av-phase'),('22-fx6-cp',DONOR/'fat-files/nflasha8/cpapp-b.bin','excluded-current-evaluation')]
    manifest={'status':'READ_ONLY_DRAFT_NO_GUEST_EXECUTION','ordering':'observed bootin -> im; remaining order is proposed, not natural runtime proof','entries':[{'step':a,'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size,'policy':policy} for a,p,policy in paths], 'guards':['preserve FX3 kernel/QEMU/DTB/env/CPIO and Backup','no FX6 Backup replacement','no FX6 AV/CP in first stage','do not remove fixed helper checks','stop before unknown hardware/LIRO/AV path; no success fallback']}
    (HERE/'migration-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'files':len(seen),'missing_fx6':len(missing),'roots':[p.name for p in roots]},indent=2))
if __name__=='__main__': main()
