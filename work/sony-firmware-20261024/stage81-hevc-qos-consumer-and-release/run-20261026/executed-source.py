#!/usr/bin/env python3
"""Original HEVC GOP target consumer and independent release-mask scopes.

Stage80 outputs are replayed as declared RAM inputs, not physical snapshots.
Only the target fragment executes; stop before unrelated HEVC fields. No real
allocation, GP state, full GOP callback or hardware completion is synthesized.
"""
from pathlib import Path
import argparse
import datetime
import json
import struct
import sys
import traceback

STAGE = Path(__file__).resolve().parent
BASE, ROOT = STAGE.parent, STAGE.parent.parents[1]
sys.path.insert(0,str(BASE/'stage80-vcd-pending-and-timing'))
import pending_timing as p
im, u, reg, IMAGE = p.im, p.u, p.reg, p.IMAGE
GOP_PA, GOP = 0x01200000, 0x81200000
BACKEND = p.CTX+0x108


class Guest(p.Guest):
    def __init__(self,blob,source):
        super().__init__(blob,bytes.fromhex(source['source_prefix64_hex']),source['seed'],True)
        self.uc.mem_write(p.CTX_PA,bytes.fromhex(source['context_after_hex']))
        self.uc.mem_write(p.OUTPUT_PA,bytes.fromhex(source['output4096_hex']))
        self.uc.mem_map(GOP_PA,4096,u.UC_PROT_READ|u.UC_PROT_WRITE)
        body=bytearray([source['seed']])*4096
        struct.pack_into('<I',body,0xc8,((16000000//64)-1)<<8)
        self.uc.mem_write(GOP_PA,bytes(body))

    def code(self,uc,pc,size,user):
        self.pcs.append(pc)
        if len(self.pcs)>20000:return self.stop('boundary: instruction_limit')
        if pc==p.STOP:return self.stop('returned')
        limits={0xd9214:'before_other_HEVC_updates',0xd9470:'after_target_before_other_fields',
                0x1a0d30:'before_unknown_GP_release_state'}
        if pc-IMAGE in limits:return self.stop('boundary: '+limits[pc-IMAGE])
        off=pc-IMAGE
        assert any(a<=off and off+size<=z for a,z in (
            (0xd9204,0xd9214),(0xd9454,0xd94cc),
            (0x19bd44,0x19bda4),(0x19bfd8,0x19c000),
            (0x1a07e4,0x1a085c),(0x1a0a64,0x1a0a8c),
            (0x1a0cfc,0x1a0df8)))
        instruction=next(self.md.disasm(self.blob[off:off+size],pc),None)
        assert instruction is not None and instruction.mnemonic not in {
            'syscall','break','cache','sync','mfc0','mtc0','eret','wait','tlbwi','tlbwr','tlbr','tlbp'}

    def start(self,label,entry,**registers):
        self.uc.reg_write(reg.UC_MIPS_REG_SP,p.SP)
        self.uc.reg_write(reg.UC_MIPS_REG_RA,p.STOP)
        for name,value in registers.items():
            self.uc.reg_write(getattr(reg,'UC_MIPS_REG_'+name.upper()),value)
        return self.phase(label,entry)


def target_case(blob,source,control=None):
    m=Guest(blob,source)
    global CURRENT_GUEST
    CURRENT_GUEST=m
    if control=='backend40_off':
        flags=int.from_bytes(m.uc.mem_read(p.CTX_PA+0x130,4),'little')&~0x40
        m.uc.mem_write(p.CTX_PA+0x130,struct.pack('<I',flags))
    elif control=='parameter_bit29_off':
        at=p.OUTPUT_PA+0x1c+0xf4
        flags=int.from_bytes(m.uc.mem_read(at,4),'little')&~0x20000000
        m.uc.mem_write(at,struct.pack('<I',flags))
    else:assert control is None
    before=bytes(m.uc.mem_read(GOP_PA,4096))
    context=bytes(m.uc.mem_read(p.CTX_PA,4096));output=bytes(m.uc.mem_read(p.OUTPUT_PA,4096))
    e=m.start('independent original HEVC GOP target-consumer fragment',0xd9204,s0=GOP,s1=BACKEND)
    backend_flags=int.from_bytes(context[0x130:0x134],'little')
    source_flags=int.from_bytes(output[0x1c+0xf4:0x1c+0xf8],'little')
    expected=bytearray(before)
    if backend_flags&0x40 and source_flags&0x20000000:
        expected[0xc8:0xcc]=output[0x28:0x2c]
        assert e['reason']=='boundary: after_target_before_other_fields'
        assert all(hex(IMAGE+pc) in e['pcs'] for pc in (0xd9454,0xd949c,0xd94c8))
    elif backend_flags&0x40:
        assert e['reason']=='boundary: after_target_before_other_fields'
        assert hex(IMAGE+0xd949c) not in e['pcs']
    else:
        assert e['reason']=='boundary: before_other_HEVC_updates'
    after=bytes(m.uc.mem_read(GOP_PA,4096))
    assert after==bytes(expected)
    assert bytes(m.uc.mem_read(p.CTX_PA,4096))==context and bytes(m.uc.mem_read(p.OUTPUT_PA,4096))==output
    assert e['SP_before']==e['SP_after']==hex(p.SP)
    events=[e];timing=None
    if source['backend_timing_flag20000000'] and control is None:
        e=m.start('complete original backend timing predicate',0x1a0a80,a0=BACKEND)
        events.append(e);assert e['reason']=='returned' and m.uc.reg_read(reg.UC_MIPS_REG_V0)==1
        e=m.start('complete original backend timing-pointer getter',0x1a07e4,a0=BACKEND)
        events.append(e);ptr=m.uc.reg_read(reg.UC_MIPS_REG_V0)
        assert e['reason']=='returned' and ptr==p.OUTPUT_PA+IMAGE+0x7d0
        timing={'native_pointer':hex(ptr),'raw8_hex':bytes(m.uc.mem_read(ptr-IMAGE,8)).hex()}
        assert timing['raw8_hex']=='80a90300481f0000'
        assert bytes(m.uc.mem_read(p.CTX_PA,4096))==context and bytes(m.uc.mem_read(p.OUTPUT_PA,4096))==output
    return {'source_label':source['label'],'seed':source['seed'],'declared_control':control,
            'events':events,'GOP_before_hex':before.hex(),'GOP_after_hex':after.hex(),
            'decoded_GOP_target_after':p.a.decode(int.from_bytes(after[0xc8:0xcc],'little')),
            'backend_flags_unchanged':True,'source_parameter_buffer_unchanged':True,
            'timing_getter':timing,'full_GOP_callback_actual_main_binding_or_hardware_proven':False}


def release_case(blob,source,kind):
    m=Guest(blob,source)
    global CURRENT_GUEST
    CURRENT_GUEST=m
    if kind=='two_declared_flags':
        m.uc.mem_write(p.CTX_PA+0x130,struct.pack('<I',0x20000040))
    elif kind=='declared_empty_handle':
        m.uc.mem_write(p.CTX_PA+0x130,struct.pack('<I',0x40))
        m.uc.mem_write(p.CTX_PA+0x10c,bytes(4))
    else:assert kind=='captured_other_flags'
    context_before=bytes(m.uc.mem_read(p.CTX_PA,4096))
    output_before=bytes(m.uc.mem_read(p.OUTPUT_PA,4096))
    expected=bytearray(context_before)
    flags=int.from_bytes(expected[0x130:0x134],'little')&~0x40
    struct.pack_into('<I',expected,0x130,flags)
    e=m.start('independent original clear-parameter40 wrapper '+kind,0x19bfd8,a0=BACKEND)
    events=[e]
    assert e['reason']=='returned'
    assert bytes(m.uc.mem_read(p.CTX_PA,4096))==bytes(expected)
    if kind=='two_declared_flags':
        assert flags==0x20000000
        e=m.start('independent original clear-final-timing-bit wrapper',0x1a0a64,a0=BACKEND)
        events.append(e)
        assert e['reason']=='boundary: before_unknown_GP_release_state'
        struct.pack_into('<I',expected,0x130,0)
        assert bytes(m.uc.mem_read(p.CTX_PA,4096))==bytes(expected)
        assert expected[0x10c:0x110]==struct.pack('<I',p.HANDLE)
    assert bytes(m.uc.mem_read(p.OUTPUT_PA,4096))==output_before
    assert bytes(m.uc.mem_read(GOP_PA,4096))==bytes([source['seed']])*0xc8+struct.pack('<I',((16000000//64)-1)<<8)+bytes([source['seed']])*(4096-0xcc)
    return {'seed':source['seed'],'kind':kind,'events':events,
            'context_before_hex':context_before.hex(),'context_after_hex':bytes(expected).hex(),
            'parameter_buffer_unchanged':True,
            'handle_still_present_after_last_flag_clear':kind=='two_declared_flags',
            'physical_free_hardware_ack_or_recovery_completion_proven':False}


def run(out):
    prior=BASE/'stage80-vcd-pending-and-timing/final-receipt.json'
    assert im.sha(prior.read_bytes())=='d4b7808e3690b8c5fea35237dad9a0bfd164bb92052b96bc9d0c46f944e11c9f'
    for row in json.loads(prior.read_text())['files']:
        assert im.sha((ROOT/row['path']).read_bytes())==row['sha256']
    assert (BASE/'GOAL_STATUS.json').read_bytes()==(STAGE/'goal-status-before.json').read_bytes()
    origin=prior.parent/'run-final-observer-20261026/pending-timing-results.json'
    source=json.loads(origin.read_text())['cases']
    blob=p.a.v.VCD_PATH.read_bytes()
    assert im.sha(blob)==im.PINS[str(p.a.v.VCD_PATH.relative_to(BASE))]
    assert im.cstring(blob,0x21cf70).endswith('/enc/HEVC/gop_ctrl_hevc.cxx')
    assert im.cstring(blob,0x21eb38).endswith('/enc/AVC/gop_ctrl_avc.cxx')
    targets=[];release=[]
    for seed in (0xa5,0xc3):
        for label in ('explicit target16M','explicit target20M override control','native query tail with existing handle'):
            x=next(z for z in source if z['seed']==seed and z['label']==label)
            targets.append(target_case(blob,x))
        x=next(z for z in source if z['seed']==seed and z['label']=='explicit target20M override control')
        targets.extend(target_case(blob,x,control) for control in ('backend40_off','parameter_bit29_off'))
        release.extend(release_case(blob,x,kind) for kind in ('captured_other_flags','two_declared_flags','declared_empty_handle'))
    result={
        'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status':'PASS_HEVC_SPECIFIC_TARGET_CONSUMPTION_AND_BOUNDED_RELEASE_MASKS',
        'target_cases':targets,'release_cases':release,
        'bounded_phases':sum(len(x['events']) for x in targets+release),
        'source_receipt':{'script_sha256':im.sha(Path(__file__).read_bytes()),
                          'corrected_observer_source_sha256':im.sha((p.STAGE/'pending_timing.py').read_bytes()),
                          'stage80_result_sha256':im.sha(origin.read_bytes()),'VCD_sha256':im.sha(blob)},
        'source_identity':{'HEVC_GOP_path':im.cstring(blob,0x21cf70),'AVC_path_excluded':im.cstring(blob,0x21eb38)},
        'original_regions':[{'start':hex(a),'end':hex(z),'instructions':p.a.v.mips_dump(blob,a,z)} for a,z in (
            (0xd9360,0xd937c),(0xd9200,0xd9214),(0xd9454,0xd94cc),
            (0x19bd44,0x19bda4),(0x19bfd8,0x19c000),(0x1a0a64,0x1a0a8c),
            (0x1a0cfc,0x1a0d30))],
        'scope':[
            'Recorded stage80 state/output bytes reused as explicit offline inputs; not live camera snapshots or natural complete controller sequencing.',
            'HEVC GOP fragment needs backend40 and parameter bit29. It copies target to declared GOP+c8 then stops before other HEVC field updates.',
            'Timing predicate/getter returns original buffer pointer and8 bytes without clearing backend flags.',
            'Clear40 with another flag remaining retains handle. Clearing final timing bit writes flags0 then stops before GP release state; zero flags do not prove handle freed.',
            'No full GOP initialization/callback, real MAIN binding, physical allocation/free, hardware acceptance/recording, backup or recovery proof.'],
        'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False,
    }
    im.write_json(out/'hevc-consumer-results.json',result)
    (out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps({'status':result['status'],'target_cases':len(targets),'release_cases':len(release),
                      'bounded_phases':result['bounded_phases'],'hardware_proven':False}))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);args=ap.parse_args()
    im.volume();out=Path(args.output).resolve();assert STAGE in out.parents and not out.exists();out.mkdir()
    try:run(out)
    except Exception:
        (out/'attempt-source.py').write_bytes(Path(__file__).read_bytes())
        im.write_json(out/'attempt-failure.json',{'traceback':traceback.format_exc(),'passing_result':False})
        if 'CURRENT_GUEST' in globals():
            m=CURRENT_GUEST;im.write_json(out/'failure-state.json',{'pc':hex(m.uc.reg_read(reg.UC_MIPS_REG_PC)),
                'reason':m.reason,'last_pcs':[hex(x) for x in m.pcs[-24:]]})
        raise


if __name__=='__main__':main()
