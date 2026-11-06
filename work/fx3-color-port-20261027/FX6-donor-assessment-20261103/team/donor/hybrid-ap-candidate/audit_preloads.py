#!/usr/bin/env python3
"""Pin all 17 actual preload payloads and AP write guards. Static only."""
import hashlib
import json
import struct
from pathlib import Path
import verify

HERE=Path(__file__).resolve().parent
MAC=HERE.parents[5]
H=MAC/'work/fx3-vm-20261101/menu-repair-01/runtime/helpers'
R=MAC/'work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime'
G=MAC/'work/fx3-vm-20261101/lead-claude/impl/gpe-perf'
ORIG=MAC/'work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib'
CONTRACT=HERE.parent/'ap-migration-contract/receipt.json'
CONTRACT_SHA='88998c30feb50977b453f4416f2b28b433513eec9d8a9240c9c6d2fa918d914a'
P=[
 ('skd',H/'fx3-skd-hw-unavailable-v1.so',H/'fx3-skd-hw-unavailable-v1.c','functional mmap ENODEV exact /dev/mem site; other calls delegate','5-14'),
 ('capid',H/'fx3-capid-v49-touch100.so',H/'fx3-capid-v49-touch100.c','functional IPC/virtual CAPID; missing native OSAL exits 126; unknown request may fail','40-55,604-705'),
 ('osd_headless',H/'fx3-osd-headless-v7-observe102.so',H/'fx3-osd-headless-v7-observe102.c','software ring/OSD owner; environment and queue gates; no AP text patch found','20,38,69-85'),
 ('osd_lifetime',R/'lifecycle-repair/fx3-osd-lifetime-v3.so',R/'lifecycle-repair/fx3-osd-lifetime-v3.c','OSAL lifetime observer; missing native next returns -1021; no AP text patch found','19-31'),
 ('preset',H/'fx3-preset-context-v6-save102.so',H/'fx3-preset-context-v6-save102.c','AP 48-word preflight before AP text writes; FX6 mismatch point 0','43-47'),
 ('timecode',H/'fx3-timecode-capture-v1.so',H/'fx3-timecode-capture-v1.c','OSAL send observer; no AP text patch found','1-2'),
 ('hdmi',H/'fx3-hdmi-registration-v3.so',H/'fx3-hdmi-registration-v3.c','HDMI software registration; missing native functions exit 126; conditional reply','35-55,68-96'),
 ('gpe',G/'fx3-gpe-observe-v26-perf.so',G/'fx3-gpe-observe-v26-perf.c','AP init patch requires RVA 0x16efb90 and 16-byte prefix; libgpe/libObj patches have own guards; native thread gate may exit 126','42-70,302-323,400-421'),
 ('signal',H/'signal-observe-v2.so',H/'signal-observe-v2.c','signal/abort observer; native lookup failure exits 126','11-19'),
 ('ioctl',H/'ioctl-trace-v12.so',H/'ioctl-trace-v12.c','ioctl/mmap/OSAL trace; unresolved native ioctl or mmap exits 126','140-145,230-235'),
 ('icrypt',H/'fx3-icrypt-observe-v1.so',H/'fx3-icrypt-observe-v1.c','ICrypt and dlopen observer; missing native lookup exits 126','5-19'),
 ('timer',H/'fx3-timer-observe-v3.so',H/'fx3-timer-observe-v3.c','AP and libObj text patch only after four 16-byte prefixes; FX6 AP first prefix mismatch','47-66'),
 ('ui_gate',H/'fx3-ui-gate-v11.so',H/'fx3-ui-gate-v11.c','AP 60-word preflight before AP text writes; FX6 mismatch point 0','103-114'),
 ('infra_crypt',ORIG/'libInfraCrypt.so',None,'original Sony library preloaded; no helper source, AP behavior not proven','n/a'),
 ('backup',H/'fx3-backup-return-v5-save102.so',H/'fx3-backup-return-v5-save102.c','Backup wrappers delegate native; missing next may trap; no AP text patch found','4-9'),
 ('rm',R/'try2-usability/src/fx3-rm-empty-provider-v8-long-use.so',R/'try2-usability/src/fx3-rm-empty-provider-v8-long-use.c','functional synthetic RM queue provider on MediaDetect dlopen; native queue/ABI gates; no AP text patch found','24-30'),
 ('media',R/'try2-usability/src/fx3-media-observe-v4-near-gap.so',R/'try2-usability/src/fx3-media-observe-v4-near-gap.c','AP parameter getter code 10x20-byte guard before sampling, no AP text write; D/M text patches have word preflight','110-130'),
]

def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def elf_offset(raw,va,size):
    assert raw[:4]==b'\x7fELF' and raw[4]==2 and raw[5]==1
    phoff=struct.unpack_from('<Q',raw,32)[0];entsz,n=struct.unpack_from('<HH',raw,54)
    for i in range(n):
        kind,flags,off,vaddr,paddr,filesz,memsz,align=struct.unpack_from('<IIQQQQQQ',raw,phoff+i*entsz)
        if kind==1 and vaddr<=va and va+size<=vaddr+filesz:return off+va-vaddr
    raise ValueError(f'VA {va:#x} not file-backed')

def main():
    assert sha(CONTRACT)==CONTRACT_SHA
    gpe_build=G/'build/cross-build.json'
    assert sha(gpe_build)=='511c5703f3767afb2f0dc2d624829e327d429ce46a2807f0afa8f3fc664e08e5'
    assert json.loads(gpe_build.read_text())['output_sha256']=='30667f76ccfa3f0b9b4834b1fbce725a76683ccd775615ed66955d49200d7ba4'
    listed=json.loads(CONTRACT.read_text())['ld_preload_order']
    members,_=verify.scan(verify.OUT);byname={x['name']:x for x in members}
    assert len(listed)==len(P)==17
    rows=[]
    for i,((tag,binary,source,risk,lines),record) in enumerate(zip(P,listed)):
        assert binary.is_file() and sha(binary)==record['guest_sha256'],(i,binary)
        name=record['path'].lstrip('/');assert name in byname
        assert verify.hash_member(verify.OUT,byname[name])==record['guest_sha256']
        rows.append({'index':i,'guest':record['path'],'guest_sha256':record['guest_sha256'],
                     'matching_local_binary':str(binary),'source':str(source) if source else None,
                     'source_sha256':sha(source) if source else None,
                     'source_lines':lines,'static_binding_risk':risk,
                     'source_to_binary_rebuild_proven':tag=='gpe'})
    raw=verify.AP.read_bytes()
    assert sha(verify.AP)==verify.PINS[verify.AP]
    # Source-backed AP guards; values are checked from the actual FX6 ELF file.
    guards=[]
    for tag,va,expected in [('timer_first_AP_prefix',0x176fb4c,bytes.fromhex('fd7bbaa9fd030091f51300f9f50300aa')),
                            ('media_first_getter',0x293c010,bytes.fromhex('00c7029000e014910004449100f02891c0035fd6'))]:
        off=elf_offset(raw,va,len(expected));actual=raw[off:off+len(expected)]
        assert actual!=expected
        guards.append({'name':tag,'VA':hex(va),'file_offset':hex(off),'expected':expected.hex(),
                       'FX6_actual':actual.hex(),'equal':False})
    assert raw[elf_offset(raw,0x16efb90,16):elf_offset(raw,0x16efb90,16)+16]!=bytes.fromhex('fd7bbaa90382019042c500d0010480d2')
    guards.append({'name':'gpe_AP_init','FX3_expected_RVA':'0x16efb90',
                   'FX6_export_RVA':'0xc0b044','FX6_export_file_offset':hex(elf_offset(raw,0xc0b044,16)),
                   'entry_RVA_equal':False,'text_write_before_guard':False})
    contract_guards=json.loads(CONTRACT.read_text())['guards']
    assert [(x['name'],x['matches']['fx6']) for x in contract_guards]==[('preset48',0),('ui60',2)]
    result={'status':'STATIC_HELPER_AND_FX6_AP_GUARD_AUDIT','candidate_sha256':sha(verify.OUT),
            'contract_receipt_sha256':CONTRACT_SHA,'preloads':rows,'preload_count':len(rows),
            'ap_guard_original_byte_checks':guards,'prior_pinned_guard_reuse':contract_guards,
            'limits':['source to binary rebuild not proven for 16 of 17 entries',
                      'source scan cannot prove all possible computed writes absent',
                      'functional IPC/OSD/RM behavior with FX6 AP unobserved',
                      'no guest or device execution this turn']}
    (HERE/'preload-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'preloads':len(rows),'AP_new_guard_checks':len(guards),
                      'FX6_first_timer_prefix_equal':guards[0]['equal'],
                      'FX6_first_media_getter_equal':guards[1]['equal']},indent=2))

if __name__=='__main__':main()
