#!/usr/bin/env python3
"""Authorized Mac cached USB device subtree, including IOService interfaces.

No USB interface/driver handles, SCSI/PTP/vendor commands or media file reads.
Uses the previously sealed whitelist sanitizer; raw IORegistry stays in memory.
"""
from pathlib import Path
import argparse,datetime,hashlib,importlib.util,json,subprocess
STAGE=Path(__file__).resolve().parent;BASE=STAGE.parent
SOURCE=BASE/'stage129-AP-DMM-config-and-device-trial-plan/mac_cached_usb_inventory.py'
SOURCE_SHA='ed7094e03e1fbad280080ac852a15e8aa571a8011d2033a397648ff6f5374647'
def main(out):
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SOURCE_SHA
    if not out.resolve().is_relative_to(STAGE.resolve()):raise ValueError('output outside current stage')
    s=importlib.util.spec_from_file_location('sealed_mac_cache_collector',SOURCE);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
    m.volume()
    # Read kernel-maintained properties for USB device roots; this does not
    # instantiate or open a USB device, user client, storage handle or driver.
    command=['/usr/sbin/ioreg','-a','-p','IOService','-r','-c','IOUSBHostDevice','-l','-w','0']
    try:r=subprocess.run(command,capture_output=True,check=True,timeout=15)
    except Exception:raise SystemExit('IOService cache query failed; raw output not saved') from None
    j=m.sanitize(r.stdout);j.update({'source':'explicit_mac_IORegistry_IOService_USB_device_cache',
        'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'raw_source_saved':False,
        'sanitizer_source_sha256':SOURCE_SHA,'collector_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'camera_interface_or_media_access':False,'authorization':'user approved Mac cached USB metadata only'})
    m.volume();out.mkdir()
    with (out/'sanitized-service-cache-receipt.json').open('x') as f:json.dump(j,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps({'candidate_count':j['candidate_count'],'receipt':str(out/'sanitized-service-cache-receipt.json')},ensure_ascii=False))
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--out',type=Path,required=True);main(a.parse_args().out)
