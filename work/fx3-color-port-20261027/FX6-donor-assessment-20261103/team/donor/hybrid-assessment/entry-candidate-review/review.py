#!/usr/bin/env python3
"""Independent, exact-two-entry, read-only audit of the frozen CPIO delta."""
import hashlib
import json
import mmap
import posixpath
import re
import stat
import struct
from pathlib import Path

HERE=Path(__file__).resolve().parent
DONOR=HERE.parents[1]
MAC=HERE.parents[6]
CAND_DIR=DONOR/'hybrid-entry-candidate'
SOURCE=MAC/'work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/vmopt-20261103-try2-long-media-gap-v2/guest.cpio'
CAND=CAND_DIR/'guest-two-entry.cpio'
BASE=MAC/'work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/fx3-platform-frozen-baseline.json'
OLD_GATE_BASE=MAC/'outputs/fx3-vm/share/fx3-original-app-loader-probe.cpio'
DONOR_BIN=DONOR/'nflasha15-files/bin'
PINS={
 'source':'eaef24b2fe9405fb48bc7823069ad16162cd67c46e004ed6660f761fc16d230d',
 'candidate':'ff2f927de24b801d334ce9111fb486fb2af85d24c509ab20c43eda0a69ffdc40',
 'baseline':'854e58f0485537e4644f81daa51d532eea5fa1f5e30887c684e9356e542b9669',
 'builder':'8a54dc4b67c5f9f9584f5b5f2ddbbf8d64bcd7d676393b0baf7eaa53eae4f6b4',
 'manifest':'de1b7cacc595903e01c8db3e927893bc37232949846ae4005818e7ccd513e5d2',
 'old_gate_base':'7d151d8f1e363c66a947724fd65c5b818e8037347c886d8b0f133c970ad1f862',
 'bootin_old':'dab3ce4b6c28a6c9ffd9f0b893dce1d08f3ee7302a09df87e518409e728be2f2',
 'bootin_new':'72480247f8d2a1eeaab076b880c35279c6c94284649e267066f5ea10de6622a6',
 'im_old':'5171f576d8b76cfbf15581389183b390c445bd6ff9dd97fd6668c5f64e77dc91',
 'im_new':'87d672bd6abbcf695c0a773cb096d72d18429e5107846a2f0d3e8add87e400ec',
}
ALLOW={'usr/bin/bootin.elf':('bootin_old','bootin_new',23960),'usr/bin/im.elf':('im_old','im_new',40920)}
def sha_bytes(data):return hashlib.sha256(data).hexdigest()
def sha_file(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def range_hash(mm,start,length):
    h=hashlib.sha256();end=start+length
    for p in range(start,end,1<<20):h.update(mm[p:min(p+(1<<20),end)])
    return h.hexdigest()
def equal_range(a,b,start,length):
    end=start+length;h=hashlib.sha256()
    for p in range(start,end,1<<20):
        x=a[p:min(p+(1<<20),end)];y=b[p:min(p+(1<<20),end)]
        if x!=y:raise ValueError('unexpected byte delta outside allowlist at '+hex(p))
        h.update(x)
    return h.hexdigest()
def parse(mm):
    result={};order=[];p=0;directories={'.'};parent_errors=[]
    while True:
        if p+110>len(mm) or mm[p:p+6]!=b'070701':raise ValueError('newc header at '+hex(p))
        header=mm[p:p+110]
        fields=[int(header[6+i*8:14+i*8],16) for i in range(13)]
        mode,size,namesz=fields[1],fields[6],fields[11]
        if not 0<namesz<4096:raise ValueError('name size')
        nstart=p+110;raw=mm[nstart:nstart+namesz]
        if raw[-1:]!=b'\0':raise ValueError('name terminator')
        name=raw[:-1].decode('utf-8')
        data_off=(nstart+namesz+3)&~3
        if data_off+size>len(mm):raise ValueError('member exceeds archive')
        if name=='TRAILER!!!':return result,order,{'header_offset':p,'end_offset':(data_off+size+3)&~3,'parent_order_errors':parent_errors}
        if name.startswith('/') or '..' in name.split('/') or name in result:raise ValueError('member path/duplicate')
        parent=posixpath.dirname(name) or '.'
        if parent not in directories:parent_errors.append({'name':name,'missing_parent':parent})
        if stat.S_ISDIR(mode):directories.add(name)
        row={'header_offset':p,'data_offset':data_off,'bytes':size,'mode':oct(mode),'sha256':range_hash(mm,data_off,size)}
        result[name]=row;order.append(name);p=(data_off+size+3)&~3

def entry_elf(mm,row):
    off=row['data_offset'];d=mm[off:off+row['bytes']]
    if d[:6]!=b'\x7fELF\x02\x01' or struct.unpack_from('<H',d,18)[0]!=183:raise ValueError('not AArch64 ELF64')
    phoff=struct.unpack_from('<Q',d,32)[0];entsz,num=struct.unpack_from('<HH',d,54)
    ph=[struct.unpack_from('<IIQQQQQQ',d,phoff+i*entsz) for i in range(num)]
    interp=None;tags={}
    load=[]
    for typ,flags,p,va,pa,sz,mem,align in ph:
        if typ==1:load.append({'file_offset':p,'filesz':sz,'vaddr':va,'sha256':sha_bytes(d[p:p+sz])})
        if typ==3:interp=d[p:p+sz].rstrip(b'\0').decode()
        if typ==2:
            for pos in range(p,p+sz,16):
                tag,val=struct.unpack_from('<qQ',d,pos)
                if tag==0:break
                tags.setdefault(tag,[]).append(val)
    def fileoff(va):
        for typ,flags,p,start,pa,sz,mem,align in ph:
            if typ==1 and start<=va<start+sz:return p+va-start
        raise ValueError('dynamic VA outside file')
    string_off=fileoff(tags[5][0]);strings=d[string_off:string_off+tags[10][0]]
    needed=[]
    for i in tags.get(1,[]):
        end=strings.index(b'\0',i);needed.append(strings[i:end].decode())
    shoff=struct.unpack_from('<Q',d,40)[0];shentsz,shnum,shstridx=struct.unpack_from('<HHH',d,58)
    sections=[struct.unpack_from('<IIQQQQIIQQ',d,shoff+i*shentsz) for i in range(shnum)]
    shstr=sections[shstridx];names=d[shstr[4]:shstr[4]+shstr[5]]
    named=[]
    for s in sections:
        start=s[0];end=names.find(b'\0',start)
        named.append({'name':names[start:end].decode('utf-8','replace'),'type':s[1],'file_offset':s[4],'bytes':s[5]})
    return {'sha256':sha_bytes(d),'machine':183,'interpreter':interp,'needed':needed,'load_segments':load,'sections':named}

def main():
    for key,path in [('source',SOURCE),('candidate',CAND),('baseline',BASE),('builder',CAND_DIR/'build.py'),('manifest',CAND_DIR/'manifest.json'),('old_gate_base',OLD_GATE_BASE)]:
        if sha_file(path)!=PINS[key]:raise ValueError('pinned '+key+' SHA changed')
    if CAND.is_symlink():raise ValueError('candidate symlink')
    manifest=json.loads((CAND_DIR/'manifest.json').read_text());baseline=json.loads(BASE.read_text())
    if SOURCE.stat().st_size!=CAND.stat().st_size or CAND.stat().st_size!=453184500:raise ValueError('archive size changed')
    with SOURCE.open('rb') as af,CAND.open('rb') as bf:
        with mmap.mmap(af.fileno(),0,access=mmap.ACCESS_READ) as a,mmap.mmap(bf.fileno(),0,access=mmap.ACCESS_READ) as b:
            old,old_order,old_trailer=parse(a);new,new_order,new_trailer=parse(b)
            if old_order!=new_order or len(old)!=1140 or old_trailer!=new_trailer or old_trailer['parent_order_errors']:raise ValueError('archive order/trailer/parent changed')
            changes=[]
            for name in old_order:
                x,y=old[name],new[name]
                if any(x[k]!=y[k] for k in ('header_offset','data_offset','bytes','mode')):raise ValueError('member metadata changed '+name)
                if x['sha256']!=y['sha256']:
                    if name not in ALLOW:raise ValueError('unallowed changed member '+name)
                    o,n,length=ALLOW[name]
                    if x['sha256']!=PINS[o] or y['sha256']!=PINS[n] or x['bytes']!=length:raise ValueError('bad allowlisted payload '+name)
                    donor=DONOR_BIN/Path(name).name
                    if sha_file(donor)!=PINS[n] or b[y['data_offset']:y['data_offset']+length]!=donor.read_bytes():raise ValueError('not donor original '+name)
                    runs=[];active=None;changed_bytes=0
                    for i in range(length):
                        differs=a[x['data_offset']+i]!=b[y['data_offset']+i]
                        if differs:
                            changed_bytes+=1
                            if active is None:active=i
                        elif active is not None:
                            runs.append({'elf_file_offset':active,'archive_offset':x['data_offset']+active,'bytes':i-active});active=None
                    if active is not None:runs.append({'elf_file_offset':active,'archive_offset':x['data_offset']+active,'bytes':length-active})
                    before_elf,after_elf=entry_elf(a,x),entry_elf(b,y)
                    if before_elf['interpreter']!=after_elf['interpreter'] or before_elf['needed']!=after_elf['needed']:
                        raise ValueError('entry ELF interpreter or DT_NEEDED changed '+name)
                    for run in runs:
                        ro=run['elf_file_offset'];rend=ro+run['bytes']
                        run['sections']=[s['name'] for s in after_elf['sections'] if s['type']!=8 and s['file_offset']<=ro and rend<=s['file_offset']+s['bytes']]
                        run['in_pt_load']=any(s['file_offset']<=ro and rend<=s['file_offset']+s['filesz'] for s in after_elf['load_segments'])
                    changes.append({'name':name,'offset':x['data_offset'],'end_exclusive':x['data_offset']+length,'bytes':length,'bytes_differing_inside':changed_bytes,'differing_runs':runs,'load_segments_equal':before_elf['load_segments']==after_elf['load_segments'],'fx3_sha256':x['sha256'],'fx6_sha256':y['sha256'],'donor_path':str(donor),'entry_elf_before':before_elf,'entry_elf':after_elf})
            if set(x['name'] for x in changes)!=set(ALLOW):raise ValueError('allowlist changed count')
            by_name={x['name']:x for x in changes}
            im_delta=by_name['usr/bin/im.elf'];boot_delta=by_name['usr/bin/bootin.elf']
            if not im_delta['load_segments_equal'] or any(r['in_pt_load'] or '.comment' not in r['sections'] for r in im_delta['differing_runs']):raise ValueError('IM loadable-byte boundary changed')
            if boot_delta['load_segments_equal'] or not any(r['in_pt_load'] and '.text' in r['sections'] for r in boot_delta['differing_runs']):raise ValueError('bootin change not loadable code')
            ranges=[];cursor=0
            for x in sorted(changes,key=lambda v:v['offset']):
                ranges.append({'offset':cursor,'bytes':x['offset']-cursor,'sha256':equal_range(a,b,cursor,x['offset']-cursor)})
                cursor=x['end_exclusive']
            ranges.append({'offset':cursor,'bytes':len(a)-cursor,'sha256':equal_range(a,b,cursor,len(a)-cursor)})
            selected=['init','usr/lib/appFw.so','usr/lib/libObj.so','setting/Backup.bin','usr/kmod/backup.ko','usr/kmod/liro.ko']
            preserved={n:{'sha256':new[n]['sha256'],'bytes':new[n]['bytes'],'unchanged':new[n]==old[n]} for n in selected}
            init=b[new['init']['data_offset']:new['init']['data_offset']+new['init']['bytes']].decode()
            lines=init.splitlines();ap=lines[287]
            preloads=re.search(r'LD_PRELOAD=([^ ]+)',ap).group(1).split(':')
            preload_rows=[]
            for p in preloads:
                n=p.lstrip('/')
                if n not in new or new[n]!=old[n]:raise ValueError('preload changed '+n)
                preload_rows.append({'path':p,'sha256':new[n]['sha256']})
            probe=[]
            for lineno in (202,205,208):
                match=re.search(r'LD_PRELOAD=([^ ]+)',lines[lineno-1])
                probe.append({'line':lineno,'preload_count':len(match.group(1).split(':')),'command':lines[lineno-1].split(match.group(0),1)[1].strip()})
            entry_bound={'init_line_211':lines[210],'bootin_line_288':ap,'probe':probe,'preload_count':len(preloads),'preloads':preload_rows,
                         'fx6_av_present':'system/av-cam.bin' in new,'fx6_cp_present':False}
    # Independent manifest and frozen-platform audit; candidate is data only.
    if manifest['candidate_cpio_sha256']!=PINS['candidate'] or manifest['source_cpio_sha256']!=PINS['source']:raise ValueError('manifest archive pins')
    if manifest['changed_members'] and set(x['name'] for x in manifest['changed_members'])!=set(ALLOW):raise ValueError('manifest allowlist')
    if manifest['model_env']!=baseline['model_env'] or manifest['frozen_platform']!=baseline['platform_parameters'] or manifest['fixed_artifacts']!=baseline['sha256']:raise ValueError('manifest platform mismatch')
    if manifest['fx3_appFw_preserved']!=new['usr/lib/appFw.so'] or manifest['fx3_libObj_preserved']!=new['usr/lib/libObj.so']:raise ValueError('manifest preserved-entry mismatch')
    with OLD_GATE_BASE.open('rb') as oldgate_file:
        with mmap.mmap(oldgate_file.fileno(),0,access=mmap.ACCESS_READ) as original:
            oldgate_members,_,oldgate_trailer=parse(original)
            oldgate_elf={n:x for n,x in oldgate_members.items() if original[x['data_offset']:x['data_offset']+4]==b'\x7fELF'}
            oldgate_changes=[n for n,x in oldgate_elf.items() if n not in new or new[n]['sha256']!=x['sha256']]
            if len(oldgate_elf)!=20 or set(oldgate_changes)!=set(ALLOW) or oldgate_trailer['parent_order_errors']:raise ValueError('old gate deviation unexpected')
    fixed={}
    for key,x in baseline['sha256'].items():
        actual=sha_file(Path(x['path']));fixed[key]={'sha256':actual,'matches_baseline':actual==x['sha256'],'path':x['path']}
        if not fixed[key]['matches_baseline']:raise ValueError('baseline artifact changed '+key)
    out={'status':'PASS_STATIC_TWO_ENTRY_ALLOWLIST_ONLY','source_sha256':PINS['source'],'candidate_sha256':PINS['candidate'],
         'source_and_candidate_bytes':CAND.stat().st_size,'member_count':len(old),'member_order_equal':True,'trailer_equal':True,
         'exact_allowlist':changes,'all_other_bytes_equal':True,'identical_ranges':ranges,'preserved':preserved,
         'effective_entry_delta':{'bootin_pt_load_changed':True,'bootin_text_changed':True,'im_pt_load_equal':True,'im_differences_only_in_nonloaded_comment':True},
         'entry_boundary':entry_bound,'baseline_sha256':PINS['baseline'],'fixed_artifacts':fixed,
         'builder_sha256':PINS['builder'],'builder_manifest_sha256':PINS['manifest'],
         'old_original_elf_gate':{'baseline_cpio_sha256':PINS['old_gate_base'],'original_elf_count':len(oldgate_elf),'changed_or_missing':oldgate_changes,'parent_order_errors':new_trailer['parent_order_errors'],'old_safe_to_unpack_would_be':False},
         'limits':['no guest execution or dynamic loader result','FX3 appFw/libObj/Backup remain in candidate','no FX6 AV or CP added','manifest platform data verified but no QEMU command generated']}
    (HERE/'receipt.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    argv=baseline['fx3_vm_command']
    if len(argv)!=34 or argv[19]!='-serial' or argv[30]!='-device' or argv[32]!='-device' or str(SOURCE) not in argv[31]:raise ValueError('frozen argv shape changed')
    handoff={'status':'PLAN_ONLY_NOT_EXECUTED','requires_runtime_owner_after_mss':True,'candidate_cpio':str(CAND),'candidate_sha256':PINS['candidate'],
        'fixed_baseline_sha256':PINS['baseline'],'exact_member_allowlist':{n:{'fx3_sha256':PINS[o],'fx6_sha256':PINS[v],'bytes':size} for n,(o,v,size) in ALLOW.items()},
        'old_gate_expected':{'original_elf_count':20,'changed_or_missing':oldgate_changes,'safe_to_unpack':False,'do_not_disable_globally':True},
        'isolated_gate':'Require this review.py PASS and original parent-order errors empty; treat only the exact two ELF identity differences as allowed in a separate runner copy, preserving all other audit failures',
        'frozen_argv_indices':{'serial':20,'candidate_initrd_loader':31,'dtb_loader':33,'kernel':29},
        'only_host_path_changes':['argv[20] file:<new unique serial.log path> under owner-allocated run directory','argv[31] loader file path to candidate, same addr=0x440000000 force-raw=on','relative QMP/GDB socket paths resolved in owner-allocated new run directory'],
        'must_match_baseline':['QEMU binary','FX3 kernel argv[29]','full DTB argv[33]','machine/cpu/smp/memory','model_env','remaining argv words','original /init and 17 preload payloads','Backup and all other CPIO members'],
        'budget_host_seconds':180,'input_policy':'no directional keys or synthetic events',
        'observe_in_order':['FX3_TRACE_ABI_VERIFY_RC','FX3_TRACE_ABI_LIST_RC','FX3_TRACE_ABI_TRUE_RC','FX3_TRACE_ABI_NOT_READY if present','FX3_AP_NATURAL_BOOTIN_BEGIN','first actual im.elf process/maps marker','first available FX3_BOOT_QUEUE_SEND with pid/source/raw/caller if naturally emitted; attribute FX3 AP traffic separately'],
        'stop':['first genuine fault, loader nonzero, module/observer refusal, or first bounded IM/IPC evidence','if IPC marker absent by time budget mark unknown; do not synthesize'],
        'cleanup':['use existing owner API16 restore path','stop and reap only own QEMU/runner children','confirm both existing run locks free','store command, hashes, serial, RCs, host/API16/locks in fresh run directory','never overwrite historical serial'],
        'interpretation':['FX3 appFw/libObj remain; menu appearance is not FX6 AP','IM PT_LOAD identical; no new FX6 IM runtime logic proven','no FX6 AV or CP in candidate','static audit is not runtime success']}
    (HERE/'handoff.json').write_text(json.dumps(handoff,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':out['status'],'members':len(old),'changed':[(x['name'],x['offset'],x['end_exclusive'],x['bytes_differing_inside']) for x in changes],
                      'preloads':len(preloads),'source_candidate_same_size':SOURCE.stat().st_size==CAND.stat().st_size},indent=2))
if __name__=='__main__':main()
