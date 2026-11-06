#!/usr/bin/env python3
"""Static original-byte provenance for the unbound channel-manager input."""
import datetime
import json
import struct
import row_channel as f


def main():
    f.im.volume();out=f.STAGE/'channel-binding-audit.json';assert not out.exists()
    blob=(f.BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes()
    assert f.im.sha(blob)==f.im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    result=json.loads((f.STAGE/'run-two-object-bounds-20261026/row-channel-results.json').read_text())
    entries=[c['original_channel_preparation']['acquisition'] for c in result['cases']
      if c['original_channel_preparation']]
    assert len(entries)==4 and all(x['x0_x4'][0]=='0x0' and not x['body_executed'] for x in entries)
    # Aligned raw scan is a candidate finder, not a whole-image call graph or
    # proof that all 0..0x300000 bytes are executable instructions.
    calls=[]
    for at in range(0,0x300000,4):
        w=struct.unpack_from('<I',blob,at)[0]
        if w&0xfc000000!=0x94000000:continue
        imm=w&0x3ffffff
        if imm&(1<<25):imm-=1<<26
        if at+imm*4==0x22c99c:calls.append(at)
    assert calls==[0x226e84,0x226eb8]
    regions=[('original manager setter',0x22c99c,0x22c9a4),
      ('factory six common / two other object pointer-binding loops',0x226e70,0x226ee0),
      ('first native manager load and acquisition call',0x21dee8,0x21df1c),
      ('unexecuted acquisition prefix and next helper call',0x22d394,0x22d3c4)]
    proof={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'avcam_sha256':f.im.sha(blob),'status':'STATIC_NEXT_BINDING_SOURCE_IDENTIFIED_NOT_EXECUTED',
      'observed_four_channel_manager_arguments_are_zero_in_partial_fixture':True,
      'null_in_model_is_not_camera_defect_or_live_state_claim':True,
      'original_setter':'str x1, [x0, #0x10a0]; ret',
      'aligned_direct_BL_scan_candidates':[hex(f.V+x) for x in calls],
      'scan_scope':'Aligned 0..0x300000 raw bytes only; not complete executable or indirect-call analysis.',
      'static_factory_loop_input':'Factory [X19] copied by original setter into six objects starting +0x40 stride0xe518, then two starting+0x56080 stride0x269b0.',
      'native_binding_constructor_factory_manager_or_allocation_provider_executed_here':False,
      'next_required':'Trace and initialize actual factory-to-manager ownership and original acquisition dependencies; do not insert an arbitrary nonzero manager or success return.',
      'regions':[{'name':name,'instructions':f.im.dump(blob,a,z,f.V)} for name,a,z in regions]}
    f.im.write_json(out,proof)
    print(json.dumps({'status':proof['status'],'direct_BL_candidates':len(calls)}))


if __name__=='__main__':main()
