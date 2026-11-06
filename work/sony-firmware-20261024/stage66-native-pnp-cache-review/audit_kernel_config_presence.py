#!/usr/bin/env python3
"""Bound the vendor config correlation against the original7.02 Image."""
from pathlib import Path
import datetime
import hashlib
import json
import sys

STAGE = Path(__file__).resolve().parent
sys.path.insert(0, str(STAGE.parent/'stage65-windows-cache-and-runtime-readiness'))
import prepare_handoff as h


def main():
    h.im.volume()
    p = STAGE.parent/'stage47-runtime-provider-binding/official-files/nflasha3/vmlinux.bin'
    raw = p.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    assert digest == 'da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c'
    offset = raw.index(b'Linux version ')
    banner = raw[offset:raw.index(bytes([0]), offset)].decode('ascii')
    assert '4.9.337-scel+' in banner and 'SMP PREEMPT' in banner
    assert raw.find(b'IKCFG_ST') == raw.find(b'IKCFG_ED') == -1
    out = {
        'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'original_kernel_sha256': digest,
        'kernel_bytes': len(raw),
        'version_banner_offset': hex(offset),
        'version': '4.9.337-scel+',
        'compiler_version': 'gcc6.4.0 Sony CE Linux14.0.1.0',
        'banner_SMP_PREEMPT': True,
        'IKCFG_ST_marker_found_in_this_Image': False,
        'IKCFG_ED_marker_found_in_this_Image': False,
        'actual7_02_dot_config_recovered': False,
        'vendor_defconfig_exact_build_match': False,
        'interpretation': 'Banner corroborates kernel version family and SMP/PREEMPT. No embedded config markers found in this Image; this does not prove no config exists elsewhere, nor that all reference7.00 config values are actual7.02 values.',
        'kernel_or_downloaded_source_executed': False,
        'camera_access': False,
        'goal_complete': False,
    }
    h.im.write_json(STAGE/'kernel-config-presence.json', out)
    print(json.dumps(out))


if __name__ == '__main__':
    main()
