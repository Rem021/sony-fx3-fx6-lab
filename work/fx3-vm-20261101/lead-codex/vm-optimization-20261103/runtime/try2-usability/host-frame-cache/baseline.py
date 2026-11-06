"""Latest committed OSD slot, with the frozen ring reader's identity/FNV guards.

Only host observation changes: the same seq-1 modulo-8 slot used by the frozen
OSD consumer is sampled, so a static screen costs only a 256-byte header read.
No source surface is read outside the committed software ring; no guest write.
"""
import json
import struct
import time
from osd_ring93_v4 import RingReader, BASE, HEADER, STRIDE, MAGIC, fnv, rgba, png, sha


def validate_slot(g, data):
    if len(data) != STRIDE:
        return None, 'short ring slot'
    v = struct.unpack_from('<36Q', data)
    if (not v[0] or v[0] != g[4] or v[0] != v[2] or v[1] != g[3]
            or not 0 < v[11] <= 0x12c000 or v[7] > 1
            or not 0 < v[8] <= 640 or not 0 < v[9] <= 480 or v[10] < v[8]):
        return None, 'uncommitted/invalid header'
    if (v[26] != 1 or v[27] not in (1, 2) or not v[29] or not v[32]
            or v[31]+v[32] > 0xffffffffffffffff or v[33] != v[5] or v[35] != v[6]
            or not v[31] <= v[6] < v[31]+v[32] or v[11] > v[31]+v[32]-v[6]
            or v[27] == 2 and not (v[28] and v[30] and v[34])):
        return None, 'invalid registered frame target tuple'
    if (not v[23] <= v[22] < v[24] or v[11] > v[24]-v[22]
            or v[25]+v[22]-v[23] != v[6]):
        return None, 'native CPU mapping/physical mismatch'
    bpp = 2 if v[7] == 0 else 4
    if ((v[9]-1)*v[10]+v[8])*bpp > v[11]:
        return None, 'pixel rows exceed committed span'
    raw = data[0x200:0x200+v[11]]
    if fnv(raw) != v[12]:
        return None, 'concurrent overwrite checksum mismatch'
    return (v, raw), None


class TrialRingReader(RingReader):
    def __init__(self, run, qmp, state):
        super().__init__(run, qmp)
        self.state = state
        self.current_png = self.current_raw = self.current_record = None

    def poll(self, final=False):
        head = self.read(BASE, 0x100, 'osd-ring-header-live.bin')
        if len(head) != 256:
            return
        g = struct.unpack_from('<16Q', head)
        if g[0] != MAGIC or g[1] != 2:
            return
        self.polls.append({'host_monotonic': time.monotonic(), 'global_words': list(g), 'final': final})
        if g[9]:
            raise RuntimeError('native OSD software consumer reports failure')
        if not g[4] or g[4] <= self.last:
            return
        index = (g[4]-1) % 8
        sample = self.read(BASE+HEADER+index*STRIDE, STRIDE, 'trial-ring-slot-live.bin')
        value, reason = validate_slot(g, sample)
        if reason:
            self.rejects.append({'sequence': g[4], 'reason': reason, 'host_monotonic': time.monotonic()})
            return  # torn live samples are retried; never shown to the user
        v, raw = value
        fmt, w, h, stride = v[7:11]
        pixels = rgba(raw, w, h, stride, fmt)
        encoded = png(w, h, pixels)
        record = {'sequence': v[0], 'epoch': v[1], 'update_id': hex(v[3]),
                  'pixel_source_sequence': v[4], 'token': hex(v[5]), 'physical': hex(v[6]),
                  'native_format': fmt, 'native_bitmap_format': v[21], 'width': w, 'height': h,
                  'stride_pixels': stride, 'span': v[11], 'fnv64': hex(v[12]), 'sha256': sha(raw),
                  'PNG_sha256': sha(encoded), 'QMP_read_only': True,
                  'nonuniform_pixels': any(pixels[i:i+4] != pixels[:4] for i in range(4, len(pixels), 4)),
                  'all_zero_pixels': raw.count(0) == len(raw),
                  'host_monotonic': time.monotonic(), 'committed_slot': index,
                  'native_identity': {'FB': hex(v[13]), 'bitmap': hex(v[14]), 'entry': hex(v[15]),
                                      'allocation': hex(v[16]), 'metadata_physical': hex(v[17]),
                                      'FB_format': v[18], 'publish_sem': hex(v[19]), 'config_hash': hex(v[20]),
                                      'bits_cpu_VA': hex(v[22]), 'map_begin': hex(v[23]),
                                      'map_end': hex(v[24]), 'map_offset': hex(v[25])},
                  'registered_target': {'version': v[26], 'kind': v[27], 'object': hex(v[28]),
                                        'epoch': v[29], 'identity': hex(v[30]), 'parent_physical': hex(v[31]),
                                        'parent_bytes': v[32], 'native_token': hex(v[33]), 'vptr': hex(v[34]),
                                        'captured_physical': hex(v[35]),
                                        'valid_during_native_read_lease_and_raster_lifecycle_guards': True},
                  'guest_native_lease_released_before_ring_commit': True,
                  'CP_composition_panel_acceptance': False}
        for name, content in [('trial-frame.png', encoded), ('trial-frame.raw', raw),
                              ('trial-frame.json', (json.dumps(record, indent=2)+'\n').encode())]:
            temp = self.run/(name+'.tmp')
            temp.write_bytes(content)
            temp.replace(self.run/name)
        self.current_raw, self.current_png, self.current_record = raw, encoded, record
        self.seen.add(v[0])
        self.records.append(record)
        self.first_nonuniform |= record['nonuniform_pixels']
        self.last = v[0]
        self.state.publish(encoded, record)
        self.save()

    def evidence(self, label, step=0, key=0):
        if self.current_record is None:
            return {'step': step, 'key': hex(key), 'error': 'no validated committed OSD frame'}
        stem = self.run/('trial-'+label)
        raw, image = stem.with_suffix('.raw'), stem.with_suffix('.png')
        if raw.exists() or image.exists():
            raise RuntimeError('trial evidence already exists')
        raw.write_bytes(self.current_raw)
        image.write_bytes(self.current_png)
        record = dict(self.current_record, step=step, key=hex(key), raw=str(raw), PNG=str(image),
                      raw_sha256=sha(self.current_raw), matches_committed_ring=True,
                      latest_native_committed_sequence=self.current_record['sequence'],
                      source='QMP validated immutable committed software-ring copy; no current source-surface reread')
        stem.with_suffix('.json').write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n')
        return record
