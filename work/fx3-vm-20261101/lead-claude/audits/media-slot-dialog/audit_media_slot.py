#!/usr/bin/env python3
"""Rebuild a read-only FX3 media-slot / warning-dialog proof. No emulation."""
import argparse
import hashlib
import io
import json
import re
import struct
import subprocess
import plistlib
import sys
from pathlib import Path
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
from elftools.elf.elffile import ELFFile
sys.dont_write_bytecode = True

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[4]
VM = ROOT / 'work/fx3-vm-20261101/menu-repair-01'
LIB = VM / 'original-uipc/ap-projection/regular-files/usr/lib'
CS = Cs(CS_ARCH_ARM64, CS_MODE_ARM)

def sha(b):
    return hashlib.sha256(b).hexdigest()

class Elf:
    def __init__(self, path):
        self.path = Path(path)
        self.b = self.path.read_bytes()
        self.e = ELFFile(io.BytesIO(self.b))
        sy = self.e.get_section_by_name('.dynsym')
        self.syms = list(sy.iter_symbols()) if sy else []
        self.ptrs = {}
        for sec in self.e.iter_sections():
            if sec['sh_type'] != 'SHT_RELA': continue
            symbols = self.e.get_section(sec['sh_link'])
            for r in sec.iter_relocations():
                s = symbols.get_symbol(r['r_info_sym']) if r['r_info_sym'] else None
                self.ptrs[r['r_offset']] = (s['st_value'] if s else 0) + r['r_addend']
        pl = self.e.get_section_by_name('.plt')
        rel = self.e.get_section_by_name('.rela.plt')
        self.plt = {pl['sh_addr']+32+i*16:sy.get_symbol(r['r_info_sym']).name
                    for i,r in enumerate(rel.iter_relocations())} if rel else {}
    def read(self, va, n):
        s = next(s for s in self.e.iter_segments() if s['p_type']=='PT_LOAD'
                 and s['p_vaddr']<=va and va+n<=s['p_vaddr']+s['p_filesz'])
        o = va-s['p_vaddr']+s['p_offset']
        return self.b[o:o+n]
    def string(self, va):
        return self.read(va, 1).decode(errors='replace') if va==0 else self.read(va, 256).split(b'\0')[0].decode(errors='replace')
    def find(self, needle):
        out=[]
        for s in self.e.iter_segments():
            if s['p_type']!='PT_LOAD': continue
            data=s.data(); start=0
            while (pos:=data.find(needle,start))>=0:
                out.append(s['p_vaddr']+pos);start=pos+1
        return out
    def dis(self,a,n):
        return [{'va':hex(i.address),'bytes':bytes(i.bytes).hex(),
                 'instruction':(i.mnemonic+' '+i.op_str).strip(),
                 **({'symbol':self.plt.get(int(i.op_str[1:],16),'')} if i.mnemonic=='bl' and i.op_str.startswith('#') else {})}
                for i in CS.disasm(self.read(a,n),a)]
    def refs(self, target):
        """Original ADRP+ADD address materializations, plus literal u64 pointers."""
        out=[]
        sec=self.e.get_section_by_name('.text'); data=sec.data(); base=sec['sh_addr']
        for j,(w,) in enumerate(struct.iter_unpack('<I',data[:len(data)//4*4])):
            if w&0x9f000000!=0x90000000:continue
            pc=base+j*4; imm=((w>>29)&3)|(((w>>5)&0x7ffff)<<2)
            if imm&0x100000:imm-=0x200000
            page=(pc&~4095)+(imm<<12)
            if page!=target&~4095: continue
            rd=w&31
            for k in range(j+1,min(j+7,len(data)//4)):
                z=struct.unpack_from('<I',data,k*4)[0]
                if z&0xffc00000==0x91000000 and (z>>5)&31==rd and page+((z>>10)&4095)==target:
                    out.append({'adrp':hex(pc),'add':hex(base+k*4)})
                if z&0xffc00000==0xf9400000 and (z>>5)&31==rd and page+((z>>10)&4095)*8==target:
                    out.append({'adrp':hex(pc),'ldr':hex(base+k*4)})
        return {'code':out,'pointers':[hex(a) for a,v in self.ptrs.items() if v==target]}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='rebuild in memory and compare proof')
    args = parser.parse_args()
    assert ROOT == Path('/Volumes/KAFU2T/AI/Projects/Mac')
    assert OUT == ROOT/'work/fx3-vm-20261101/lead-claude/audits/media-slot-dialog'
    vol = plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
    assert vol['VolumeUUID'].upper() == 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
    pins = {
        'appFw.so':'545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f',
        'libObj.so':'c4681d209a7fe2ed63752be3b0be89ab7b7ce400679c00068c8c6e47d39f83ae',
        'libInfraMediaDetect.so':'4c1dbb303cf9d2d762723e0eb2266309c83aefe7d50f050fc8baa3964e4ea70d',
        'libInfraMediaMount.so':'33b4c61c39f724e08e1bc4d07fd505a799ee37a9c1f37a43fffc7c2c9c8f75ad',
        'libInfraMediaCommon.so':'1ddec7e4d903eaca7cdc7901936b99a9bf97bc52f67259cd3ebb3ee60620b40b',
    }
    aliases = {'app':'appFw.so','obj':'libObj.so','detect':'libInfraMediaDetect.so',
               'mount':'libInfraMediaMount.so','common':'libInfraMediaCommon.so'}
    elfs = {k:Elf(LIB/v) for k,v in aliases.items()}
    proof = {'schema':'fx3-media-slot-dialog-readonly-audit-v1',
        'scope':'Original ELF bytes and frozen AP90-r2/AP91-r2 artifacts only. No QEMU, guest action, original edit, runtime write, or device access.',
        'assessment':'PARTIAL_STATIC_AUDIT: executable empty-slot provider and exact dialog exit predicates remain unproven',
        'sources':{},'blocks':{},'checks':[]}
    def source(key, path, blob=None):
        path=Path(path);blob=path.read_bytes() if blob is None else blob
        proof['sources'][key]={'path':str(path),'bytes':len(blob),'sha256':sha(blob)}
        return blob
    for key,e in elfs.items():
        assert sha(e.b)==pins[aliases[key]], (key,'original SHA changed')
        source(key,e.path,e.b)
    spec = [
        ('input_event_dispatch','obj',0xc8dec,0x164),
        ('input_event_thread','obj',0xc8f50,0x1f8),
        ('app_input_forward','app',0x16f0fc0,0x110),
        ('app_input_registration','app',0x16ef2a0,0xa4),
        ('media_detect_front_callback','detect',0xe6dc,0x218),
        ('media_detect_front_decode','detect',0x1091c,0x668),
        ('media_detect_status','detect',0xf380,0x108),
        ('media_detect_notify','detect',0xd40c,0x184),
        ('media_detect_notify_adapter','detect',0xf8d8,0x54),
        ('media_detect_update','detect',0xfb48,0x204),
        ('media_detect_start','detect',0xf92c,0x128),
        ('media_detect_init','detect',0x1007c,0x314),
        ('media_detect_constructor','detect',0x10390,0x174),
        ('media_detect_rm_sync','detect',0xf1e4,0x154),
        ('media_detect_config','detect',0xfd4c,0xbc),
        ('media_detect_notify_registration','detect',0xfe08,0x7c),
        ('media_detect_timeout_fallback','detect',0xe8f4,0x40c),
        ('media_mount','mount',0x9c98,0x2e0),
        ('common_rm_init','common',0x3c7a8,0x318),
        ('caution_emit','app',0x179bf48,0x60),
        ('caution_slot1_appear_predicate','app',0x1799794,0x134),
        ('caution_slot1_shared_predicate','app',0x178fc3c,0x1c),
        ('caution_slot1_zero_predicate','app',0x1789350,8),
        ('dialog_rtti_vtable_methods','app',0x1c97258,0x68),
        ('dialog_action_gate','app',0x1c9bc78,0x60),
        ('dialog_event_30226_30227','app',0x1c9753c,0x74),
        ('dialog_action_185','app',0x1c975b0,0x60),
        ('dialog_tick','app',0x1c97698,0x3c),
        ('dialog_event_1336e_handler','app',0x1c980fc,0x140),
        ('dialog_event_13372_handler','app',0x1c9828c,0xac),
        ('dialog_bind_1336e_13372','app',0x19f0398,0x160),
        ('model_insert_event_adapter','app',0x2a7a7a4,0xc4),
        ('model_start_inout','app',0x2d0db4c,0x32c),
        ('app_start_inout_request','app',0x2e4d0b0,0x178),
        ('caution_getter1','app',0x293c010,0x50),
        ('caution_getter2','app',0x293c150,0x28),
    ]
    for key,src,a,n in spec:
        e=elfs[src];raw=e.read(a,n)
        proof['blocks'][key]={'source':src,'start':hex(a),'bytes':n,'sha256':sha(raw),'instructions':e.dis(a,n)}
    def check(key,va,asm):
        actual=next(x['instruction'] for x in proof['blocks'][key]['instructions'] if int(x['va'],16)==va)
        assert actual==asm,(key,hex(va),actual,asm)
        proof['checks'].append({'block':key,'va':hex(va),'instruction':asm,'pass':True})
    for row in [
        ('input_event_dispatch',0xc8e2c,'blr x2'),
        ('input_event_thread',0xc9140,'bl #0xc8dec'),
        ('input_event_thread',0xc9124,'ldrb w0, [x22, #0x30]'),
        ('app_input_forward',0x16f10b0,'bl #0x1592f10'),
        ('media_detect_front_decode',0x109bc,'cmp w2, #2'),
        ('media_detect_front_decode',0x10cc0,'strb w1, [x19, #0x268]'),
        ('media_detect_front_decode',0x10cd4,'strb w1, [x19, #0x26a]'),
        ('media_detect_status',0xf3fc,'strb wzr, [x19]'),
        ('media_detect_update',0xfc38,'mov w1, #1'),
        ('media_detect_update',0xfc48,'cbz w0, #0xfcf4'),
        ('media_detect_update',0xfccc,'mov w2, #0'),
        ('media_detect_notify',0xd474,'strb w24, [x29, #0xa0]'),
        ('media_mount',0x9e14,'bl #0x68c0'),
        ('media_mount',0x9e44,'cbnz w0, #0x9e64'),
        ('caution_emit',0x179bf9c,'bl #0x15927c0'),
        ('caution_slot1_appear_predicate',0x17997b4,'cmp w0, #2'),
        ('caution_slot1_appear_predicate',0x17997e0,'cmp w0, #1'),
        ('dialog_action_gate',0x1c9bc98,'ldr x2, [x2, #0x28]'),
        ('dialog_bind_1336e_13372',0x19f03d4,'mov w0, #0x336e'),
    ]:check(*row)
    app=elfs['app'];det=elfs['detect']
    ids={}
    for name,p in [('slot1_auto',0x415e9d0),('slot2_auto',0x415e9e0)]:
        ident,n,_=struct.unpack('<IIQ',app.read(p,16));ptr=app.ptrs[p+8]
        ids[name]={'table_va':hex(p),'id':hex(ident),'length':n,'name_va':hex(ptr),'name':app.string(ptr)}
    assert ids['slot1_auto']['id']=='0x213'
    base=app.ptrs[0x4799170];row=base+0x213*200
    ptrfields={hex(o):hex(app.ptrs.get(row+o,struct.unpack('<Q',app.read(row+o,8))[0])) for o in range(0,200,8)}
    assert row==0x41f66a0 and int(ptrfields['0x10'],16)==0x1799794
    assert struct.unpack('<I',app.read(row+0x2c,4))[0]==0x2c7
    proof['caution_descriptor']={'names':ids,'table_base':hex(base),'record_va':hex(row),'stride':200,
        'raw':app.read(row,200).hex(),'fields_u64':ptrfields,'screen_id_at_2c':'0x2c7',
        'limitation':'Pointer field roles beyond screen id and appearance predicate are not all named. Predicate getter identities and complete exit logic are NOT established.'}
    proof['front_state_fields']={
        'source':'detect+0x109b8..0x10d38; labels at0x128ef..0x12b15',
        'body_minimum_bytes':7,'body_0_type':2,
        'body_3_bits_0_2':'RM1Enable/RM2Enable/RM3Enable',
        'body_4':'RM1 hold bit0; port_state bit1; RemoveCnt bits4..7',
        'body_5':'RM2 same fields','body_6':'RM3 same fields',
        'empty_configured_slot_semantics':'enabled slot with port_state=0; hold=0; preserve original framing and per-slot configuration',
        'unproven':'Destination, full FRONT message header/length/status semantics, CP sender and physical GPIO polarity are not closed; do not inject a naked 7B body.'}
    proof['detect_labels']=[{'va':hex(a),'value':det.string(a)} for a in [0x128ef,0x12921,0x12953,0x12985,0x129b7,0x129e9,0x12a1b,0x12a4d,0x122a1]]
    proof['original_media_event_names']=[]
    for p in [0x4171670,0x4171680,0x4171690,0x41716a0,0x4172600,0x4172610,0x4172620,0x4172630]:
        ident,n=struct.unpack('<II',app.read(p,8));ptr=app.ptrs[p+8]
        proof['original_media_event_names'].append({'va':hex(p),'id':hex(ident),'name':app.string(ptr),'name_va':hex(ptr)})
    proof['media_parameter_registration']=[]
    for p in [0x417eda8,0x417edc0,0x417ee68,0x417ee80,0x417f1e0,0x417f1f8,0x41766f0,0x4176708,0x418f968,0x418f980]:
        typ,ident,n=struct.unpack('<IIQ',app.read(p,16));ptr=app.ptrs[p+16]
        proof['media_parameter_registration'].append({'va':hex(p),'type':typ,'id':hex(ident),'aux':n,'name':app.string(ptr)})
    serial_paths = {'ap90':VM/'runtime/runs/ap90r2parent-f5c66d0b/serial.log',
        'ap91':VM/'runtime/runs/ap91r2keys-9d3939d7/serial.log'}
    proof['serial']={}; app_events=[]
    for label,path in serial_paths.items():
        blob=source(label+'_serial',path); lines=[s.rstrip('\r') for s in blob.decode(errors='replace').split('\n')]
        needles=['Caution [MOUNT_ERR_EXTMEDIA_SLOT1_FOR_AUTO_TRIGGER] appears',
            'open screen:', 'FX3_AP89_SCREEN_OPEN_ENTER','FX3_KEY_INPUT_RECV ',
            'FX3_KEY_INTERNAL_SEND ','FX3_KEY_EVENT_THREAD_RECV ','FX3_SYNTH_KEY_SCRIPT_DONE ',
            'FX3_PROC_MODULES_BEGIN','osal_uipc 77824','osal_utm 16384','devno 12288']
        rx=re.compile(r'FX3_BOOT_QUEUE_SEND .*raw=(?:00000100|01000100|02000100|03000100|ee000300|ef000300|f0000300|f1000300)|FX3_BOOT_QUEUE_SEND .*caller_relative=0x16f10b4')
        picked=[{'line':i,'text':line} for i,line in enumerate(lines,1) if any(n in line for n in needles) or rx.search(line)]
        proof['serial'][label]={'line_count':len(lines),'selected':picked}
        if label=='ap91':
            for item in picked:
                line=item['text']
                if 'FX3_BOOT_QUEUE_SEND ' not in line or 'caller_relative=0x16f10b4 ' not in line:continue
                raw=bytes.fromhex(re.search(r'raw=([0-9a-f]{64})',line).group(1))
                key,packed,status,prev,ex,repeat,from_type,inh=struct.unpack('<8I',raw)
                if key not in (0x1ac,0x1ab,0x30,0x1af):continue
                app_events.append({'line':item['line'],'raw':raw.hex(),'event_code':hex(key),
                    'status':status,'prev_status':prev,'ex_info':ex,'repeat':repeat,'from_type':from_type,'inh':inh&255})
    expected_keys=[0x1ac,0x1ab,0x30,0x30,0x1af,0x1ab]
    assert len(app_events)==12
    assert [int(app_events[i]['event_code'],16) for i in range(0,12,2)]==expected_keys
    assert [x['status'] for x in app_events]==[1,0]*6
    assert all(x['from_type']==1 and x['inh']==0 for x in app_events)
    proof['ap91_application_callback_events']=app_events
    readbacks_path=serial_paths['ap91'].parent/'ap91-step-readbacks.json'
    rb=json.loads(source('ap91_readbacks',readbacks_path))
    assert len(rb)==6
    for item in rb:
        raw=Path(item['raw']).read_bytes();assert sha(raw)==item['raw_sha256']
        source('ap91_step_'+str(item['step']),Path(item['raw']),raw)
    assert len({x['raw_sha256'] for x in rb})==1
    proof['ap91_pixels']={'steps':len(rb),'same_sha256':rb[0]['raw_sha256'],
        'native_sequences':[x['latest_native_committed_sequence'] for x in rb],
        'scope':'Unchanged pixels at six frozen readback times, not proof the UI never redrew.'}
    command=json.loads(source('ap90_command',serial_paths['ap90'].parent/'command.json'))
    assert '-nodefaults' in command['args'] and '-drive' not in command['args'] and '-blockdev' not in command['args']
    proof['ap90_machine_devices']={'args':command['args'],'storage_device_in_args':False,
        'scope':'QEMU command plus frozen module snapshot; no live device probe performed.'}
    init=ROOT/'work/sony-firmware-20261024/stage129-AP-DMM-config-and-device-trial-plan/inputs/insmod_drv2'
    data=source('original_insmod',init).decode()
    proof['original_storage_module_loads']=[{'line':i,'text':s} for i,s in enumerate(data.splitlines(),1) if re.search(r'mcmn_drv|mmc_drv|nvme|ms_drv|sata_drv',s)]
    manifest_path=VM/'original-uipc/ap-projection/full-v5/projection-manifest-full-v5.json'
    manifest=json.loads(source('projection_manifest',manifest_path))
    proof['storage_modules_in_projection']=[]
    for guest,entry in manifest['logical_guest_to_payload'].items():
        if re.search(r'/usr/kmod/(mcmn_drv|mmc_drv|nvme|nvme-core|ms_drv|sata_drv)\.ko$',guest):
            p=Path(entry['payload_file']);b=p.read_bytes()
            proof['storage_modules_in_projection'].append({'guest':guest,'path':str(p),'bytes':len(b),'sha256':sha(b)})
    proof['conclusions']=[
        {'level':'A-runtime + A-static','claim':'AP91 entered the original application input forwarding callback twelve times; no inh suppression on those packets.',
         'evidence':['ap91_application_callback_events','blocks.app_input_forward','blocks.input_event_thread']},
        {'level':'A-static','claim':'Original detection consumes FRONT RMDATA enable/hold/port_state/remove counter separately from media mounting.',
         'evidence':['blocks.media_detect_front_decode','blocks.media_detect_update','blocks.media_mount']},
        {'level':'A-runtime','claim':'AP90 emits media inserted SLOT1/SLOT2 events and mount/unmount completion events before/around the warning; these events lack per-call mount result.',
         'evidence':['serial.ap90','original_media_event_names']},
        {'level':'unproven','claim':'A particular GPIO/MMC register default caused this warning; CP wire sender and exact runtime mount return are not captured.'},
        {'level':'unproven','claim':'Exact keys that dismiss caution0x213 and its complete dynamic close predicate have not been closed.'},
    ]
    proof['recommendation']={'minimum_candidate':'A stateful empty two-slot provider at the original FRONT/RM service boundary, with enabled slots and port_state0, returning original no-card status through original MediaDetect; capture framing and original current result first.',
        'do_not_change':['inh/from_type','callback dispatch','UI predicates','application media parameters','fake mounted media','MMC/GPIO register guesses'],
        'runtime_observation_points':['detect+0xf1e4 entry/return (RM queue 0x80d9016e, full message)','detect+0xe6dc raw FRONT callback + actual source/size',
            'detect+0xf380 out6B; +0xf8d8 status; +0xd40c emitted16B',
            'mount+0x9c98 entry/return; +0x9e14 mcmn_drv_open result and path',
            'app+0x1799794 predicate return; full getter values, caution0x213 descriptor',
            'app+0x16f10b0 send result plus UI queue0x5503e0 dequeue; map/controller/action dispatch',
            'original new screen and framebuffer readback after no-card propagation'],
        'readiness':'NOT an executable packet contract; Lead must close full FRONT/RM framing and caller result before integration.'}
    proof['official_sources']=[
        {'url':'https://helpguide.sony.net/ilc/2035/v1/en/contents/TP1000285248.html','accessed_utc':'2026-11-02','scope':'Sony FX3 guide documents NO CARD memory-card status icon; not proof of 7.02 warning exit behavior.'},
        {'url':'https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000888864.html','accessed_utc':'2026-11-02','scope':'FX3 Ver.2 or later guide for still-image shooting icons; not runtime acceptance.'},
    ]
    payload=(json.dumps(proof,ensure_ascii=False,indent=2)+'\n').encode()
    path=OUT/'media-slot-proof.json'
    if args.check:
        assert path.read_bytes()==payload,'proof differs; rebuild and inspect'
    else:path.write_bytes(payload)
    print(json.dumps({'ok':True,'mode':'check' if args.check else 'rebuild','proof':str(path),
        'sha256':sha(payload),'blocks':len(spec),'instruction_checks':len(proof['checks']),
        'application_callback_events':len(app_events),'assessment':proof['assessment']},ensure_ascii=False))

if __name__ == '__main__':
    main()
