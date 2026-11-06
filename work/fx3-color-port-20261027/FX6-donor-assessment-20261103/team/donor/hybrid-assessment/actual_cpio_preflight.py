#!/usr/bin/env python3
"""Read-only symbol/version check against the frozen 1140-member newc image."""
import hashlib
import importlib.util
import json
import re
import struct
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
DONOR=HERE.parent
MAC=HERE.parents[5]
CPIO=MAC/'work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/vmopt-20261103-try2-long-media-gap-v2/guest.cpio'
CPIO_AUDIT=CPIO.with_name('cpio-audit.json')
COORD=DONOR/'coordinator-hybrid-review/audit.py'
COORD_RECEIPT=COORD.with_name('receipt.json')
FX6=DONOR/'nflasha15-files'
HELP=MAC/'work/fx3-vm-20261101/menu-repair-01/runtime/helpers'
PIN={'cpio':'eaef24b2fe9405fb48bc7823069ad16162cd67c46e004ed6660f761fc16d230d',
     'coord':'9b231574d229f375f99023157a48b344a14a0bc67eae7375b37e5833a8c7ca41',
     'coord_receipt':'367a584d11935cfaaac594be78b424184657b61ea8f18568732d3de91553ee03',
     'cpio_audit':'cc0b3c5b1925aa4bb0cb14aab275f2831833c7378490ca5408789f3824eb4847',
     'bootin':'72480247f8d2a1eeaab076b880c35279c6c94284649e267066f5ea10de6622a6',
     'im':'87d672bd6abbcf695c0a773cb096d72d18429e5107846a2f0d3e8add87e400ec',
     'appFw':'a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067',
     'libmpr':'814dfff34cac6517d71f659fce8d1ead0bb7ee52b8a9ac1a4e25aa9f83ac2d4e'}
def sha(data):return hashlib.sha256(data).hexdigest()
def checked(path,digest):
    d=path.read_bytes()
    if sha(d)!=digest:raise ValueError('SHA mismatch: '+str(path))
    return d

class VElf:
    def __init__(self,data):
        self.data=data
        if data[:6]!=b'\x7fELF\x02\x01' or struct.unpack_from('<H',data,18)[0]!=183:raise ValueError('ELF64 AArch64 required')
        po=struct.unpack_from('<Q',data,32)[0];pe,pn=struct.unpack_from('<HH',data,54)
        so=struct.unpack_from('<Q',data,40)[0];se,sn=struct.unpack_from('<HH',data,58)
        ph=[struct.unpack_from('<IIQQQQQQ',data,po+i*pe) for i in range(pn)]
        sh=[struct.unpack_from('<IIQQQQIIQQ',data,so+i*se) for i in range(sn)]
        def fileoff(va):
            for typ,flags,off,start,pa,sz,ms,al in ph:
                if typ==1 and start<=va<start+sz:return off+va-start
            raise ValueError('unmapped dynstr')
        tags={}
        for typ,flags,off,va,pa,sz,ms,al in ph:
            if typ==2:
                for p in range(off,off+sz,16):
                    tag,val=struct.unpack_from('<qQ',data,p)
                    if tag==0:break
                    tags.setdefault(tag,[]).append(val)
        if 5 not in tags:raise ValueError('no dynamic string table')
        ds=data[fileoff(tags[5][0]):fileoff(tags[5][0])+tags[10][0]]
        def cstr(n):
            end=ds.find(b'\0',n)
            if n<0 or end<0:raise ValueError('bad dynstr index')
            return ds[n:end].decode('utf-8','replace')
        self.needed=[cstr(x) for x in tags.get(1,[])]
        verneed={};verdef={};versym=None;dynsym=None
        for idx,fields in enumerate(sh):
            name,typ,flags,addr,off,size,link,info,align,entsz=fields
            if typ==0x6fffffff:versym=data[off:off+size]
            if typ==11:dynsym=(off,size,entsz)
            if typ==0x6ffffffe:
                pos=off
                while pos<off+size:
                    v,count,lib,aux,nxt=struct.unpack_from('<HHIII',data,pos)
                    q=pos+aux
                    for _ in range(count):
                        h,fl,other,nm,qn=struct.unpack_from('<IHHII',data,q)
                        verneed[other&0x7fff]={'library':cstr(lib),'version':cstr(nm)}
                        if not qn:break
                        q+=qn
                    if not nxt:break
                    pos+=nxt
            if typ==0x6ffffffd:
                pos=off
                while pos<off+size:
                    v,fl,ndx,count,h,aux,nxt=struct.unpack_from('<HHHHIII',data,pos)
                    nm,_=struct.unpack_from('<II',data,pos+aux)
                    verdef[ndx&0x7fff]=cstr(nm)
                    if not nxt:break
                    pos+=nxt
        if not dynsym:raise ValueError('dynsym absent')
        off,size,entsz=dynsym
        self.imports=[];self.exports=[]
        for j,p in enumerate(range(off,off+size,entsz)):
            nm,info,other,ndx,value,sz=struct.unpack_from('<IBBHQQ',data,p)
            if nm==0 or info>>4 not in (1,2):continue
            sym=cstr(nm);vi=struct.unpack_from('<H',versym,j*2)[0] if versym else 1
            index=vi&0x7fff;hidden=bool(vi&0x8000)
            if ndx==0:
                v=verneed.get(index,{})
                self.imports.append({'symbol':sym,'version':v.get('version'),'version_library':v.get('library'),'weak':info>>4==2,'versym_index':index})
            elif other&3 in (0,3):
                self.exports.append({'symbol':sym,'version':verdef.get(index),'hidden_version':hidden,'weak':info>>4==2})

def main():
    checked(COORD,PIN['coord'])
    # The coordinator parser is read as fixed source and executed in-memory;
    # __main__ is not entered and no coordinator file is written.
    env={'__file__':str(COORD),'__name__':'hybrid_cpio_helpers'}
    exec(compile(COORD.read_bytes(),str(COORD),'exec'),env)
    raw=checked(CPIO,PIN['cpio']);members=env['newc'](raw);resolve=env['resolve']
    audit=json.loads(checked(CPIO_AUDIT,PIN['cpio_audit']))
    prior=json.loads(checked(COORD_RECEIPT,PIN['coord_receipt']))
    if len(members)!=len(audit['members']) or any(sha(members[x['path']][1])!=x['sha256'] for x in audit['members']):raise ValueError('CPIO member audit mismatch')
    init=members['init'][1].decode()
    ap_line=next((i,l) for i,l in enumerate(init.splitlines(),1) if '/usr/bin/bootin.elf' in l and 'LD_PRELOAD=' in l)
    preloads=re.search(r'LD_PRELOAD=([^ ]+)',ap_line[1]).group(1).split(':')
    libpath=re.search(r'LD_LIBRARY_PATH=([^ ]+)',ap_line[1]).group(1).split(':')
    cache={}
    def elf(data):
        h=sha(data)
        if h not in cache:cache[h]=VElf(data)
        return cache[h]
    def find(name):
        for directory in libpath:
            path,chain=resolve(members,directory+'/'+name)
            if path:return {'path':path,'chain':chain,'sha256':sha(members[path][1])}
        return None
    preload=[]
    builds={}
    for build in HELP.glob('*-build.json'):
        try:
            meta=json.loads(build.read_text());digest=meta.get('output_sha256')
            if digest and digest not in builds:
                source=next((Path(x) for x in meta.get('args',[]) if isinstance(x,str) and x.endswith('.c') and Path(x).exists()),None)
                if source and sha(source.read_bytes())==meta.get('source_sha256'):
                    builds[digest]={'build_receipt':str(build),'source':str(source),'source_sha256':meta['source_sha256']}
        except (ValueError,OSError,KeyError):pass
    for p in preloads:
        path,chain=resolve(members,p)
        if not path:raise ValueError('preload missing '+p)
        e=elf(members[path][1]);digest=sha(members[path][1]);preload.append({'path':p,'resolved':path,'chain':chain,'sha256':digest,'build_identity':builds.get(digest),'needed':[{'name':n,'binding':find(n)} for n in e.needed]})
    roots={'bootin.elf':checked(FX6/'bin/bootin.elf',PIN['bootin']),
           'im.elf':checked(FX6/'bin/im.elf',PIN['im']),
           'appFw.so':checked(FX6/'lib/appFw.so',PIN['appFw']),
           'libmpr.so':checked(FX6/'lib/libmpr.so',PIN['libmpr'])}
    checks={}
    for root,data in roots.items():
        queue=[(root,data)];nodes={};missing=[]
        while queue:
            path,blob=queue.pop(0)
            if path in nodes:continue
            e=elf(blob);needed=[]
            for n in e.needed:
                hit=find(n);needed.append({'name':n,'binding':hit})
                if hit:queue.append((hit['path'],members[hit['path']][1]))
                else:missing.append({'from':path,'needed':n})
            nodes[path]={'sha256':sha(blob),'needed':needed,'strong_imports':[],'weak_import_count':sum(x['weak'] for x in e.imports)}
        scope={p:elf(roots[root] if p==root else members[p][1]) for p in nodes}
        for item in preload:scope[item['resolved']]=elf(members[item['resolved']][1])
        for path,row in nodes.items():
            e=scope[path]
            for imp in e.imports:
                if imp['weak']:continue
                name,ver,lib=imp['symbol'],imp['version'],imp['version_library']
                candidates=[]
                if ver and lib:
                    b=find(lib)
                    if b:candidates=[b['path']]
                else:candidates=list(scope)
                matches=[];name_only=[]
                for provider in candidates:
                    pe=scope.get(provider)
                    if not pe and provider in members:pe=elf(members[provider][1])
                    if not pe:continue
                    for ex in pe.exports:
                        if ex['symbol']!=name:continue
                        name_only.append(provider)
                        if (ver and ex['version']==ver) or (not ver and not ex['hidden_version']):matches.append(provider)
                if matches:status='MATCHED_SYMBOL_VERSION_STATIC'
                elif ver:status='VERSIONED_STRONG_UNRESOLVED_STATIC'
                else:status='UNVERSIONED_GLOBAL_SCOPE_UNKNOWN'
                row['strong_imports'].append({'symbol':name,'required_version':ver,'required_from':lib,'status':status,'providers':sorted(set(matches)),'name_only':sorted(set(name_only))})
        counts={}
        for row in nodes.values():
            for x in row['strong_imports']:counts[x['status']]=counts.get(x['status'],0)+1
        checks[root]={'nodes':nodes,'missing_paths':missing,'counts':counts}
    im_nodes=checks['im.elf']['nodes']
    conditional=[]
    for x in checks['appFw.so']['nodes']['appFw.so']['strong_imports']:
        if x['status']!='UNVERSIONED_GLOBAL_SCOPE_UNKNOWN':continue
        providers=[]
        for path in im_nodes:
            pe=elf(roots['im.elf'] if path=='im.elf' else members[path][1])
            if any(y['symbol']==x['symbol'] and not y['hidden_version'] for y in pe.exports):providers.append(path)
        if providers:conditional.append({'symbol':x['symbol'],'im_scope_providers':sorted(providers)})
    uipc=find('libosal_uipc.so')
    if not uipc:raise ValueError('actual guest OSAL UIPC absent')
    osal_exports={x['symbol'] for x in elf(members[uipc['path']][1]).exports}
    capid_names=['osal_valloc_msg_wait','osal_free_msg','osal_set_msg_src','osal_snd_msg','osal_msg_size','osal_get_msg_src']
    capid_bind={'provider':uipc,'symbols':{n:n in osal_exports for n in capid_names},'source_sha256':preload[1]['build_identity']['source_sha256'] if preload[1]['build_identity'] else None}
    # Two source-backed helper guards use the original appFw PT_LOAD mapping.
    src=checked(HELP/'fx3-ui-gate-v11.c','bb6650761764f2990650243b9e81ef7f4434c165faef8701afa1033cb961261c').decode()
    offsets=[int(x,16) for x in re.findall(r'0x[0-9a-f]+',re.search(r'const U offsets\[60\]=\{(.*?)\};',src)[1])]
    words=[int(x,16) for x in re.findall(r'0x[0-9a-f]+',re.search(r'const W words\[60\]=\{(.*?)\};',src)[1])]
    fx3=checked(MAC/'work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so','545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f')
    coelf=env['ELF'];a,b=coelf(fx3),coelf(roots['appFw.so'])
    guard=[]
    for i,(va,w) in enumerate(zip(offsets,words)):
        item={'index':i,'relative_va':hex(va),'expected':hex(w)}
        for label,e in [('fx3',a),('fx6',b)]:
            try:off,actual=e.word(va);item[label]={'file_offset':hex(off),'word':hex(actual),'matches':actual==w}
            except ValueError as ex:item[label]={'unmapped':str(ex),'matches':False}
        guard.append(item)
    lines=init.splitlines()
    runner=MAC/'work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/trial_log_v4_mss.py'
    host_runner=runner.with_name('run_trial_v14_final_receipt.py')
    host_source=host_runner.read_text()
    if 'from trial_log_v4_mss import FullLogMonitor' not in host_source or 'if log_monitor.failure:' not in host_source:raise ValueError('host runner monitor edge changed')
    out={'status':'STATIC_ONLY_NO_GUEST_EXECUTION','cpio_sha256':sha(raw),'members_verified':len(members),
         'coordinator_parser_sha256':PIN['coord'],'init_ap_line':ap_line[0],'preload_order':preload,'library_path':libpath,
         'roots':checks,'ui_gate':{'source_sha256':sha(src.encode()),'points':guard,'fx3_matches':sum(x['fx3']['matches'] for x in guard),'fx6_matches':sum(x['fx6']['matches'] for x in guard)},
         'prior_preset_guard':{'guest_sha256':prior['helper']['sha256'],'fx3_matches':prior['helper']['fx3_matches'],'fx6_matches':prior['helper']['fx6_matches'],'first':prior['helper']['guards'][0]},
         'conditional_im_plus_appfw_scope':{'assumption':'only if appFw is dlopened into IM process with IM dependencies visible globally','appfw_unknown_unversioned_root_imports_with_im_provider':conditional},
         'first_functional_preloads':{'skd':{'guest_sha256':preload[0]['sha256'],'source':preload[0]['build_identity']},'capid':{'guest_sha256':preload[1]['sha256'],'bind':capid_bind}},
         'runner_gates':{'init_sha256':sha(members['init'][1]),'init_lines':{str(n):lines[n-1] for n in (202,205,208,211,212,288)},'trial_log_path':str(runner),'trial_log_sha256':sha(runner.read_bytes()),'host_runner_path':str(host_runner),'host_runner_sha256':sha(host_source.encode()),'host_runner_imports_log_monitor':True,'host_runner_stops_on_monitor_failure':True,'preload_probe_count':9,'ap_preload_count':len(preload)},
         'limits':['symbol and version matches are static; no relocation or ABI execution','unversioned symbols may be produced by global plugins or later dlopen','preload interposition and init order are not simulated','no QEMU or guest program run']}
    (HERE/'actual-cpio-receipt.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    base=MAC/'work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/fx3-platform-frozen-baseline.json'
    fx3_image=MAC/'work/sony-firmware-20261024/stage47-runtime-provider-binding/official-files/nflasha3/vmlinux.bin'
    stages=[('fixed-platform','retain',base),('fixed-fx3-image','retain',fx3_image),('fixed-fx3-cpio','retain',CPIO),('fx6-bootin','entry-assessment-only',FX6/'bin/bootin.elf'),('fx6-im','entry-assessment-only',FX6/'bin/im.elf'),('fx6-appfw','later-conditional-assessment',FX6/'lib/appFw.so'),('fx6-libmpr','later-conditional-assessment',FX6/'lib/libmpr.so'),('fx6-av','later-not-loaded',DONOR/'fat-files/nflasha3/av-cam.bin'),('fx6-cp','excluded',DONOR/'fat-files/nflasha8/cpapp-b.bin')]
    manifest={'status':'READ_ONLY_DRAFT_V2_NO_GUEST_EXECUTION','actual_cpio_sha256':sha(raw),'source_order':'FX3 init invokes bootin; donor IM has AV and libObj path; appFw/libmpr order not proven','entries':[{'name':n,'policy':policy,'path':str(p),'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size} for n,policy,p in stages],
              'actual_guest_runtime_dependencies':{n:find(n) for n in ('libopus.so.0','libSoundTouch.so.1','libObj.so','libstdc++.so.6','libc.so.6')},
              'preloads':[{'path':x['path'],'sha256':x['sha256'],'source':x['build_identity']['source'] if x['build_identity'] else None} for x in preload],
              'stop_rules':['do not replace fixed platform/Backup/helper','do not infer ABI from symbol/version match','init line211 triple loader probe failure stops before AP','first original-app guard mismatch is conditional observer refusal, not AP exit','no deployable mixed payload generated']}
    (HERE/'migration-manifest-v2.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'members':len(members),'preloads':len(preload),'roots':{k:{'nodes':len(v['nodes']),'missing_paths':len(v['missing_paths']),'counts':v['counts']} for k,v in checks.items()},'ui_gate_fx3_fx6':[out['ui_gate']['fx3_matches'],out['ui_gate']['fx6_matches']],'conditional_im_scope_count':len(conditional)},indent=2))
if __name__=='__main__':main()
