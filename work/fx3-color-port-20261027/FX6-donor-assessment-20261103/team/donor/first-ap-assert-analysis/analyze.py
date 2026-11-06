#!/usr/bin/env python3
"""Read-only, pinned FX6 first-AP-assert proof; no guest execution."""
import hashlib
import json
import re
import struct
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAC = HERE.parents[5]
DONOR = HERE.parent
RUNTIME = MAC / 'work/fx3-vm-20261101/menu-repair-01/runtime'
RUN = DONOR / 'hybrid-ap-candidate/runs/fx6ap-bb7588e5'
FX6 = DONOR / 'nflasha15-files/lib/appFw.so'
FX3 = MAC / 'work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so'
CAP = RUNTIME / 'helpers/fx3-capid-v49-touch100.so'
CAP_SRC = RUNTIME / 'helpers/fx3-capid-v49-touch100.c'
AUDIO_SRC = RUNTIME / 'helpers/fx3-hdmi-audio-format.c'
CAP_CORE = RUNTIME / 'helpers/capid-service.c'
SERIAL = RUN / 'serial.log'
OLD_SERIAL = RUNTIME / 'runs/ap85r4osdring-5dcb8371/serial.log'
CPIO = DONOR / 'hybrid-ap-candidate/guest-three-entry.cpio'
PINS = {
    FX6: 'a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067',
    FX3: '545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f',
    CAP: 'cd51ea7b3347ccb8bd8d0cdd72b096936f0a226c142575f41a24cc018948156e',
    CAP_SRC: '8d65d6907c38e0f6767f7127e74de29e703e927aa0dc0be08deb9081d36bb7e7',
    AUDIO_SRC: '5192b2dcfe37da60e61daf658273623693e28797763570e906ac0fe2767591c6',
    CAP_CORE: '45b787c1e078cc8970d026a913b5294a7a9f2f6f79a14050830e01a00d14f157',
    SERIAL: '7fd297d60c72a1211fa44a0103ae69fabec0c72c422be6c34519c2636db3a43f',
    CPIO: 'bb618bd24f0b504edb14820da4d8204c4b1517cc225e4633eb43f5884f3fff02',
}

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()

def va_offset(data, va):
    assert data[:4] == b'\x7fELF' and data[4] == 2 and data[5] == 1
    phoff = struct.unpack_from('<Q', data, 32)[0]
    entsz, num = struct.unpack_from('<HH', data, 54)
    for i in range(num):
        p = phoff + i * entsz
        typ, flags = struct.unpack_from('<II', data, p)
        off, vaddr, _, filesz, memsz = struct.unpack_from('<QQQQQ', data, p + 8)
        if typ == 1 and vaddr <= va < vaddr + filesz:
            return {'file_offset': off + va - vaddr, 'segment_offset': off,
                    'segment_va': vaddr, 'segment_filesz': filesz, 'segment_memsz': memsz,
                    'flags': flags}
    raise ValueError(f'unmapped file-backed VA {va:#x}')

def dis(path, start, stop):
    out = subprocess.check_output(['xcrun', 'llvm-objdump', '-d',
        f'--start-address={start:#x}', f'--stop-address={stop:#x}', str(path)], text=True)
    return out

def find_lines(raw, marker):
    out=[]; off=0
    for line_no, line in enumerate(raw.splitlines(keepends=True), 1):
        if marker in line:
            out.append({'line':line_no,'range':[off,off+len(line)],
                        'text':line.rstrip(b'\r\n').decode('utf-8','replace')})
        off+=len(line)
    return out

def main():
    hashes = {}
    for path, expected in PINS.items():
        got=sha(path); assert got==expected,(path,got,expected)
        hashes[str(path)] = got
    hashes[str(OLD_SERIAL)] = sha(OLD_SERIAL)
    imgs={k:k.read_bytes() for k in (FX6,FX3,CAP)}
    points={
      'fx6': (FX6,[0x20f15a0,0x20f15b0,0x20f1608,0x20ef79c,0x20ef7a0,0x20ef7b4,0x20ef7b8,0x20ef7c8]),
      'fx3': (FX3,[0x2dedd20,0x2dedd78,0x2de7260,0x2de7264,0x2de72f4]),
      'cap': (CAP,[0x15168,0x1519c,0x151e0,0x151f8,0x15214,0x183a4,0x183d4,0x183f8,0x18400,0x1840c,0x18410,0x1986c,0x1e754,0x1e764,0x1e768,0x245d0]),
    }
    words={}
    for key,(path,vas) in points.items():
        data=imgs[path]; words[key]={}
        for va in vas:
            m=va_offset(data,va);o=m['file_offset'];words[key][f'{va:#x}']={**m,'word_le':data[o:o+4].hex()}
    assert words['fx6']['0x20ef79c']['word_le']=='61aaa897'
    assert words['fx6']['0x20ef7a0']['word_le']=='e0000034'
    assert words['fx6']['0x20ef7b4']['word_le']=='61868052'
    assert words['fx6']['0x20ef7c8']['word_le']=='bea9a897'
    assert words['cap']['0x1e754']['word_le']=='807f8012'
    assert words['cap']['0x1e764']['word_le']=='08c14bb9'
    assert imgs[CAP][0xcf8:0xd04].hex()=='0d202d130c00018000005800'
    excerpts={
       'fx6_sender.txt':dis(FX6,0x20ef720,0x20ef7f0),
       'fx6_request.txt':dis(FX6,0x20f158c,0x20f1624),
       'fx3_sender.txt':dis(FX3,0x2de723c,0x2de7300),
       'fx3_request.txt':dis(FX3,0x2dedd00,0x2dedd94),
       'cap_intercept.txt':dis(CAP,0x18390,0x18420),
       'cap_audio_entry.txt':dis(CAP,0x1e730,0x1e7d0),
       'cap_initialize.txt':dis(CAP,0x24550,0x245dc),
       'cap_return.txt':dis(CAP,0x19838,0x19894),
       'cap_audio_format.txt':dis(CAP,0x15164,0x15224),
    }
    for name,txt in excerpts.items(): (HERE/name).write_text(txt)
    serial=SERIAL.read_bytes(); old=OLD_SERIAL.read_bytes()
    markers={k:find_lines(serial,v) for k,v in {
      'dynamic_qid':b'FX3_GPE104_DYNAMIC_RETURN tid=716',
      'request':b'FX3_PROVIDER_REQUEST destination=0x92840747 bytes=10 source=0x81cf6196',
      'assert':b'assert at infra_wrapper_bb_procam_chaplin_base.cpp:1075',
      'function':b'function:void infra_wrapper_bb::detail::send_and_wait_cmp_i',
      'cap_bind':b'FX3_CAPID_BIND', 'cap_commit':b'FX3_CAPID_COMMIT',
      'audio_commit':b'FX3_HDMI_AUDIO_COMMIT',
      'audio_reject':b'FX3_HDMI_AUDIO_REJECT',
      'native_audio_send':b'FX3_UIPC_SEND_UNIQUE tid=716 target=0x92840747',
      'helper_bound':b'FX3_BOOT_REPLY_BOUND version=31',
    }.items()}
    assert len(markers['request'])==len(markers['assert'])==len(markers['dynamic_qid'])==1
    req=re.search(r'raw=([0-9a-f]+)',markers['request'][0]['text']).group(1)
    assert req=='0d202d030a0001800000'
    old_markers={k:find_lines(old,v) for k,v in {
        'cap_bind':b'FX3_CAPID_BIND', 'cap_commit':b'FX3_CAPID_COMMIT',
        'audio_commit':b'FX3_HDMI_AUDIO_COMMIT',
        'same_request':b'FX3_PROVIDER_REQUEST destination=0x92840747 bytes=10',
    }.items()}
    same_old=[x for x in old_markers['same_request'] if f'raw={req}' in x['text']]
    assert len(old_markers['cap_bind'])==1 and any('op=0x1003' in x['text'] and 'initialized=1' in x['text'] for x in old_markers['cap_commit'])
    assert len(same_old)>0 and len(old_markers['audio_commit'])>0
    init=subprocess.check_output(['bsdtar','-xOf',str(CPIO),'init'])
    init_env={}
    for n in [b'FX3_CAPID_STORAGE',b'FX3_HDMI_AUDIO',b'FX3_VDF_OBSERVE']:
        m=re.search(rb'(?:^|\s)'+n+rb'=([^\s]+)',init)
        init_env[n.decode()]=m.group(1).decode() if m else None
    assert all(init_env.values())
    receipt={
      'schema':'fx6-first-ap-assert-static-v1','hashes':hashes,
      'points':words,'excerpts':{n:sha(HERE/n) for n in excerpts},
      'live_markers':markers,'fx3_reference':{'serial_path':str(OLD_SERIAL),'serial_sha256':hashes[str(OLD_SERIAL)],
            'cap_bind':old_markers['cap_bind'][:1],
            'cap_init_end':[x for x in old_markers['cap_commit'] if 'op=0x1003' in x['text']][:1],
            'same_request':same_old[:1], 'audio_commit':old_markers['audio_commit'][:1]},
      'request':{'hex':req,'bytes':list(bytes.fromhex(req)),'destination':'0x92840747',
                 'source':'0x81cf6196','source_passes_local_mask':(0x81cf6196>>28)==8 and bool(0x81cf6196&0x0fffffff)},
      'expected_helper_reply':{'hex':imgs[CAP][0xcf8:0xd04].hex(),
             'va':'0xcf8','file_offset':'0xcf8','length':12,'only_if_helper_dispatch_succeeds':True},
      'init_sha256':hashlib.sha256(init).hexdigest(),'init_env_values_in_shell':init_env,
      'conclusions':{
        'measured_send_return':'nonzero, exact integer not logged',
        'reply_wait_entered':'no: original cbz branches to osal_rcv_msg_tmo only on zero',
        'request_layout_matches_fx3_audio_core':True,
        'helper_model_initialization_in_this_run':'no CAPID_BIND/COMMIT in complete serial; helper BSS field unobserved directly',
        'conditional_helper_result':'if v49 audio branch taken and model.initialized remains zero, -1021 before any alloc/send/reply',
        'actual_failure_origin':'not directly measured; requires one read-only return-value or state observation',
      }}
    (HERE/'receipt.json').write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'status':'PASS_STATIC','receipt':str(HERE/'receipt.json'),
      'fx6_request':req,'measured_send_return':'nonzero','conditional_helper_return':-1021,
      'fx6_cap_bind_count':len(markers['cap_bind']), 'fx3_init_end_count':len(receipt['fx3_reference']['cap_init_end'])},indent=2))

if __name__=='__main__': main()
