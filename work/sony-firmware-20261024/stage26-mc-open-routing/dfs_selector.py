#!/usr/bin/env python3
"""Original DFS-labelled selector before logging; not format validation."""
from pathlib import Path
import argparse
import datetime
import json
import struct
import traceback

import mc_open_routing as r


def case(blob,label,packet,fmt,instance=0):
    m=r.RawGuest(blob,[(0x1788d4,0x178aac)],
       {0x178a0c:'before_original_diagnostic',0x178a98:'nonzero_instance_skip_exit'})
    r.seed(m,packet,fmt)
    m.uc.mem_write(r.NORMAL+8,r.p64(r.MSGIF))
    m.uc.mem_write(r.CONFIG+8,struct.pack('<I',instance))
    m.uc.mem_write(r.NORMAL+0x50,packet)
    m.uc.mem_write(r.NORMAL+0x3a4,struct.pack('<I',0xdeadbeef))
    m.regs(x0=r.NORMAL)
    result=m.run(0x1788d4)
    rate=int.from_bytes(m.read(r.NORMAL+0x3a4,4),'little')
    mode=m.uc.reg_read(r.reg.UC_ARM64_REG_X20)
    if instance:
        assert result['reason']=='boundary: nonzero_instance_skip_exit' and rate==0xdeadbeef
        mode=None
    else:
        assert result['reason']=='boundary: before_original_diagnostic'
        assert (rate,mode)==({'target MAIN':(30,0x15),'matching proxy':(30,0x15),
           'factory UHD59.94 control':(60,0x13),'invalid codec/frame fixture':(0,0x10)}[label])
    assert m.read(r.NORMAL+0x50,0x98)==packet
    result.update(label=label,instance_index_fixture=instance,
       nominal_rate_scalar=rate if not instance else None,DFS_mode_scalar=hex(mode) if mode is not None else None,
       packet_unchanged=True,
       precondition='Independent post-copy state fixture; actual instance, task hooks and preceding Open dependencies not executed.',
       scope='Original DFS-labelled width/height/rate selection before diagnostic. No DFS backend applied, no format support or exact frame-clock acceptance.')
    return result


def run(out):
    r.im.volume()
    prior=r.STAGE/'run-20261025/source-receipt.json'
    receipt=json.loads(prior.read_text())
    assert r.im.sha((r.STAGE/'mc_open_routing.py').read_bytes())==receipt['script_sha256']
    assert r.im.sha((r.STAGE/'run-20261025/mc-open-routing-results.json').read_bytes())==receipt['result_sha256']
    blob=(r.BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes()
    assert r.im.sha(blob)==r.im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    variants=r.packet_variants()
    cases=[case(blob,*v) for v in variants]
    cases.append(case(blob,*variants[0],instance=1))
    proof={'status':'PASS_ORIGINAL_DFS_LABELLED_SELECTOR_ONLY',
      'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'cases':cases,'nominal_rate_table_offset':'0x314830',
      'nominal_rate_table':list(struct.unpack_from('<10I',blob,0x314830)),
      'original_region':r.im.dump(blob,0x1788d4,0x178aac,r.V),
      'original_diagnostic':r.im.cstring(blob,0x41e447),
      'target_nominal_30_does_not_prove_exact_30_000_or_hardware_frameclock':True,
      'mode_0x15_is_not_codec_enum_decimal15':True,
      'scope':'Independent original pre-diagnostic selection on fixture state. Raw output mode labels are not codec support, frequency application or acceptance.',
      'DFS_backend_or_hardware_executed':False,'native_output_adapters':False,
      'camera_or_remote_access_attempted':False,'goal_complete':False,'persistent_write_release':False}
    r.im.write_json(out/'dfs-selector-results.json',proof)
    r.im.write_json(out/'source-receipt.json',{'script_sha256':r.im.sha(Path(__file__).read_bytes()),
      'guest_harness_sha256':receipt['script_sha256'],'raw_image_sha256':r.im.sha(blob),
      'packet_source_sha256':r.im.sha((r.BASE/'stage23-encoder-boundary/run-corrected-20261025/encoder-boundary-results.json').read_bytes()),
      'result_sha256':r.im.sha((out/'dfs-selector-results.json').read_bytes())})
    print(json.dumps({'status':proof['status'],'cases':len(cases),
       'target_nominal_rate':30,'target_raw_DFS_mode':'0x15','hardware_verified':False}))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True)
    args=parser.parse_args();r.im.volume();out=Path(args.output).resolve()
    assert r.STAGE in out.parents and not out.exists();out.mkdir()
    try:run(out)
    except Exception:
        with (out/'attempt-source.py').open('xb') as f:f.write(Path(__file__).read_bytes())
        r.im.write_json(out/'attempt-failure.json',{'traceback':traceback.format_exc(),'passing_result':False});raise


if __name__=='__main__':main()
