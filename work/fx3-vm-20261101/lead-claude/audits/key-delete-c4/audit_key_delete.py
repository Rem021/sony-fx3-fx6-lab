#!/usr/bin/env python3
"""Static FX3 Delete/C4 audit; writes only sibling key-delete-proof.json."""
import argparse
import hashlib
import io
import json
import plistlib
import re
import struct
import subprocess
from pathlib import Path

from capstone import Cs, CS_ARCH_ARM64, CS_ARCH_ARM, CS_MODE_ARM, CS_MODE_THUMB
from elftools.elf.elffile import ELFFile

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[4]
VM = ROOT / 'work/fx3-vm-20261101/menu-repair-01'
LIB = VM / 'original-uipc/ap-projection/regular-files/usr/lib'
UUID = 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'


def sha(b):
    return hashlib.sha256(b).hexdigest()


class Elf:
    def __init__(self, path):
        self.path = path
        self.b = path.read_bytes()
        self.e = ELFFile(io.BytesIO(self.b))
        self.reloc = {r['r_offset']: r['r_addend']
                      for s in self.e.iter_sections() if s['sh_type'] == 'SHT_RELA'
                      for r in s.iter_relocations()}

    def read(self, va, size):
        s = next(s for s in self.e.iter_segments()
                 if s['p_type'] == 'PT_LOAD' and s['p_vaddr'] <= va
                 and va + size <= s['p_vaddr'] + s['p_filesz'])
        off = va - s['p_vaddr'] + s['p_offset']
        return self.b[off:off+size]

    def va(self, off):
        s = next(s for s in self.e.iter_segments()
                 if s['p_type'] == 'PT_LOAD' and s['p_offset'] <= off
                 < s['p_offset'] + s['p_filesz'])
        return off-s['p_offset']+s['p_vaddr']

    def string(self, va):
        return self.read(va, 300).split(b'\0')[0].decode(errors='replace')

    def dis(self, va, n):
        return [(hex(i.address), (i.mnemonic+' '+i.op_str).strip())
                for i in Cs(CS_ARCH_ARM64, CS_MODE_ARM).disasm(self.read(va,n),va)]

    def ptr(self, va):
        return self.reloc.get(va, struct.unpack('<Q', self.read(va,8))[0])


def backup_property(data, base, ident):
    """Read original BK4 index and verify the complete record checksum."""
    magic, cookie, dirty, rev, ns, np, start, size, checksum = struct.unpack_from('<III4s5I', data, base)
    assert rev == b'BK4\0'
    end = base+start+size
    assert end <= len(data)
    assert sum(data[base:base+32])+sum(data[base+36:end]) == checksum
    cnt, idx = struct.unpack_from('<HI', data, base+256+(ident >> 16)*6)
    assert (ident & 65535) < cnt and idx+cnt <= np
    prop = base+256+ns*6+(idx+(ident & 65535))*6
    attr, ptr = struct.unpack_from('<HI', data, prop)
    assert ptr != 0xffffffff
    n, off = ptr >> 24, ptr & 0xffffff
    if n == 255:
        n = struct.unpack_from('<H', data, base+off)[0]
        off += 2
    elif n == 0:
        n, maximum = struct.unpack_from('<HH', data, base+off)
        assert n <= maximum
        off += 4
    assert start <= off and off+n <= start+size
    return data[base+off:base+off+n], {
        'id': hex(ident), 'record_base': hex(base), 'property_table_file_offset': hex(prop),
        'file_offset': hex(base+off), 'bytes': n, 'sha256': sha(data[base+off:base+off+n]),
        'record_checksum_matches': True,
    }, (end+4095) & ~4095


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='rebuild and compare; write nothing')
    args = parser.parse_args()
    volume = subprocess.run(['diskutil', 'info', '-plist', '/Volumes/KAFU2T'],
                            check=True, capture_output=True).stdout
    assert plistlib.loads(volume)['VolumeUUID'].upper() == UUID
    assert ROOT == Path('/Volumes/KAFU2T/AI/Projects/Mac')
    assert OUT == ROOT/'work/fx3-vm-20261101/lead-claude/audits/key-delete-c4'
    paths = {
        'app': LIB/'appFw.so', 'obj': LIB/'libObj.so',
        'input': VM/'original-uipc/ap-projection/full-v4/payloads/d9fcf59b62f9960878f5ea433d350112f4a03fb9c6cd9d30154fb3e3ff54a057',
        'cp': ROOT/'work/sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin',
        'seed': VM/'original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin',
        'seed_provenance': VM/'original-uipc/original-service-seed-provenance.json',
        'prior_proof': OUT.parent/'key-input/key-input-proof.json',
        'prior_readme': OUT.parent/'key-input/README.md',
        'common_context': OUT.parents[1]/'COMMON-CONTEXT.md',
        'serial': VM/'runtime/runs/ap94r4object-37305ab2/serial.log',
        'run_review': VM/'runtime/ap94r4object-37305ab2-review.json',
        'phone_page_step3': VM/'runtime/runs/ap94r4object-37305ab2/ap93-step-03-key-1ac.png',
        'phone_page_step6': VM/'runtime/runs/ap94r4object-37305ab2/ap93-step-06-key-1ab.png',
    }
    blobs = {k: p.read_bytes() for k,p in paths.items()}
    pins = {
        'app': '545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f',
        'obj': 'c4681d209a7fe2ed63752be3b0be89ab7b7ce400679c00068c8c6e47d39f83ae',
        'input': 'd9fcf59b62f9960878f5ea433d350112f4a03fb9c6cd9d30154fb3e3ff54a057',
        'cp': 'c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba',
        'seed': 'bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2',
    }
    for k,h in pins.items():
        assert sha(blobs[k]) == h, (k, 'original changed')
    app, obj, inp = [Elf(paths[k]) for k in ('app','obj','input')]
    elves = {'app':app, 'obj':obj, 'input':inp}
    proof = {
        'schema': 'fx3-key-delete-c4-static-audit-v1',
        'scope': 'Static original ELF/CP/template analysis and frozen AP94 evidence; no QEMU, injection, guest command or original mutation.',
        'sources': {k:{'path':str(p),'bytes':len(blobs[k]),'sha256':sha(blobs[k])} for k,p in paths.items()},
        'blocks': {}, 'checks': [],
    }
    cs = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
    thumb = Cs(CS_ARCH_ARM, CS_MODE_THUMB)

    def block(key, source, va, n, section=None):
        if source == 'cp':
            raw = blobs[source][va-0x108000:va-0x108000+n]
        elif section:
            raw = elves[source].e.get_section_by_name(section).data()[va:va+n]
        else:
            raw = elves[source].read(va,n)
        md = thumb if source == 'cp' else cs
        ins = [{'va':hex(i.address),'bytes':bytes(i.bytes).hex(),
                'instruction':(i.mnemonic+' '+i.op_str).strip()} for i in md.disasm(raw,va)]
        proof['blocks'][key] = {'source':source,'section':section,'start':hex(va),
                                'bytes':n,'sha256':sha(raw),'instructions':ins}
        return {int(i['va'],16):i['instruction'] for i in ins}

    # Read the entire prior proof and independently rebuild every original code block.
    prior = json.loads(blobs['prior_proof'])
    old_checks = 0
    for key,b in prior['blocks'].items():
        va,n = int(b['start'],16),b['bytes']
        block('prior_'+key,b['source'],va,n,b['section'])
        assert proof['blocks']['prior_'+key] == b, key
        old_checks += len(b['instructions'])
    for sn,rows in prior['input_relocations'].items():
        sy = inp.e.get_section_by_name('.symtab')
        rebuilt = []
        for r in inp.e.get_section_by_name(sn).iter_relocations():
            sym = sy.get_symbol(r['r_info_sym'])
            rebuilt.append({'offset':hex(r['r_offset']),'symbol':sym.name,
                            'symbol_section':sym['st_shndx'],'addend':hex(r['r_addend']),
                            'type':r['r_info_type']})
        assert rebuilt == rows, sn
    proof['prior_audit_revalidation'] = {'json_read_completely':True,
        'code_blocks_rebuilt':len(prior['blocks']),'instructions_compared':old_checks,
        'module_relocations_compared':sum(map(len,prior['input_relocations'].values())),
        'full_projection_scan_not_repeated':True}

    names = {}
    for m in re.finditer(rb'UIBIZ_KEY_[A-Z0-9_]+\0', app.b):
        names[app.va(m.start())] = m.group()[:-1].decode()
    enums = {}
    for p,t in app.reloc.items():
        if t not in names:
            continue
        val,length = struct.unpack('<II',app.read(p-8,8))
        if length != len(names[t])+1:
            continue
        enums[names[t]] = {'ui_code':hex(val),'name_va':hex(t),'enum_record_va':hex(p-8)}
    requested = {
        'DELETE_C4':('TACT_DELETE',0x23,0x1f8),
        'C1':('TACT_CUSTOM',0xe,0x66),
        'C2':('TACT_CUSTOM2',0xdf,0x70e7),
        'C3':('TACT_CUSTOM3',0xe4,0x70ec),
        'PLAY':('TACT_PLAY',0x22,0x1f7),
        'FN':('TACT_FN',0x8d,0x7095),
    }
    pairs = list(struct.iter_unpack('<II',app.read(0x2f8f8d8,0x22d0)))
    keys = {}
    for label,(suffix,ui,code) in requested.items():
        name = 'UIBIZ_KEY_'+suffix
        row = dict(enums[name])
        assert int(row['ui_code'],16) == ui
        matches = [(i,y) for i,(x,y) in enumerate(pairs) if x == ui]
        assert len(matches) == 1 and matches[0][1] == code
        i,_ = matches[0]
        row.update(name=name,infra_code=hex(code),map_va=hex(0x2f8f8d8+i*8),
                   map_raw8=app.read(0x2f8f8d8+i*8,8).hex(),
                   down20=struct.pack('<5I',code,0,1,0,1).hex(),
                   up20=struct.pack('<5I',code,0,0,0,1).hex())
        keys[label] = row
    assert not any(n in enums for n in ['UIBIZ_KEY_TACT_CUSTOM4','UIBIZ_KEY_TACT_C4'])
    proof['keys'] = keys
    proof['c4_identity'] = {
        'same_physical_button_as_delete':'Confirmed by Sony FX3 rear-side manual; no new independent C4 scan code inferred.',
        'absent_exact_enum_names':['UIBIZ_KEY_TACT_CUSTOM4','UIBIZ_KEY_TACT_C4'],
        'all_matching_custom_enum_names':sorted(n for n in enums if 'CUSTOM' in n),
        'name_table_records_scanned':len(enums),
        'name_record_va_min':hex(min(int(r['enum_record_va'],16) for r in enums.values())),
        'name_record_va_max':hex(max(int(r['enum_record_va'],16) for r in enums.values())),
    }
    codes = {r[2] for r in requested.values()}
    callback_rows = []
    for i,r in enumerate(struct.iter_unpack('<III',app.read(0x2f96460,1086*12))):
        if r[0] in codes:
            assert r[0] == r[1] and r[2] == 0x7ffffffe
            callback_rows.append({'va':hex(0x2f96460+i*12),'key':hex(r[0]),
                                  'event':hex(r[1]),'filter_status':hex(r[2])})
    assert len(callback_rows) == 6
    proof['app_registered_input_keys'] = callback_rows

    logical,meta,nextrec = backup_property(blobs['seed'],0,0x7a0001)
    assert struct.unpack_from('<4I',logical) == (0x214e4942,0xd080,2,0xd080)
    fields = ['keyName','infraName','keyCode','localCode','priority','repeat_time0_ms',
              'repeat_time_ms','group','flag','osalId','dummy1','dummy2']
    selected = []
    for at in range(16,16+0xd080,48):
        vals = struct.unpack_from('<12I',logical,at)
        if vals[2] in codes:
            assert vals[0] == 0x2159454b and vals[1] == 1 and vals[3] == 0 and vals[9] == 0x410025
            selected.append({'file_offset':hex(int(meta['file_offset'],16)+at),
                             'raw48':logical[at:at+48].hex(),**dict(zip(fields,vals))})
    assert len(selected) == 6
    proof['libobj_consumed_logical_key_table'] = {'property':meta,'row_bytes':48,'rows':1112,'selected':selected,
        'consumer':'libObj+0xcd904 reads property; +0xcd4bc selects BIN type2, stride48; +0xc9bb4 searches row+8 key.',
        'TACT_DELETE_ascii_present_in_libObj':b'TACT_DELETE' in obj.b}
    assert not proof['libobj_consumed_logical_key_table']['TACT_DELETE_ascii_present_in_libObj']
    hardware = []
    for seq,base in enumerate([0,nextrec]):
        raw,meta,_ = backup_property(blobs['seed'],base,0x1120000)
        count,length = struct.unpack_from('<II',raw,16)
        assert count == 1 and length % 64 == 0
        rows = []
        for at in range(24,24+length,64):
            v = struct.unpack_from('<16I',raw,at)
            if v[9] in codes:
                assert v[10:12] == (1,0)
                rows.append({'file_offset':hex(int(meta['file_offset'],16)+at),'raw64':raw[at:at+64].hex(),
                    'u32':list(v),'key':hex(v[9]),'category':prior['hardware_categories'][str(v[1])],
                    'unit_or_bank':hex(v[2]),'channel_or_bit':v[3],'active_level':v[4],
                    'on_value':v[10],'ex_info':v[11]})
        hardware.append({'record':seq,'property':meta,'total_rows':length//64,'selected':rows})
    assert len(hardware[0]['selected']) == 1 and hardware[0]['selected'][0]['key'] == '0x70ec'
    assert {r['key'] for r in hardware[1]['selected']} == {'0x66','0x70e7','0x1f8','0x1f7','0x7095'}
    proof['template_hardware_keys'] = hardware
    prov = json.loads(blobs['seed_provenance'])['records'][0]
    assert prov['sha256'] == sha(blobs['seed'])
    proof['template_provenance'] = {k:prov[k] for k in ['source_fdat','source_fdat_sha256','tar_member','absolute_data_offset','sha256','bytes']}

    decoded = {}
    for key,src,va,n in [
        ('ui_event_lookup','app',0x16ec0c4,0x60),
        ('ui_event_emit','app',0x16ec14c,0x1c8),
        ('setup_action_bindings','app',0x1c3bf48,0x90),
        ('setup_phone_action_candidate_a','app',0x23cce8c,0x88),
        ('setup_camera_action_candidate','app',0x23cd1d0,0xa0),
        ('setup_phone_action_candidate','app',0x23ccf14,0xac),
        ('setup_screen_open','app',0x23ccd00,0x160),
    ]:
        decoded[key] = block(key,src,va,n)
    # Original key-to-UI-event rows: key, press, repeat, release.
    assert app.ptr(0x479c560) == 0x47cd6e8
    event_table = []
    for at in range(0x47cd6e8,0x47cd6e8+0x100,16):
        key,press,repeat,release = struct.unpack('<4I',app.read(at,16))
        if key in [0x23,0x22,0x8d,0x13,0x14]:
            event_table.append({'va':hex(at),'ui_key':hex(key),'press':hex(press),
                                'repeat':hex(repeat),'release':hex(release),'raw16':app.read(at,16).hex()})
    delete = next(r for r in event_table if r['ui_key']=='0x23')
    assert (delete['press'],delete['repeat'],delete['release']) == ('0x90000','0x5','0x90001')
    proof['ui_key_to_event_table'] = {'got_va':'0x479c560','table_va':'0x47cd6e8','stride':16,'selected':event_table}
    event_names = {}
    for at in [0x416c760,0x416c770]:
        val,length = struct.unpack('<II',app.read(at,8))
        nameva = app.ptr(at+8)
        text = app.string(nameva)
        assert length == len(text)+1
        event_names[hex(val)] = {'enum_record_va':hex(at),'name_va':hex(nameva),'name':text}
    assert event_names['0x90000']['name']=='EVENT_INPUT_TACT_DELETE_ON'
    proof['delete_event_names'] = event_names
    assert struct.unpack('<II',app.read(0x3c8c1fc,8)) == (0x90000,0x18e)
    assert struct.unpack('<II',app.read(0x4159790,8)) == (0x18e,13)
    assert app.string(app.ptr(0x4159798)) == 'scr0103_0023'
    screen_rows = []
    for at in range(0x3c8c1bc,0x3c8c3a4,8):
        event,screen = struct.unpack('<II',app.read(at,8))
        if screen == 0x18e:
            screen_rows.append({'va':hex(at),'event':hex(event),'screen':hex(screen)})
    proof['setup_screen'] = {'screen_name':'scr0103_0023','screen_id':'0x18e',
        'screen_name_record_va':'0x4159790','screen_name_va':'0x31013f7',
        'event_screen_raw_pair_va':'0x3c8c1fc','event_screen_pairs':screen_rows,
        'pair_semantics_limit':'Raw original event/screen pairs confirmed; this pair alone is not an event-to-action dispatch proof.',
        'controller_typeinfo_va':'0x45819f8','controller_name_va':'0x313d850',
        'action_candidate':{'action_id':'0x922b','binding_va':'0x1c3bfc4','got_va':'0x4757f58',
            'handler_va':'0x23cd1d0','next_screen':'0x178','next_screen_name':'scr0103_0009',
            'limit':'Handler/action-id binding is proven; DELETE_ON to this action-id is NOT closed.'}}
    assert app.ptr(0x4740a50) == 0x23cce8c
    assert app.ptr(0x4757f58) == 0x23cd1d0
    assert struct.unpack('<II',app.read(0x4159630,8)) == (0x178,13)
    assert app.string(app.ptr(0x4159638)) == 'scr0103_0009'

    def expect(key,va,text):
        assert decoded[key][va] == text,(key,hex(va),decoded[key].get(va),text)
        proof['checks'].append({'block':key,'va':hex(va),'instruction':text,'pass':True})

    for row in [
        ('ui_event_emit',0x16ec294,'add x0, x1, x0, lsl #4'),
        ('ui_event_emit',0x16ec298,'ldr w0, [x0, #4]'),
        ('ui_event_emit',0x16ec2e0,'ldr w0, [x0, #8]'),
        ('ui_event_emit',0x16ec30c,'ldr w0, [x0, #0xc]'),
        ('setup_action_bindings',0x1c3bfb8,'mov w0, #0x922b'),
        ('setup_camera_action_candidate',0x23cd1d4,'mov w1, #0x178'),
        ('setup_camera_action_candidate',0x23cd208,'bl #0x23ccd00'),
        ('setup_phone_action_candidate_a',0x23ccebc,'mov w0, #0x18b'),
        ('setup_phone_action_candidate_a',0x23ccf0c,'mov w0, #0x1cd'),
    ]:
        expect(*row)
    proof['transport_contract'] = {
        'dst':'0x807a0020','src':'0x00410025','body_bytes':20,
        'fields_u32_le':['key_code','sub_key_code','status','ex_info','from_type'],
        'pressed_status':1,'released_status':0,'sub_key_code':0,'ex_info':0,'from_type':1,
        'boundary':'Original OSAL hidden metadata is outside the 20B body; do not add a VDF header or use destination as source.',
        'repeat_note':'All six selected template rows enable repeat; DELETE/C1/C2/C3/FN 800ms/100ms, PLAY 1000ms/200ms. The proof constructs a down/up pair only; no timing or runtime action is validated.',
    }
    review = json.loads(blobs['run_review'])
    serial = blobs['serial'].decode(errors='replace').split('\n')
    proof['existing_ap94_evidence'] = {
        'scope':'Existing frozen software-rendered AP94 artifacts only; this audit started no VM.',
        'screen_open_lines':[{'LF_line':i+1,'text':s.rstrip('\r')} for i,s in enumerate(serial) if 'open screen:' in s],
        'review_screen_records':review['screen_records'],
        'screenshot_observation':'Visually inspected step6 PNG: trash icon then Set on the camera; top text says initial camera settings with smartphone / Creators App.',
        'delete_event_action_tested_here':False,
    }
    proof['official_references'] = [
        {'url':'https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000886869.html',
         'access_date':'2026-11-02','claim':'FX3 Ver.2+ rear side: same 4/custom-button-4 and Delete control; Fn and Playback identified.'},
        {'url':'https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000888870.html',
         'access_date':'2026-11-02','claim':'Initial setup supports smartphone from firmware3+, privacy notice7+, and camera area/date/time setup without smartphone; no private numeric key codes supplied.'},
    ]
    proof['unproven'] = [
        'No QEMU execution, down/up delivery, input consumption, DELETE-driven next frame, completed initial setup or camera acceptance in this audit.',
        'DELETE_ON=0x90000 to setup action0x922b (or another action) is not fully closed; raw event/screen pair, action-handler binding and screenshot support different links only.',
        'Exact localization-resource text/icon identifier to action-id binding was not located; Set on the camera is a visual observation of the frozen PNG, not an ASCII appFw string.',
        'Public defaults do not establish active-VM record selection, current camera settings, PCB wiring or CP/SysCon interrupt/frame behavior.',
        'No separate TACT_CUSTOM4 enum was found; this does not prove that all possible C4/custom-function names are absent.',
        'C1/C2/C3 names are firmware custom-key logical names; do not equate record0/record1 GPIO tuples or numeric body legends without model-specific routing proof.',
    ]
    encoded = json.dumps(proof,ensure_ascii=False,indent=2)+'\n'
    target = OUT/'key-delete-proof.json'
    if args.check:
        assert target.read_text() == encoded, 'proof differs from original-byte reconstruction'
        print('PASS: deterministic proof matches; no file written')
    else:
        target.write_text(encoded)
        print('PASS: rebuilt '+str(target))
    print('6 keys; 12 exact 20B bodies; %d prior instructions and %d relocations revalidated' %
          (old_checks,proof['prior_audit_revalidation']['module_relocations_compared']))


if __name__ == '__main__':
    main()

