#!/usr/bin/env python3
"""Additional original VCD baseband predicates and checker scope controls.

Preserve the stage48 minimal common fixture unchanged as a failing observation.
Geometry-only edits are explicit HOST controls, not a native input producer.
"""
from pathlib import Path
import argparse
import json
import struct
import traceback
import vcd_consumer as v


class BasebandGuest(v.Guest):
    def code(self,uc,pc,size,user):
        off=pc-v.IMAGE_VA
        if 0x1a81cc<=off and off+size<=0x1a8594:
            self.pcs.append(pc)
            raw=bytes(uc.mem_read(off,size));assert raw==self.blob[off:off+size]
            ins=next(self.md.disasm(raw,pc),None)
            assert ins is not None and ins.mnemonic not in {
              'syscall','break','cache','sync','mfc0','mtc0','eret','wait','tlbwi','tlbwr','tlbr','tlbp'}
            return
        return super().code(uc,pc,size,user)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True)
    args=parser.parse_args();v.im.volume();out=Path(args.output).resolve()
    assert v.STAGE in out.parents and not out.exists();out.mkdir()
    try:
        core=v.STAGE/'run-corrected-20261025/vcd-consumer-results.json'
        proof=json.loads(core.read_text());source=v.STAGE/'vcd_consumer.py'
        assert v.im.sha(source.read_bytes())==v.im.sha((core.parent/'executed-source.py').read_bytes())
        old=json.loads((v.c.STAGE/'run-20261025/codec-initialization-results.json').read_text())
        data=bytes.fromhex(old['cases'][1]['common_hex'])
        vcd=v.VCD_PATH.read_bytes();assert v.im.sha(vcd)==proof['static_evidence']['VCD_sha256']
        basebands=[]
        for label,width,height,expected in (
          ('unchanged stage48 minimal common block',None,None,0x3006),
          ('host geometry-only control1920_1080',1920,1080,0),
          ('host odd geometry-only control1921_1080',1921,1080,0x3006)):
            raw=bytearray(data)
            if width is not None:
                struct.pack_into('<I',raw,0xc,width);struct.pack_into('<I',raw,0x10,height)
            m=BasebandGuest(vcd,bytes(raw))
            m.uc.reg_write(v.reg.UC_MIPS_REG_A1,0);m.uc.reg_write(v.reg.UC_MIPS_REG_A2,0)
            event=m.run(label,0x1a81cc)
            assert event['reason']=='returned' and int(event['native_v0'],16)==expected
            event['expected_v0']=hex(expected)
            event['scope']='Original baseband checker only. Geometry controls are host edits to common+0xc/+0x10; actual native start-input producer, meaning/binding of every field and real sensor timing remain unverified.'
            basebands.append(event)
        payload=bytes.fromhex(old['cases'][1]['payload_hex']);rates=[]
        for label,word in (('all three rate words zero',0),('all three rate words FFFFFFFF',0xffffffff)):
            raw=bytearray(payload);struct.pack_into('<3I',raw,0x2c,word,word,word)
            event=v.Guest(vcd,bytes(raw)).run(label)
            assert event['reason']=='returned' and int(event['native_v0'],16)==0
            assert not set(range(0x2c,0x38))&set(int(i,16) for i in event['input_byte_offsets_read'])
            event['scope']='Bounded original config predicate does not read the packed target/trace/CPB words on this HEVC fixture. Return0 is not a numeric bitrate/capacity/hardware check.'
            rates.append(event)
        result={'status':'PASS_NATIVE_BASEBAND_REJECTION_AND_GEOMETRY_RATE_SCOPE_CONTROLS',
          'additional_original_function_runs':len(basebands)+len(rates),'baseband_cases':basebands,'rate_scope_controls':rates,
          'unchanged_stage48_common_rejected_by_original_checker':True,
          'first_observed_error':'0x3006 at original baseband checker; zero horizontal geometry in minimal upstream fixture',
          'host_geometry_control_not_native_input_producer':True,
          'config_predicate_does_not_validate_packed_bitrate_words_on_this_path':True,
          'full_start_request_validity_or_hardware_acceptance':False,
          'baseband_checker_original_instructions':v.mips_dump(vcd,0x1a81cc,0x1a8594),
          'camera_or_remote_operation':False,'goal_complete':False,'persistent_write_release':False}
        v.im.write_json(out/'baseband-results.json',result)
        (out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
        v.im.write_json(out/'source-receipt.json',{'script_sha256':v.im.sha(Path(__file__).read_bytes()),
          'core_source_sha256':v.im.sha(source.read_bytes()),'core_proof_sha256':v.im.sha(core.read_bytes()),
          'VCD_sha256':v.im.sha(vcd),'stage48_common_hex':data.hex()})
        print(json.dumps({k:result[k] for k in ('status','additional_original_function_runs',
          'unchanged_stage48_common_rejected_by_original_checker','full_start_request_validity_or_hardware_acceptance')}))
    except Exception:
        (out/'attempt-source.py').write_bytes(Path(__file__).read_bytes())
        v.im.write_json(out/'attempt-failure.json',{'traceback':traceback.format_exc(),'passing_result':False})
        raise


if __name__=='__main__':main()
