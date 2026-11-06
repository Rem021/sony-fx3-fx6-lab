#!/usr/bin/env python3
"""Host-only audit of the one consumed window's pre-fault VA evidence."""
import hashlib
import json
import re
import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import readonly_probe as probe
import run_once as runner
from two_phase_identity import choose_early_cap, target_profile

SERIAL=HERE/'runs/ap-ro-f58ad0fb/serial.log'
SERIAL_SHA='19117b7c967fef4220177380beea201f7e3d465a46cecd19761b4d4b37b93688'
INIT_SHA='8ad0be3aec240977060e25ba1193ad80f6ef596ffe47392e3d5b5b79c0ee4a05'
HELPER_SOURCE_SHA='8d65d6907c38e0f6767f7127e74de29e703e927aa0dc0be08deb9081d36bb7e7'

def main():
    assert probe.sha(SERIAL)==SERIAL_SHA
    init=HERE/'init-frozen.sh'
    source=runner.FX3_RUNTIME/'helpers/fx3-capid-v49-touch100.c'
    assert probe.sha(init)==INIT_SHA and probe.sha(source)==HELPER_SOURCE_SHA
    lines=init.read_text().splitlines()
    assert lines[348].strip()=='echo FX3_AP_EARLY_MAPS_${im_pid}_${early}_BEGIN'
    assert lines[349].strip()=='/bin/busybox cat /proc/uptime /proc/$im_pid/maps'
    assert lines[350].strip()=='echo FX3_AP_EARLY_MAPS_${im_pid}_${early}_END'
    assert lines[323].strip()=='echo FX3_AP_IM_ENDMAPS_${im_pid}_BEGIN'
    assert lines[325].strip()=="/bin/busybox grep '/usr/bin/im.elf' /proc/$im_pid/maps"
    assert 'dladdr((void *)row[1],&info)' in source.read_text()
    data=SERIAL.read_bytes()
    request=data.find(b'FX3_PROVIDER_REQUEST destination=0x92840747')
    fault=data.find(b'assert at infra_wrapper_bb_procam_chaplin_base.cpp:1075')
    assert 0<request<fault
    early=[]
    for x in probe.parse_maps(data):
        if x['kind']!='early':continue
        assert x['complete'] and x['pid']==237 and x['byte_end']<request
        cap=probe.map_bias(x['rows'],probe.CAP_PATH,probe.elf_loads(runner.CAP_ELF))
        ap_rows=[r for r in x['rows'] if r['path']==probe.AP_PATH]
        early.append({'epoch':x['epoch'],'pid':x['pid'],'byte_range':[x['byte_start'],x['byte_end']],
                      'first_uptime':x['first_uptime'],'map_rows':len(x['rows']),
                      'cap_rows':len(cap['rows']),'cap_inode':cap['inode'],'cap_bias':hex(cap['bias']),
                      'ap_rows':len(ap_rows)})
    assert [x['epoch'] for x in early]==[1,2,3,4,5]
    assert len({x['cap_bias'] for x in early})==1 and early[0]['cap_bias']=='0x7f816d4000'
    assert all(x['ap_rows']==0 for x in early)
    # The helper's own stack profiler uses dladdr() on return addresses. Its
    # base is strong loader evidence, but not a /proc VMA or target vCPU proof.
    profiles=[];loads=probe.elf_loads(runner.AP_ELF)
    pat=re.compile(rb'FX3_PROFILE_STACK_BEGIN[^\r\n]*')
    for m in pat.finditer(data[:request]):
        end=re.search(rb'FX3_PROFILE_STACK_END[^\r\n]*',data[m.start():request])
        if not end:continue
        span=data[m.start():m.start()+end.end()]
        frames=[]
        for lr,relative in re.findall(rb'FX3_PROFILE_FRAME[^\r\n]*lr=(0x[0-9a-f]+) module=/usr/lib/appFw.so relative=(0x[0-9a-f]+)',span):
            addr=int(lr,16);va=int(relative,16)
            assert any(s['va']<=va<s['va']+s['memsz'] for s in loads)
            frames.append({'lr':hex(addr),'relative':hex(va),'dladdr_base':hex(addr-va)})
        if frames:
            bases={f['dladdr_base'] for f in frames}
            assert len(bases)==1 and int(next(iter(bases)),16)%probe.PAGE==0
            profiles.append({'byte_range':[m.start(),m.start()+end.end()],
                             'marker':m.group().decode(),'frame_count':len(frames),
                             'base':next(iter(bases)),'first_two':frames[:2]})
    assert profiles and profiles[0]['byte_range'][0]<request
    assert len({p['base'] for p in profiles})==1
    assert probe.choose_mapping(data,runner.AP_ELF,runner.CAP_ELF) is None
    cap_stage=choose_early_cap(data[:early[0]['byte_range'][1]],runner.CAP_ELF)
    assert cap_stage and cap_stage['pid']==237 and cap_stage['snapshot_epoch']==1
    native=runner._lineage(data)
    ap_profile=target_profile(data,native,runner.AP_ELF)
    assert ap_profile['bias']==int(profiles[0]['base'],16)
    receipt=json.loads((SERIAL.parent/'receipt.json').read_text())
    assert receipt['probe_stage'] is None and receipt['stop']=='first_health_fault'
    out={'status':'CAP_PHASE1_READY_AP_PHASE2_UNRUN','runtime_run':str(SERIAL.parent),
         'serial_sha256':SERIAL_SHA,'init_member_sha256':INIT_SHA,
         'helper_source_sha256':HELPER_SOURCE_SHA,
         'frozen_cpio_sha256':runner.frozen.PINS['candidate'],
         'init_source_lines':{'endmaps':'323-327: grep only /usr/bin/im.elf',
                              'early_maps':'348-351: pidof im.elf then cat /proc/uptime /proc/$im_pid/maps',
                              'late_maps':'354-369: delayed 10s snapshots; IM_PROCESS appears after fault'},
         'early_snapshots':early,'pre_fault_ap_dladdr_profiles':profiles,
         'request_byte_offset':request,'fault_byte_offset':fault,
         'first_profile_precedes_request_bytes':request-profiles[0]['byte_range'][1],
         'ap_complete_proc_maps_before_request':False,
         'cap_complete_proc_maps_before_request':True,
         'old_strict_two_image_map_gate_ready':False,
         'revised_CAP_phase1_ready_from_first_complete_snapshot':True,
         'revised_AP_phase2_current_vcpu_identity':'not_run',
         'explanation':'AP loads after last early maps; CAP can be armed from its complete PID237 map. Later same-process native dladdr AP base is only a candidate until current stopped vCPU ELF header/PHDR/original words/TLS/frame prove it.',
         'next_minimal_observation':'With a separately allocated VM window, arm CAP Z1 from early original map; on hit validate current CPU images and same-call evidence before any model read; no historical ASLR substitution.'}
    (HERE/'mapping-failure-audit.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({'status':out['status'],'early_epochs':len(early),
                      'profiles':len(profiles),'ap_base':profiles[0]['base']}))

if __name__=='__main__':main()
