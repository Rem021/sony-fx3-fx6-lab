"""Pure parser regression on saved fixture bytes; no live-origin reacceptance."""
from pathlib import Path
from hashlib import sha256
import json,struct
import flow_receiver as F
import receipt_receiver as R
H=Path(__file__).resolve().parent;rows=[]
for name in ['derived-FS','derived-SS']:
    d=H/'runs'/name;identity=R.Identity(**json.loads((d/'verified-helper.json').read_text())['identity'])
    nonce=bytes.fromhex(json.loads((d/'spec.json').read_text())['nonce'])
    frames=[p.read_bytes()for p in sorted(d.glob('flow-*.bin'))]
    receiver=F.FlowReceiver(identity,nonce,R.GRANT_ID)
    for frame in frames:receiver.accept(frame)
    assert receiver.complete
    acquired=next(x for x in frames if struct.unpack_from('<I',x,24)[0]==11 and struct.unpack_from('<I',x,12)[0]==1)
    for change in ['active_mismatch','missing_required_attribute','packed_config_reserved','claimed_profile_packet']:
        frame=bytearray(acquired)
        if change=='active_mismatch':frame[325]=2
        elif change=='missing_required_attribute':frame[327]=0
        elif change=='packed_config_reserved':frame[314]=1
        else:struct.pack_into('<H',frame,304,512)
        copied=struct.unpack_from('<I',frame,260)[0];frame[264:296]=sha256(frame[320:320+copied]).digest()
        try:F.FlowReceiver(identity,nonce,R.GRANT_ID).descriptor_record(frame)
        except R.Rejected:pass
        else:raise AssertionError(change+' accepted')
    rows.append(dict(case=name,saved_bytes_accepted_by_parser_only=True,new_metadata_mismatches_rejected=4))
with(H/'saved-decoder-bounds-receipt.json').open('x')as f:json.dump(dict(rows=rows,no_new_child_or_USB=True,does_not_recreate_live_origin_proof=True),f,indent=2);f.write('\n')
print('saved-byte decoder regression passed; no live proof recreated')
