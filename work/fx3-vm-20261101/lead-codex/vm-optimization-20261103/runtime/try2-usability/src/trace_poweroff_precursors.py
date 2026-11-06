#!/usr/bin/env python3
"""Read-only, byte-positioned native power event comparison for two fixed runs."""
import hashlib
import json
import re
import struct
from pathlib import Path

ROOT = Path('/Volumes/KAFU2T/AI/Projects/Mac')
OUT = ROOT/'work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability'
AP = ROOT/'work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/appFw.so'
RUNS = {
    'user_try2': OUT.parent/'try2-delivery/runs/try2-70588c4c/serial.log',
    'internal_v2': OUT/'runs/try2gapinternal-47e2924a/serial.log',
}
ROWS = {0x10004:0x41716b0, 0x10005:0x41716c0, 0x3002c:0x41719e0,
        0x30172:0x4172e40, 0x30173:0x4172e50}
AP_SHA = '545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f'
RX = re.compile(rb'FX3_BOOT_QUEUE_SEND tid=(\d+) bytes=28 source=0x830128 raw=([0-9a-f]{56}) caller_relative=0x2eacd4c')

def main():
    raw = AP.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == AP_SHA
    phoff = struct.unpack_from('<Q',raw,32)[0]
    phsize, count = struct.unpack_from('<HH',raw,54)
    segments=[]
    for i in range(count):
        typ,flags,off,va,pa,fs,ms,align = struct.unpack_from('<IIQQQQQQ',raw,phoff+i*phsize)
        if typ == 1: segments.append((va,off,fs))
    def at(va,n):
        for start,off,size in segments:
            if start <= va and va+n <= start+size: return raw[off+va-start:off+va-start+n]
        raise ValueError(hex(va))
    names={}
    for event,row in ROWS.items():
        assert struct.unpack('<I',at(row,4))[0] == event
        ptr=struct.unpack('<Q',at(row+8,8))[0]
        names[event]={'row_va':hex(row),'string_va':hex(ptr),'name':at(ptr,100).split(b'\0')[0].decode()}
    runs={}
    for label,path in RUNS.items():
        data=path.read_bytes();events=[]
        for m in RX.finditer(data):
            event=int.from_bytes(bytes.fromhex(m.group(2).decode())[:4],'little')
            if event in names:
                events.append({'serial_byte':m.start(),'tid':int(m.group(1)),'event':hex(event),
                               'name':names[event]['name'],'raw28':m.group(2).decode()})
        decision=re.search(rb'FX3_AP89_UUD_DECISION[^\r\n]*',data)
        runs[label]={'serial_path':str(path),'serial_sha256':hashlib.sha256(data).hexdigest(),
                     'uud_decision_byte':decision.start() if decision else None,
                     'uud_decision':decision.group().decode() if decision else None,
                     'native_events':events}
        assert sum(e['event']=='0x3002c' for e in events)==1
    result={'schema':'fx3-poweroff-native-events-readonly-v1','appFw_sha256':AP_SHA,
            'event_name_table':{hex(k):v for k,v in names.items()},'runs':runs,
            'inference_limit':'Serial byte order is emission order, not elapsed time or source-causation; native 28B event payload here has zero fields after ID. Both runs have AP89 UUD return 0, unlike old AP87 UUD return 1. No UPM notification payload, power factor/type, or actual setting readback is captured.'}
    dest=OUT/'poweroff-precursors.json';dest.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    print(dest)
    for label,run in runs.items():
        print(label,run['uud_decision'],[(e['serial_byte'],e['name']) for e in run['native_events']])

if __name__=='__main__': main()
