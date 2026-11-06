#!/usr/bin/env python3
"""Build FX3MS2 host fixtures from the accepted native FX3MS1 framed fixture.

No target execution: this only re-encodes the already accepted host-side maps
payload into the new bounded-sequential-read protocol and validates it with
the new strict decoder/provider.
"""
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CAND = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(CAND / 'host'))
import decode_fx3ms1 as old
import fx3ms2 as new

SRC = CAND / 'fixtures/source-native-target-frame-fx3ms1.serial'
SRC_MAPS = CAND / 'fixtures/source-native-target-frame-fx3ms1.maps'
OUT = CAND / 'fixtures/native-target-frame-v2.serial'
OUT_MAPS = CAND / 'fixtures/native-target-frame-v2.maps'
NOAPP = CAND / 'fixtures/no-appfw-v2.serial'
MANIFEST = CAND / 'fixtures/manifest.json'

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def b64(b):
    import base64
    return base64.b64encode(b).decode('ascii')

def make(payload, pid, starttime, seq=1, read_count=3, eintr=2):
    attempts = read_count + eintr + 1
    cap = 262144
    max_reads = 64
    max_ms = 1000
    ident = '%d:%d' % (pid, starttime)
    lines = []
    lines.append('FX3MS2 BEGIN pid=%d starttime=%d seq=%d cap=%d max_reads=%d max_ms=%d capture=bounded_sequential_read' %
                 (pid, starttime, seq, cap, max_reads, max_ms))
    for i in range(0, len(payload), 192):
        chunk = payload[i:i + 192]
        lines.append('FX3MS2 DATA %d %d %d %d %s' % (i // 192, pid, starttime, seq, b64(chunk)))
    lines.append('FX3MS2 END pid=%d starttime=%d seq=%d bytes=%d lines=%d digest=fnv1a64:%016x read_count=%d eintr_count=%d read_attempts=%d eof_observed=1 identity_before=%s identity_after=%s snapshot_atomic=0 line_terminated=1 complete=1 cap_hit=0 read_limit_hit=0 time_limit_hit=0' %
                 (pid, starttime, seq, len(payload), payload.count(b'\n'), new.fnv1a64(payload), read_count, eintr, attempts, ident, ident))
    return ('\n'.join(lines) + '\n').encode()

def main():
    src = old.decode(SRC.read_text())
    payload = src['maps_text'].encode()
    SRC_MAPS.write_bytes(payload)
    serial = make(payload, src['pid'], src['starttime'])
    OUT.write_bytes(serial)
    OUT_MAPS.write_bytes(payload)
    d = new.decode(serial.decode())
    mapd = new.FramedProviderV2().select(serial.decode())
    app_rows = [l for l in payload.decode().splitlines() if '/usr/lib/appFw.so' in l]
    im_rows = [l for l in payload.decode().splitlines() if '/usr/bin/im.elf' in l]
    # no-appFw fixture: keep a complete valid frame whose payload has no appFw rows
    no_payload = b'\n'.join(l for l in payload.split(b'\n') if b'/usr/lib/appFw.so' not in l) + b'\n'
    no_serial = make(no_payload, src['pid'], src['starttime'])
    NOAPP.write_bytes(no_serial)
    nd = new.decode(no_serial.decode())
    try:
        new.FramedProviderV2().select(no_serial.decode())
        no_app_reject = None
    except new.NoAppFwFrame as e:
        no_app_reject = str(e)
    manifest = {
        'schema': 'fx6-map-collector-shortread-fixtures-v1',
        'source': {'path': str(SRC), 'sha256': sha(SRC),
                   'fx3ms1_pid': src['pid'], 'fx3ms1_starttime': src['starttime'],
                   'fx3ms1_bytes': src['bytes'], 'fx3ms1_maps_sha256': src['maps_sha256']},
        'source_maps': {'path': str(SRC_MAPS), 'sha256': sha(SRC_MAPS), 'bytes': len(payload)},
        'valid': {'path': str(OUT), 'sha256': sha(OUT), 'bytes': len(serial),
                  'pid': d['pid'], 'starttime': d['starttime'], 'seq': d['selected_seq'],
                  'payload_bytes': d['bytes'], 'lines': d['lines'],
                  'read_count': d['read_count'], 'eintr_count': d['eintr_count'],
                  'read_attempts': d['read_attempts'], 'snapshot_atomic': d['snapshot_atomic'],
                  'maps_sha256': d['maps_sha256'],
                  'bias': hex(mapd['ap']['bias']), 'appfw_rows': len(app_rows),
                  'imelf_rows': len(im_rows), 'frame_count': d['frame_count']},
        'no_appfw': {'path': str(NOAPP), 'sha256': sha(NOAPP), 'bytes': len(no_serial),
                     'payload_bytes': nd['bytes'], 'no_appfw_reject': no_app_reject},
        'note': 'host fixture only; source FX3MS1 frame was accepted offline; no target execution or VM',
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(manifest, indent=2))

if __name__ == '__main__':
    main()
