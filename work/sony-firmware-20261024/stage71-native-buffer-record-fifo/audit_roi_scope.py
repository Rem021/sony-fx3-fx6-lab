#!/usr/bin/env python3
"""Pinned original names and backing-record branch; no deallocation execution."""
from pathlib import Path
import datetime
import struct
import sys
import buffer_record_fifo as q


def main():
    q.im.volume();out=q.STAGE/'roi-map-name-and-backing-scope.json';assert not out.exists()
    b=(q.BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes()
    assert q.im.sha(b)==q.im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    values=[]
    for at,expected in [(0x43d784,'fail to alloc ROI MAP dmm area\n'),
                        (0x43e829,'roi_map_queue empty'),(0x43e83d,'roi_map_queue full'),
                        (0x43e850,"didn't return all RIO_MAP queue elements qsize:%d")]:
        end=b.index(b'\0',at,at+180);raw=b[at:end]
        assert raw.decode('ascii')==expected
        values.append({'offset':hex(at),'ASCII':expected,'sha256_including_NUL':q.im.sha(raw+b'\0')})
    result={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'script_sha256':q.im.sha(Path(__file__).read_bytes()),'avcam_sha256':q.im.sha(b),
            'diagnostic_names':values,'static_only':True,
            'regions':[{'start':hex(a),'end':hex(z),'instructions':q.im.dump(b,a,z,q.V)} for a,z in
                       [(0x21ef60,0x21efbc),(0x22db34,0x22dc28)]],
            'backing_descriptor_static_offsets':{'pointer':hex(0x209b8),'low_word':hex(0x209c0),'ID':hex(0x209c4)},
            'scope':['Original diagnostic calls the record queue roi_map_queue; do not silently identify it with all main-stream buffers.',
                     'A later manager routine checks the separate209c4 ID, conditionally calls22dc28 and clears its descriptor. Neither routine nor underlying physical release executes here.',
                     'row8a/output14 controls a later dequeue on this path; current target row386 has raw value0, but the real target request has not executed this later branch.',
                     'stage70 storage-release boundary name is refined to record-return enqueue only; its historical unexecuted stop remains unchanged.'],
            'real_buffer_origin_consumer_lifetime_or_physical_release_proven':False,
            'Mac_offline_only':True,'goal_complete':False,'persistent_write_release':False}
    q.im.write_json(out,result)
    print('original ROI names and separate backing-descriptor branch verified, static only')


if __name__=='__main__':main()
