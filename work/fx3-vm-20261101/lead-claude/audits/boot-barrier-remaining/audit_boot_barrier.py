#!/usr/bin/env python3
"""Offline, original-byte boot audit. Writes only the adjacent proof JSON."""
from pathlib import Path
import hashlib, io, json, re, struct, subprocess, sys
from capstone import Cs, CS_ARCH_ARM64, CS_ARCH_ARM, CS_MODE_ARM, CS_MODE_THUMB
from elftools.elf.elffile import ELFFile

ROOT = Path('/Volumes/KAFU2T/AI/Projects/Mac')
OUT = Path(__file__).resolve().parent
APDIR = ROOT/'work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib'
CP = ROOT/'work/sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin'
PATHS = {'ap': APDIR/'appFw.so', 'cp': CP, 'crypt': APDIR/'libInfraCrypt.so', 'mpr':APDIR/'libmpr.so', 'option':APDIR/'libInfraOptionInstall.so'}
DATA = {k:p.read_bytes() for k,p in PATHS.items()}
ELFS = {k:ELFFile(io.BytesIO(b)) for k,b in DATA.items() if k!='cp'}
def read(k,va,n):
    if k=='cp':
        assert 0x108000<=va and va+n<=0x108000+len(DATA[k]),hex(va)
        return DATA[k][va-0x108000:va-0x108000+n]
    s=next(s for s in ELFS[k].iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=va and va+n<=s['p_vaddr']+s['p_filesz'])
    o=s['p_offset']+va-s['p_vaddr']; return DATA[k][o:o+n]
def string(k,va,n=300):
    try:return read(k,va,n).split(b'\0')[0].decode('utf8')
    except (StopIteration,UnicodeDecodeError,AssertionError):return None
SYMS={}
for k,e in ELFS.items():
    syms={s['st_value']:s.name for s in e.get_section_by_name('.dynsym').iter_symbols() if s['st_value'] and s.name}
    sec=e.get_section_by_name('.rela.plt'); ds=e.get_section_by_name('.dynsym'); plt=e.get_section_by_name('.plt')
    if sec:
        for j,r in enumerate(sec.iter_relocations()):syms[plt['sh_addr']+32+j*16]=ds.get_symbol(r['r_info_sym']).name
    SYMS[k]=syms
def dis(k,va,n):
    c=Cs(CS_ARCH_ARM,CS_MODE_THUMB) if k=='cp' else Cs(CS_ARCH_ARM64,CS_MODE_ARM)
    rows=[]; regs={}
    for i in c.disasm(read(k,va,n),va):
        op=i.mnemonic+' '+i.op_str
        r={'va':hex(i.address),'bytes':i.bytes.hex(),'instruction':op}
        m=re.fullmatch(r'adrp x(\d+), #(0x[0-9a-f]+)',op)
        if m:regs[int(m[1])]=int(m[2],16)
        m=re.fullmatch(r'add x(\d+), x(\d+), #(0x[0-9a-f]+)',op)
        if m and int(m[2]) in regs:
            v=regs[int(m[2])]+int(m[3],16); regs[int(m[1])]=v
            s=string(k,v)
            if s and all(x.isprintable() or x in '\r\n\t' for x in s):r['string_address']=hex(v);r['string']=s
        m=re.fullmatch(r'b[l]? #(0x[0-9a-f]+)',op)
        if m and int(m[1],16) in SYMS.get(k,{}):r['symbol']=SYMS[k][int(m[1],16)]
        rows.append(r)
        # String annotations are deliberately local, not a CFG register simulation.
        if i.mnemonic in ('bl','blr','b','br','ret','cbz','cbnz','tbz','tbnz') or i.mnemonic.startswith('b.'):
            regs.clear()
        elif i.mnemonic not in ('adrp','add'):
            dst=re.match(r'x(\d+)(?:,|$)',i.op_str)
            if dst:regs.pop(int(dst[1]),None)
    return rows
def main():
    # Identity check precedes every output write; no mount-point creation fallback.
    info=subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T'])
    import plistlib
    assert plistlib.loads(info)['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
    if len(sys.argv)>1:
        k=sys.argv[1]
        if k=='string':
            for a in sys.argv[3:]:print(a,string(sys.argv[2],int(a,16)))
        elif k=='find':
            k=sys.argv[2]; needle=bytes.fromhex(sys.argv[3]); start=0
            while (start:=DATA[k].find(needle,start))>=0:
                if k=='cp':print(hex(start+0x108000))
                else:
                    for s in ELFS[k].iter_segments():
                        if s['p_type']=='PT_LOAD' and s['p_offset']<=start<s['p_offset']+s['p_filesz']:print(hex(start-s['p_offset']+s['p_vaddr']))
                start+=1
        else:
            for spec in sys.argv[2:]:
                a,n=(int(x,16) for x in spec.split(':'))
                for r in dis(k,a,n):print(r['va'],r['instruction'],r.get('symbol',r.get('string','')))
        return
    reconstruct()

PINNED = {
 'ap':'545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f',
 'cp':'c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba',
 'crypt':'d3140522c90c0d1e5d75dca06f0f18f58b628d8f8dd6b29b808aaf205cfd842b',
 'mpr':'9aeef3b9edb3d011c0c90cd2387b3a47bd3b506ebfa57be39ad1a9729771b57c',
 'option':'62f2b8a3a0e533a6c80dfd8e2d78ddcaca8ec000c6187bfcf914b9de1a6a8256',
}
BLOCKS = {
 'ap':[(0x2b61efc,0x128c),(0x2b5fe54,0x2b8),(0x278e438,0x128),
 (0x2de20a4,0x40),(0x2de21a4,0x80),(0x2de22e4,0x40),(0x2de2444,0x80),
 (0x2e8b064,0xf8),(0x2e8b46c,0x238),(0x2e8b9a4,0x114),
 (0x2eacf18,0x158),(0x2e1014c,0xa8),(0x2e10048,0x104),
 (0x2ddba54,0x40),(0x2e5d9e4,0x110),(0x2de3894,0x40),
 (0x2e0bae4,0xf0),(0x2de0994,0x40),(0x2eb720c,0xe0),
 (0x2eb091c,0xec),(0x2eafc58,0x148),(0x16f0bd0,0x18),
 (0x2b60208,0x764),(0x2dd0c94,0x40),(0x2dec778,0x3d4),
 (0x2f6ea24,0xc4),(0x2de70a8,0x29c),(0x2de4574,0x168),
 (0x2ddae94,0x40),(0x2e6e5d8,0xb8),(0x2dda7d4,0x40),
 (0x2e69ef0,0x4f0),(0x2ddb054,0x40),(0x2e5c8e8,0x298),
 (0x2ddb4d4,0x40),(0x2e5cb80,0x1d0),
 (0x2b638b8,0x50),(0x2b66dc8,0x40),(0x2b66e08,0x950),
 (0x2b67644,0x60),(0x2b67a60,0x28),(0x2b67a70,0x48),(0x2dee6f0,0xdc),(0x2b631c4,0x60),
 (0x2b63224,0xf8),(0x2b634a8,0x94),(0x2b6353c,0x148),
 (0x2b5fc40,0x28),(0x2b5fe2c,0x28),(0x2dcb354,0x78),
 (0x2dcb494,0x120),(0x2dcb7c8,0x6c),(0x2dcb834,0x1d4)],
 'cp':[(0x1ac2c2,0x28),(0x1b34a8,0x50),(0x1645b4,0x62),
 (0x597f06,0x8c),(0x1b0a80,0x5f0),(0x1ab680,0x26),
 (0x185860,0x48),(0x1adc88,0x58),(0x5ca218,0x52)],
 'crypt':[(0x24a0,0x88),(0x2664,0x88)],
 'mpr':[(0x2b4aec,0x4d4),(0x95fc4,0x120)],
 'option':[(0xf6d0,0x2c),(0x10b44,0x9c)],
}
CHECKS = [
 ('ap',0x2b61f64,'bl #0x2de20a4'),('ap',0x2b62328,'cmp w21, #0x32'),
 ('ap',0x2b61ff0,'bl #0x2de22e4'),('ap',0x2b62290,'bl #0x2de21a4'),
 ('ap',0x2b62640,'bl #0x2de2484'),('ap',0x2b62684,'bl #0x2de2444'),
 ('ap',0x2b626b0,'b.ne #0x2b62630'),('ap',0x2b62208,'bl #0x2ddba54'),
 ('ap',0x2b62d70,'bl #0x2de0994'),('ap',0x2e8b484,'bl #0x1592ea0'),
 ('ap',0x2e8ba78,'bl #0x15937b0'),('ap',0x2eacfe4,'bl #0x1593de0'),
 ('ap',0x2b60264,'bl #0x2dd0c94'),('ap',0x2dd0cb0,'bl #0x2f6ea24'),
 ('ap',0x2dd0cbc,'bl #0x2dec778'),('ap',0x2dec7a0,'mov w0, #0x325'),
 ('ap',0x2dec7e4,'bl #0x2de70a8'),('ap',0x2de72fc,'mov w2, #-1'),
 ('ap',0x2decb30,'ldr w0, [x29, #0x48]'),('ap',0x2b605ac,'bl #0x2dda7d4'),
 ('ap',0x2b605b4,'cbnz w0, #0x2b60800'),('ap',0x2b67a6c,'bl #0x2b6353c'),
 ('ap',0x2dcb9bc,'blr x1'),('ap',0x2dcb9cc,'blr x1'),
 ('ap',0x2b634fc,'str w1, [x20, #-4]!'),('ap',0x2b6350c,'bl #0x2b634a8'),
 ('ap',0x2b63528,'bl #0x1593f80'),('ap',0x2b635d0,'bl #0x1592d30'),
 ('ap',0x2b635dc,'ldr w0, [x0]'),('ap',0x2b63648,'sub w22, w22, #1'),
 ('ap',0x2b6329c,'mov w23, #0x1000'),('ap',0x2b63600,'cmp w0, #2, lsl #12'),
 ('ap',0x2b63678,'cbnz w22, #0x2b63584'),('ap',0x2b6367c,'mov w0, #0'),
 ('cp',0x1ac2c4,'bl #0x1b34a8'),('cp',0x1b34bc,'movt r0, #0x128'),
 ('cp',0x597f2e,'movt r0, #0x8128'),('cp',0x1b0aa0,'movw r1, #0x1325'),
 ('cp',0x1b0aaa,'movs r1, #0x1c'),('cp',0x1b0ad0,'cmp r3, #0x80'),
 ('cp',0x1b0dce,'cmp r6, #0x81'),('cp',0x1b1064,'bl #0x1aef1c'),
 ('mpr',0x2b4f08,'bl #0x827c0'),('mpr',0x2b4fb8,'bl #0x80100'),
]
CAP_FIELDS = [
 ('inProSetIntMicSens',[(4,'!=0'),(5,'==0')]),
 ('inProSetInputType',[(11,'==0')]),('inProSetInputTrim',[]),
 ('inProSetChSource',[(8,'!=0'),(9,'==0'),(10,'==0')]),
 ('inProSetRecLevelMode',[]),('inProSetAgcLink',[]),
 ('inProSetManualGainLink',[]),('inProSetRecLevelLimitter',[]),
 ('inSetLowCut',[(6,'==0x81'),(7,'==0')]),('inSetWindNr',[(13,'==0')]),
 ('inSetIvoice',[]),('inSetMyvoiceCanceling',[(19,'==0')]),
 ('inSetPremiumCloserVoice',[(12,'==0')]),('prcSetZoomNrEe',[(20,'==0')]),
 ('inProSetShoeMic (CP label); AP only logs is_available_wind_nr_mode',[]),
 ('inSetWindNrMode (CP label); AP derives advanced_wind_nr_mode',[(22,'==0')]),
]
def decode_capability(raw):
    assert len(raw)==28
    o=bytearray(23)
    for i,(_,rules) in enumerate(CAP_FIELDS):
        for offset,test in rules:
            value=raw[12+i]
            o[offset]=int(value!=0 if test=='!=0' else value==int(test[2:],0))
    return o
def serial_snapshot(p):
    b=p.read_bytes(); lines=b.split(b'\n')
    def hits(needle):return [{'line':i+1,'text':s.decode(errors='replace').rstrip('\r')} for i,s in enumerate(lines) if needle in s]
    providers=hits(b'FX3_PROVIDER_REQUEST ')
    requests=[]
    for e in providers:
        m=re.search(r'destination=(0x[0-9a-f]+) bytes=(\d+) source=(0x[0-9a-f]+).*?raw=([0-9a-f]+)',e['text'])
        if m:
            v=bytes.fromhex(m[4]); row={'line':e['line'],'destination':m[1],'source':m[3],'size':int(m[2]),'raw':v.hex()}
            if v[:2]==b'\x0d\x20':row['command']=hex(struct.unpack_from('<H',v,2)[0])
            requests.append(row)
    snapshots=[]
    for i,line in enumerate(lines):
        mt=re.fullmatch(rb'FX3_TASK_SNAPSHOT_(32[3-6])_BEGIN\r?',line)
        if mt:
            end=next(j for j in range(i+1,len(lines)) if b'FX3_TASK_SNAPSHOT_' + mt[1]+b'_END' in lines[j])
            rows=[{'line':j+1,'text':lines[j].decode(errors='replace').rstrip('\r')} for j in range(i+1,end) if lines[j].startswith((b'Name:',b'State:',b'98 '))]
            snapshots.append({'tid':int(mt[1]),'begin_line':i+1,'selected_rows':rows})
    return {'path':str(p.relative_to(ROOT)),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),
      'newline_line_count':len(lines)-int(lines[-1]==b''),'provider_count':len(providers),
      'requests':requests,'has':hits(b'FX3_ICRYPT_HAS '),'beep':hits(b'FX3_ADF_BEEP_COMMIT '),
      'icdt':hits(b'FX3_ICDT_MUTED_COMMIT '),'volume_and_base':hits(b'FX3_ADF_MUTED_COMMIT '),
      'mpr_sync_16B':hits(b'FX3_UIPC_SYNC_RETURN '),'pool_snapshots':snapshots,
      'observer_end':hits(b'FX3_UIPC_OBSERVER_END ')[-4:],
      'getfunc_request_count':sum(e.get('command')=='0x325' for e in requests),
      'getfunc_response_count':len(hits(b'tag1=0x1325200d')),
      'barrier_match_receipt':'UNPROVEN: no probe at 2b634dc/2b6353c/2b63628; 28B boot queue sends are unrelated'}

RUNTIME=ROOT/'work/fx3-vm-20261101/menu-repair-01/runtime'
def identity(p):
    b=p.read_bytes()
    return {'path':str(p.relative_to(ROOT)),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def gate_serial(p):
    """Parse LF records without treating binary/control bytes as extra lines."""
    lines=p.read_bytes().split(b'\n'); events=[]
    for line,s in enumerate(lines,1):
        if b'FX3_BOOT_GATE_SAMPLE ' not in s:continue
        fields=dict(re.findall(rb'(\w+)=([^\s]+)',s))
        row={'line':line}
        for k,v in fields.items():
            # printk can append immediately to the final numeric field (0[).
            # Accept only a complete numeric prefix, retain that raw line, and
            # still require every AP80 exposed value to equal saved RAM below.
            numeric=re.match(rb'(?:0x[0-9a-f]+|[0-9]+)(?:/(?:0x[0-9a-f]+|[0-9]+))*',v)
            assert numeric,(str(p),line,k,v)
            if numeric[0]!=v:row['interleaved_raw_line']=s.decode(errors='replace').rstrip('\r')
            v=numeric[0]
            row[k.decode()]=[int(x,0) for x in v.split(b'/')] if k==b'expected' else int(v,0)
        events.append(row)
    def selected(needle):
        return [{'line':i+1,'text':s.decode(errors='replace').rstrip('\r')} for i,s in enumerate(lines) if needle in s]
    return {**identity(p),'events':events,
      'getfunc_commit':selected(b'FX3_ADF_GET_FUNC_COMMIT '),
      'getfunc_consumed':selected(b'FX3_ADF_GET_FUNC_CONSUMED '),
      'selftest':selected(b'FX3_UI_GATE_SELFTEST_PASS '),
      'bound':selected(b'FX3_UI_GATE_BOUND '),
      'next_0328':selected(b'raw=0d2028030a0001800300'),
      'reply1328_count':len(selected(b'tag1=0x1328200d'))}

def runtime_barrier_proof():
    names=['ap77agate-f63dd39e','ap78bboot-537976cc','ap79tail-17293cc1','ap80apins-d8b39ab6']
    runs={n:gate_serial(RUNTIME/'runs'/n/'serial.log') for n in names}
    for n,expected_counts in zip(names,[(3,3,0,0),(3,3,0,0),(4,4,0,0),(4,4,1,1)]):
        es=runs[n]['events']
        counts=tuple(sum(e['id']==v for e in es) for v in [12,21,22,25])
        assert counts==expected_counts,(n,counts)
        runs[n]['counts']={str(v):sum(e['id']==v for e in es) for v in range(12,46)}
        receipt_path=RUNTIME/'runs'/n/'receipt.json';receipt=json.loads(receipt_path.read_bytes())
        runs[n]['receipt']={**identity(receipt_path),**{k:receipt[k] for k in ['created_utc','candidate_sha256','qemu_exit','process_reaped','inputs_unchanged','menu_verified']}}
    n=names[-1]; run=runs[n];events=run['events'];folder=RUNTIME/'runs'/n
    def one(id):
        rows=[e for e in events if e['id']==id];assert len(rows)==1,(id,len(rows));return rows[0]
    entry=one(22); seq=entry['x0'];assert seq==0x7f881841b0
    expected=[entry['x'+str(i)] for i in range(1,5)]
    assert expected==[1,3,2,0] and len(set(expected))==4
    tasks=[('license',0x2b61efc,13),('volume',0x2b5fae4,14),('beep',0x2b61a90,15),('getfunc',0x2b60208,17)]
    creates=[e for e in events if e['id']==12];assert len(creates)==4
    base=creates[0]['x2']-tasks[0][1];bound_tasks=[]
    for name,va,rid in tasks:
        cs=[e for e in creates if e['x2']==base+va];assert len(cs)==1
        c=cs[0];ret=one(rid);handle=ret['x0'];assert handle!=0x1000 and c['x0']==seq
        completes=[e for e in events if e['id']==21 and e['completion_handle']==handle]
        assert len(completes)==1
        done=completes[0]
        assert done['x0']==done['completion_sequence']==seq and done['x1']==handle
        bound_tasks.append({'name':name,'entry_VA':hex(va),'handle':handle,'LE32':struct.pack('<I',handle).hex(),
          'create_line':c['line'],'dispatch_return_line':ret['line'],'completion_line':done['line'],'completion_tid':done['tid']})
    assert sorted(t['handle'] for t in bound_tasks)==sorted(expected)
    before=[e for e in events if e['id']==23];after=[e for e in events if e['id']==24]
    assert len(before)==len(after)==4
    for i,(b,a) in enumerate(zip(before,after)):
        assert b['x19']==a['x19']==seq and b['expected']==a['expected']==expected
        assert b['remaining']==4-i and a['remaining']==3-i
        assert b['token_or_req']==a['token_or_req']==b['x0']==expected[i]
        assert b['tid']==a['tid']==entry['tid'] and b['line']<a['line']
    ret=one(25);assert ret['x0']==0 and ret['tid']==entry['tid'] and ret['line']>after[-1]['line']
    assert len(run['getfunc_commit'])==len(run['getfunc_consumed'])==1
    assert 'result=0' in run['getfunc_consumed'][0]['text']
    send=one(20);assert [send['x0'],send['x2'],send['x4']]==[0x92840747,8,28]
    assert send['token_or_req']==int.from_bytes(bytes.fromhex('0d20250308000180'),'little')

    # Existing observer-RAM mirror, not a new guest read or a second producer.
    ram_path=folder/'ui-gate-counters.bin';ram=ram_path.read_bytes();header=struct.unpack_from('<16Q',ram)
    receipt=json.loads((folder/'receipt.json').read_bytes())
    assert receipt['candidate_sha256']=='e35dca5304ebb0bb51ae89d8945b78114989bd9e87775af6e00c8459bd9d9d7a'
    assert receipt['qemu_exit']==0 and receipt['process_reaped'] and receipt['inputs_unchanged'] and not receipt['menu_verified']
    saved=next(x for x in receipt['read_only_guest_memory_snapshots'] if x['name']==ram_path.name)
    assert saved['sha256']==hashlib.sha256(ram).hexdigest()=='e71bd846f1adb9d7f02ce504b1c97132ad02a8619dc1bd84e9f13ceaa11f5889'
    assert header[0]==0x3145544147335846 and header[1]==2 and header[5]==42 and header[6]==0
    assert len(ram)==saved['actual_bytes']==saved['size']==65536
    ram_fields='id n tid pc x0 x1 x2 x3 x4 x19 x20 x21 remaining w25 w26 w27 w28 fp token_or_req create_sequence create_function completion_sequence completion_handle sentinel'.split()
    records=[]
    for i in range(header[5]):
        row=dict(zip(ram_fields,struct.unpack_from('<24Q',ram,0x4000+i*192)))
        assert row['sentinel']==0x544f4f4245544147
        serial=[e for e in events if all(e[k]==row[k] for k in ['id','n','tid'])];assert len(serial)==1
        e=serial[0]
        for k in ['pc','x0','x1','x2','x3','x4','x19','remaining','token_or_req','create_sequence','create_function','completion_sequence','completion_handle']:
            assert e[k]==row[k],(i,k)
        assert [row['w'+str(j)] for j in range(25,29)]==e['expected']
        row.update({'index':i,'file_offset':hex(0x4000+i*192),'serial_line':e['line']});records.append(row)
    assert {(e['id'],e['n'],e['tid']) for e in events}=={(e['id'],e['n'],e['tid']) for e in records}

    # Tie the installed CPIO names to exactly the reviewed version, then check
    # every expected patch-site word against the unmodified original appFw.
    pins={'fx3-ui-gate-v6.c':'48b357e6415b209bd30e5da68c6b55efc5e7863405eb088cf12bf8efd88d0071',
      'fx3-ui-gate-v6.so':'d4e8de033718447b37f02335ac21a923d464588f48a2430ab98bc77f9555278f',
      'fx3-capid-v33.c':'67dc7657eab55935b215fc767dae73bff01a8f1565403e20fbd14bbc065b761e',
      'fx3-capid-v33.so':'d26885acab342deb475a187b42740ad2749a1ee1502ae6c98460d370f985af75'}
    sources={k:identity(RUNTIME/'helpers'/k) for k in pins}
    for k,h in pins.items():assert sources[k]['sha256']==h
    source=(RUNTIME/'helpers/fx3-ui-gate-v6.c').read_text()
    offsets=[int(x,0) for x in re.search(r'offsets\[45\]=\{([^}]+)',source)[1].split(',')]
    words=[int(x,0) for x in re.search(r'words\[45\]=\{([^}]+)',source)[1].split(',')]
    for va,word in zip(offsets,words):assert struct.unpack('<I',read('ap',va,4))[0]==word,hex(va)
    assert len(offsets)==len(words)==45
    for e in events:assert e['pc']==offsets[e['id']],(e['id'],hex(e['pc']))
    cpio_path=folder/'cpio-audit.json';cpio=json.loads(cpio_path.read_bytes())
    installed=[]
    for member,version in [('simulation/fx3-ui-gate-v1.so','fx3-ui-gate-v6.so'),('simulation/fx3-capid-v1.so','fx3-capid-v33.so')]:
        row=next(m for m in cpio['members'] if m['path']==member);assert row['sha256']==pins[version];installed.append(row)
    assert 'FX3_BOOT_DEFERRED' not in cpio['init_text'] and 'FX3_PIN_GRAPH=empty-owned-mode1-v1' in cpio['init_text']
    capid=(RUNTIME/'helpers/fx3-capid-v33.c').read_text()
    packet=re.search(r'packet\[28\]=\{([^}]+)\};memset\(packet\+12,128,16\)',capid)
    assert packet
    gf_reply=bytes(int(v,0) for v in packet[1].split(','))+bytes([128])*16
    assert gf_reply.hex()=='0d2025131c0001800000000080808080808080808080808080808080'
    next_anchors=[('ap',0x2b67aa0,'bl #0x2dd1014'),('ap',0x2dee798,'bl #0x2de70a8'),
      ('cp',0x18588e,'bl #0x5ad926'),('cp',0x18589e,'bl #0x1858e4'),
      ('cp',0x1adc8a,'mov.w r2, #0x580000'),('cp',0x1adcde,'orrs r0, r2'),
      ('cp',0x5ca236,'movw r0, #0x1328'),('cp',0x5ca258,'str r5, [sp, #0xc]')]
    for k,va,instruction in next_anchors:assert dis(k,va,4)[0]['instruction']==instruction
    assert len(run['selftest'])==len(run['bound'])==1 and 'count=45 ' in run['bound'][0]['text']
    assert len(run['next_0328'])==2 and run['reply1328_count']==0
    assert min(e['line'] for e in run['next_0328'])>ret['line']
    assert all('source=0x81cf61c0' in e['text'] and 'destination=0x92840747' in e['text'] for e in run['next_0328'])
    assert struct.pack('<4HI',0x200d,0x1328,12,0x8001,0x580000).hex()=='0d2028130c00018000005800'
    lines=(folder/'serial.log').read_bytes().split(b'\n');snapshots=[]
    for i,s in enumerate(lines):
        if s.rstrip(b'\r')==b'FX3_TASK_SNAPSHOT_327_BEGIN':
            end=next(j for j in range(i+1,len(lines)) if b'FX3_TASK_SNAPSHOT_327_END' in lines[j])
            selected=[{'line':j+1,'text':lines[j].decode(errors='replace').rstrip('\r')} for j in range(i+1,end)
              if lines[j].startswith((b'Name:',b'State:',b'29 ',b'98 ')) or b'osal_rcv_msg_tmo' in lines[j]]
            snapshots.append({'begin_line':i+1,'selected_rows':selected})
    assert any(x['line']>ret['line'] and x['text'].startswith('29 ') for s in snapshots for x in s['selected_rows'])
    return {'verdict':'PASS_FOUR_DISTINCT_NATURAL_COMPLETIONS_MATCHED_COUNT_ZERO_RETURN_ZERO_AP80',
      'scope':'Existing instrumented software guest only; no new QEMU or guest reads. RAM and serial share the same passive probe producer; timing effects not excluded; not menu/native CP/audio/device acceptance.',
      'runs':runs,'AP80_sequence':hex(seq),'AP80_module_base':hex(base),'AP80_tasks':bound_tasks,
      'barrier_entry_line':entry['line'],'expected_handle_order':expected,
      'match_lines':[e['line'] for e in before],'remaining_after':[e['remaining'] for e in after],
      'barrier_return_line':ret['line'],'barrier_return_w0':ret['x0'],
      'observer_RAM':{**identity(ram_path),'physical':hex(saved['address']),'header_u64':list(header),'record_stride':192,
        'records':records,'crosscheck':'All 42 published RAM records equal serial on every exposed numeric field, including four expected registers; no overflow'},
      'probe_provenance':{'sources':sources,'CPIO_audit':identity(cpio_path),'installed_members':installed,
        'capidv33_static_getfunc_reply28B':gf_reply.hex(),'capidv33_reply_source_line':414,
        'original_instruction_pins':[{'id':i,'VA':hex(va),'word':hex(word)} for i,(va,word) in enumerate(zip(offsets,words))],
        'register_validity':'Probe is before original instruction. Entry id22 uses x0,x1..4 only; id23/24 use x19,w22,w25..28,stack token; id25 after frame restoration uses w0 only (remaining/expected are restored caller values). license void-return x0=0x72 is not a failure status.'},
      'next_wait':{'request10B':'0d2028030a0001800300','proposed_1328_success12B':'0d2028130c00018000005800',
        'parent_after_barrier_return_address':'0x2b67aa4','request_events':run['next_0328'],'reply1328_count':run['reply1328_count'],
        'parent_snapshots':snapshots,'deployed_profile':'capidv33; no FX3_BOOT_DEFERRED in installed init',
        'original_instruction_anchors':[{'image':k,'VA':hex(va),'instruction':ins} for k,va,ins in next_anchors],
        'status':'0328 sent, no1328 observed, parent later remains in osal_rcv_msg_tmo; next software contract, no menu claim'}}

def later_status_proof():
    """Bounded follow-up: later existing serial, separately from AP80a RAM proof."""
    result={}
    for name in ['ap80b1path-d244a966','ap80b2digital-bd9672cf']:
        folder=RUNTIME/'runs'/name;p=folder/'serial.log';run=gate_serial(p);es=run['events']
        lines=p.read_bytes().split(b'\n')
        def hits(needle):
            return [{'line':i+1,'text':s.decode(errors='replace').rstrip('\r')} for i,s in enumerate(lines) if needle in s]
        entry=[e for e in es if e['id']==22];returns=[e for e in es if e['id']==25]
        assert len(entry)==len(returns)==1 and returns[0]['x0']==0
        entry=entry[0];seq=entry['x0'];expected=[entry['x'+str(i)] for i in range(1,5)]
        assert expected==[1,3,2,0]
        creates=[e for e in es if e['id']==12];done=[e for e in es if e['id']==21]
        assert len(creates)==len(done)==4
        base=creates[0]['x2']-0x2b61efc;tasks=[]
        for label,va,rid in [('license',0x2b61efc,13),('volume',0x2b5fae4,14),('beep',0x2b61a90,15),('getfunc',0x2b60208,17)]:
            c=[e for e in creates if e['x2']==base+va];r=[e for e in es if e['id']==rid]
            assert len(c)==len(r)==1 and c[0]['x0']==seq
            handle=r[0]['x0'];completed=[e for e in done if e['x1']==handle]
            assert len(completed)==1 and completed[0]['x0']==completed[0]['completion_sequence']==seq
            tasks.append({'name':label,'handle':handle,'create_line':c[0]['line'],'return_line':r[0]['line'],'completion_line':completed[0]['line']})
        assert sorted(t['handle'] for t in tasks)==sorted(expected)
        before=[e for e in es if e['id']==23];after=[e for e in es if e['id']==24]
        assert len(before)==len(after)==4
        assert sorted(e['token_or_req'] for e in before)==sorted(expected)
        for i,(b,a) in enumerate(zip(before,after)):
            assert b['x19']==a['x19']==seq and b['expected']==a['expected']==expected
            assert b['token_or_req']==a['token_or_req']==b['x0']
            assert b['remaining']==4-i and a['remaining']==3-i
            assert b['tid']==a['tid']==returns[0]['tid']==entry['tid']
            assert b['line']<a['line']<returns[0]['line']
        run['four_task_confirmation']={'sequence':hex(seq),'tasks':tasks,'entry_line':entry['line'],
          'token_order':[e['token_or_req'] for e in before],'remaining_after':[e['remaining'] for e in after],
          'return_line':returns[0]['line'],'return_w0':returns[0]['x0']}
        run['path_commit']=hits(b'FX3_ADF_PATH_COMMIT ');run['path_consumed']=hits(b'FX3_ADF_PATH_CONSUMED ')
        assert len(run['path_commit'])==len(run['path_consumed'])==1
        assert 'path=3 status=0x580000' in run['path_commit'][0]['text'] and 'result=0' in run['path_consumed'][0]['text']
        receipt_path=folder/'receipt.json';receipt=json.loads(receipt_path.read_bytes())
        run['receipt']={**identity(receipt_path),**{k:receipt[k] for k in ['created_utc','candidate_sha256','inputs_unchanged','menu_verified']}}
        assert receipt['inputs_unchanged'] and not receipt['menu_verified']
        if name.startswith('ap80b2'):
            run['digital_commit']=hits(b'FX3_DIGITAL_COMMIT ');run['digital_consumed']=hits(b'FX3_DIGITAL_CONSUMED ')
            run['panel_reverse_enum']=hits(b'FX3_PANEL_REVERSE_ENUM ')
            raw='0d2019011c0001800101000000000000000000000000000000000000'
            run['actual_0119_request28B']=raw;run['actual_0119_requests']=hits(('raw='+raw).encode())
            run['1119_reply_count']=len(hits(b'tag1=0x1119200d'))
            assert len(bytes.fromhex(raw))==28 and bytes.fromhex(raw)[8:11]==bytes([1,1,0])
            assert len(run['digital_commit'])==len(run['digital_consumed'])==len(run['panel_reverse_enum'])==1
            assert 'op=3 status=0' in run['digital_commit'][0]['text'] and 'samples_emitted=0' in run['digital_consumed'][0]['text']
            assert 'enum=2 ' in run['panel_reverse_enum'][0]['text'] and len(run['actual_0119_requests'])==2 and run['1119_reply_count']==0
            assert returns[0]['line']<run['path_consumed'][0]['line']<run['digital_consumed'][0]['line']<run['panel_reverse_enum'][0]['line']
        result[name]=run
    return {'scope':'Later existing serial receipts only; AP80a 42-record RAM/source cross-check remains separately scoped.',
      'verdict':'FOUR_TASK_BARRIER_PASSED_AGAIN_PATH3_AND_DIGITAL_CONSUMED_ACTUAL_0119_ENUM2_PENDING',
      'runs':result,'unproven':'enum2 software orientation consumer,1119 result/consumption,later single-task barrier and final boot notify/menu; enum0-only contract does not admit enum2'}

def reconstruct():
    for k,h in PINNED.items():assert hashlib.sha256(DATA[k]).hexdigest()==h,k
    proof={'scope':'Read-only static audit and existing AP76..AP80 logs/saved RAM; no QEMU, guest actions, runtime/STATE or original-image mutations; only this directory output',
      'sources':{k:{'path':str(v.relative_to(ROOT)),'sha256':hashlib.sha256(DATA[k]).hexdigest(),'bytes':len(DATA[k])} for k,v in PATHS.items()},
      'blocks':{k:{hex(v):dis(k,v,n) for v,n in blocks} for k,blocks in BLOCKS.items()},
      'tool_sources':[{'url':'https://www.capstone-engine.org/lang_python.html','checked':'2026-11-01','scope':'API only; private Sony semantics from original bytes'},
       {'url':'https://github.com/ARM-software/abi-aa/blob/2025Q1/aapcs64/aapcs64.rst','scope':'register ABI only; Sony prototypes inferred'}]}
    for k,v,want in CHECKS:
        got=dis(k,v,4)[0]
        assert got['instruction']==want,(k,hex(v),got,want)
    proof['checked_instructions']=[{'image':k,'va':hex(v),'instruction':s,'bytes':dis(k,v,4)[0]['bytes']} for k,v,s in CHECKS]
    task_rows=[('license_get_i',0x70,0x472c3c0,0x2b61efc,0x2b63900),('volume',0x6c,0x472b2d0,0x2b5fae4,0x2b66de4),
      ('beep',0x68,0x474f098,0x2b61a90,0x2b66e04),('adf_get_func_i',0x64,0x47a6698,0x2b60208,0x2b67678)]
    for name,slot,got,entry,ret in task_rows:assert struct.unpack('<Q',read('ap',got,8))[0]==entry
    proof['tasks']=[{'name':name,'parent_fp_handle_offset':hex(slot),'GOT':hex(got),'entry':hex(entry),'dispatch_return_probe':hex(ret)} for name,slot,got,entry,ret in task_rows]
    proof['handle_sentinels']={'no_free_handle':{'value':0x1000,'hex':'0x1000','LE32':struct.pack('<I',0x1000).hex(),'VA':'0x2b6329c'},
      'abort_token':{'value':0x2000,'hex':'0x2000','LE32':struct.pack('<I',0x2000).hex(),'VA':'0x2b63600','return_w0':1},
      'note':'Hexadecimal sentinel values; historical unprefixed1000/2000 prose refers to these, never decimal1000/2000'}
    # Exact C++ closure vtables bind business and completion member methods.
    vp1=struct.unpack('<Q',read('ap',0x4749398,8))[0]
    vp2=struct.unpack('<Q',read('ap',0x47160d8,8))[0]
    assert struct.unpack('<Q',read('ap',vp1+0x20,8))[0]==0x2b5fc40
    assert struct.unpack('<Q',read('ap',vp2+0x20,8))[0]==0x2b5fe2c
    assert struct.unpack('<Q',read('ap',0x46fe548,8))[0]==0x2b634dc
    proof['closure_binding']={'business_vtable':hex(vp1),'completion_vtable':hex(vp2),'completion_member_pointer_GOT':'0x46fe548 ->0x2b634dc',
      'business_closure_40B':'vptr@0, target_object64@8, member_function64@16, member_adjust64@24',
      'completion_closure_40B':'vptr@0, sequence64@8, member_function64@16, adjust64=0@24, handle32@32, padding4@36'}
    flags=bytes([0x80])*16
    reply=struct.pack('<4HI',0x200d,0x1325,28,0x8001,0)+flags
    legacy=struct.pack('<4HI',0x2004,0x8128,32,1,0)+flags+bytes(4)
    decoded=decode_capability(reply)
    assert len(reply)==28 and len(legacy)==32
    assert [i for i in range(4,23) if decoded[i]]==[4,8]
    assert len(struct.pack('<I',0x1234))==4
    proof['getfunc_contract']={'request':'0d20250308000180','destination':'0x92840747',
      'legacy_request':'0420280108000100','legacy_response_example':legacy.hex(),
      'legacy_tail':'last4B zero is model choice; translator consumes only old+12..27, original old+28..31 meaning unproven',
      'AP_muted_response':reply.hex(),'status':'u32+8=0, required by 2b60268..26c; nonzero is fatal',
      'fields':[{'AP_wire_offset':12+i,'CP_legacy_offset':12+i,'name':name,'muted_byte':'80',
       'AP_output_rules':[{'offset':off,'predicate':'wire'+test} for off,test in rules]} for i,(name,rules) in enumerate(CAP_FIELDS)],
      'AP_output23B':decoded.hex(),'AP_output_capability19B':decoded[4:].hex(),
      'unavoidable_fallback_flags':['out+4 mic_base_level =1 when raw+12!=0','out+8 tone_gen_direct=1 when raw+15!=0'],
      'not_checked':'wrapper does not compare reply opcode/length itself; transport lower-layer validation not established',
      'warning':'80 is wire unavailable; AP still selects base-level/tone-direct fallbacks. 00 advertises supported features. No audio/playback implementation claimed.'}
    # CP table entry proves the request case and its two-stage internal dispatch index.
    jump=struct.unpack('<H',read('cp',0x1ab808,2))[0]
    assert 0x1ab6a6+2*jump==0x1ac2c2
    proof['cp_dispatch']={'internal_case':'0xd0','tbh_instruction':'0x1ab6a2','table_base':'0x1ab6a6','slot':'0x1ab808',
      'raw':read('cp',0x1ab808,2).hex(),'destination':'0x1ac2c2','wire_to_internal_mapping':'not independently reconstructed; request/reply pair also bound by unique ProcGetFunc builder and 1325 translator',
      'RTTI':'0xb38a70 14ProcMsgGetFunc','typeinfo':'0xb6cb84','vtable_address_point':'0xb6cb6c','Execute':'0x1645b4',
      'legacy_success':'0x1645f6 copies cached24B at object+0x38; 597f48 overwrites firstword with status0; object+0x50 error gives efff',
      'flags':'0 or80 accepted in translator; lowcut also81; unknown values diagnostic then preserved, never synthesize arbitrary values',
      'native_current_values':'UNPROVEN runtime cache; no original CP execution'}
    for va,expect in [(0xb38a70,'14ProcMsgGetFunc')]:assert string('cp',va)==expect
    proof['strings']={k+':'+hex(v):string(k,v) for k,vs in {
      'ap':[0x391a590,0x391a5c0,0x3917a6c,0x3917b77,0x3917c05,0x3917c9e,
            0x3963be4,0x3963c05,0x3963c25,0x3963c44,0x3963c5e,0x3963c78,0x3963c92,0x3963cb8,0x3963cdc],
      'cp':[0xb38a70,0x1b34f8,0xd8656c,0xd86595,0xd865be,0xd865e7,0xd86610,0xd86639,0xd86662,0xd8668b,
            0xd866b4,0xd866dd,0xd86706,0xd8672f,0xd86758,0x1b1070,0x1b109c,0x1b10c8]}.items() for v in vs}
    proof['license_flow']={
      'entry':'2b61efc; mode helper16f0bd0==1 returns at2b6241c',
      'options':'2b61f64 ->2de20a4 ->2e8b064: op64=0, exact0x418B synchronous message to01ae852d; response+8 u64 status, +16..25 ten raw option bytes; raw5..13 mapped by3996420',
      'option_retry':'status nonzero ->2b62320 sleep20ms ->50 tries; exhausted clears selectedtype and installed flag, not fatal; a hung osal_snd_sync_msg itself is not bounded by these retries',
      'file':'selected type3: fopen/fseek/ftell/malloc/fread/fclose /setting/sig.txt via2de22e4 ->2e8b9a4; missing file status2 is skipped, not fatal; other selected types call remove(path) via2de21a4 ->2e8b46c; selected<=1 also reset model',
      'detail_list':'if installed flag: op64=7,0x418B sync same service via2de21e4->2e8b4a4; zeroed0x230B info buffer, failure fatal',
      'Has':'selected!=0 queries that type public and private; selected0 loops1..3; each Has*=0 maps {missing:u32=1,status:u32=0}; loop updates1405/1406/1407 booleans to0 if both absent; no key creation in this task',
      'MPR':'2b62208->2ddba54->2e5d9e4->libmpr2b4af4 SetDigitalSignitureLicenseType; selected0/empty list maps MPRmask0; even mask0 matches table category0(NONE) and attempts iCrypt_GetPublicKeyDer(20300006), optionally HashData/FreeData; GetPublicKeyDer failure clears factory hash and continues; synchronous40B op00920111 to80924127; library may call LoadCertificateInfo if returned+8=1 or8; wrapper status must0 else boot fatal',
      'certificate':'only model featuresb1 or360 enabled:2b62de8->2de3894->2e0bae4->libmpr95fc4 GetCertificateInfo; nonzero status continues with defaults. Actual file/secure-store work of certificate loading not exhaustively traced.',
      'model':'2b62e50 transaction, update13b3..13bc,13c5,13c4,412,1324,11f5,11f6,13d2,13fc..1403; optional saved-option rows; event94 and feature2 notification; no direct bk_read symbol in license_get_i itself',
      'UPM':'2b62d70 ->2de0994 ->2eb720c ->2eb0988 ->2eb091c ->2eafc58: 208B asynchronous osal_snd_msg to80920871, op2 subtype12 innercmd00920171, two option bytes58/59 values1 or2 derived from inputs; no reply wait; allocation/send failure logs then returns, not fatal here',
      'runtime_verdict':'six original Has calls prove selected0 traversal passed in AP76corr and sync; no captured named completion handle, exact later wait site UNPROVEN; no crypt stub warranted',
      'backup_boundary':'task reads installed-option service and model state; libInfraOptionInstall f6d0 copies cached10B list and10b44 returns cached license info. Origin/current persistence and transitive C2PA/crypt storage not proven by absence of direct backup calls.'}
    proof['license_flow']['mpr_none_category_table']={'VA':'0x369ce0','raw':read('mpr',0x369ce0,16).hex(),
      'category0_label':read('mpr',0x369ce4,9).decode(),'GetLicenseCategory':'libmpr2b4aec truncates mask to low16bits; mask0 matches category0'}
    proof['software_minimum']={
      'Has_original_return_w0':0,'Has_wrapper_result8B':'0100000000000000',
      'optional_empty_option_response':{
        'activation':'UNPROVEN need; only after runtime proves this exact service wait. No model implemented here.',
        'mode':'same original 1048B synchronous message storage and return0; preserve operation64; status64@8=0; no installed options',
        'op0_response_1048B':bytes(0x418).hex(),
        'op7_response_1048B':(struct.pack('<Q',7)+bytes(0x410)).hex()},
      'getfunc_reply28B':reply.hex(),'completion_record':'LE32(actual dispatch handle), original callback only',
      'UPM':'no reply should be invented for the asynchronous208B battery-option notification'}
    proof['getfunc_flow']={'pre_request':'entry log2b60258 ->trace/profiling2dd0cb0 (may lock) ->2dec778 builds/sends325 at2dec7e4; no conditional business/service call preceding325 inside task',
      'parent_prerequisites':'creation2b67674 only after parent TC sync,timecode,VDF black/OSD/shutter/temp/panel,TPdirection,panelout,resolution,layout,touch sensitivity; last call2b6758c can block before task exists',
      'after_reply':'status0; model f04 19B capability, conditionalf05=1; conditional mpr_CheckCamIdReelNoFile; mpr_SetMovieRecParam; optional mpr_ResetNumberingResume; mpr_GetMovieRecStatus must succeed else fatal; model72a/72b/6f4/6f5/6f8/6f9 then event3010c and return',
      'runtime_verdict':'no observed325 in74 provider records, below256 cap. Exact creation, entry, trace mutex, dispatch or send wait site UNPROVEN without VA probes; post-reply MPR cannot explain pre-send absence.'}
    proof['barrier_contract']={'call':'2b67a6c ->2b6353c',
      'argument_order':{'x0':'sequence','w1':'volume(+6c)','w2':'getfunc(+64)','w3':'beep(+68)','w4':'license(+70)'},
      'completion':'2dcb9bc calls business; after return2dcb9cc calls completion closure ->2b5fe2c ->2b634dc(sequence,handle); copies LE32 handle into deque +a8 under mutex+f8, notify_one(condition+128)',
      'queue':'sequence+a8 std::deque<u32>; front pointer sequence+b8, end cursor+d8; not an OSAL/UIPC queue, no envelope/status/source/callback bytes',
      'consume':'lock+f8; if front==end conditionwait+128; read LE32(front); pop; unlock; token2000 abortreturns1, otherwise compare againstw25..28; match --w22 from4, recycle handle into free deque+28 under mutex+78; unmatched asserts',
      'duplicates':'original compares any of4, does not mark individual done bits; duplicate matching token would decrement again. Verification must independently require four distinct handles exactlyonce; never inject completion',
      'success':'four unique captured dispatch handles each naturally enqueued and matched, w22=0 at2b63678 andw0=0 at2b67a70;2000 abort or1000 no-free sentinel is not success',
      'minimal_bytes':'LE32(actual_handle); examplehandle1234 ->34120000 only illustrates encoding, not a valid runtimehandle',
      'observations':[
       {'VA':'2b63224 / dispatch return probes in tasks[]','read':'x0sequence,x1businessobj,x2businessentry,x3adjust,w4priority; returnw0handle; reject1000'},
       {'VA':'2b634dc','read':'x0sequence,w1handle; [sequence+b8],[sequence+d8], mutex+f8,cond+128; bind context to createdtask'},
       {'VA':'2b6353c','read':'x0,w1..4 map fourhandles; save sequence'},
       {'VA':'2b63628 /2b63648 /2b63678','read':'w0token,w25..28expected,w22before/after;4B at[fp+7c]'},
       {'VA':'2b67a70','read':'w0return0 and fourunique matching receipts; do not infer success solely from PC'},
       {'VA':'2b67674/2b60208/2dd0cb4/2dec7e4','read':'getfunc created/entry/pasttrace; send x0dest,x1request8B,x3reply28B,w2=8,w4=28'},
       {'VA':'2b62208/2b62de8/2b62d70/2b62438','read':'license MPR/C2PA/UPM boundaries; x29 and status slots; finalreturn alone must bindcompletionhandle'}]}
    runs=ROOT/'work/fx3-vm-20261101/menu-repair-01/runtime/runs'
    proof['serial']={p.parent.name:serial_snapshot(p) for p in sorted(runs.glob('ap76*/serial.log'))}
    for run in ['ap76corr-316e20b7','ap76sync-fe30bc21']:
        s=proof['serial'][run]
        assert len(s['beep'])==26 and len(s['icdt'])==4 and len(s['has'])==6
        assert s['getfunc_request_count']==0 and s['getfunc_response_count']==0
        assert s['provider_count']==74
    # Preserve the original AP76 state observation and read current metadata
    # separately. The runtime owner may update STATE; it is not the verdict input.
    proof['AP76_STATE_historical_snapshot']={'path':str((RUNTIME/'STATE.json').relative_to(ROOT)),
      'sha256':'de67308da903bd3a9483eb3832e0f06813fb5dbdbf69bbb19dca4769b1d2feb5',
      'barrier_passed':None,'barrier_verdict':'UNPROVEN_NO_MATCHED_FOUR_TASK_COMPLETION_HANDLE_RECEIPT',
      'provenance':'Preserved from the first completed audit; not regenerated from the newer mutable STATE'}
    state=ROOT/'work/fx3-vm-20261101/menu-repair-01/runtime/STATE.json'
    sb=state.read_bytes();sd=json.loads(sb)
    proof['STATE_readonly_snapshot']={'path':str(state.relative_to(ROOT)),'sha256':hashlib.sha256(sb).hexdigest(),
      'barrier_passed':sd.get('barrier_passed'),'barrier_verdict':sd.get('barrier_verdict'),
      'evidence_priority':'AP80 serial and saved RAM matched four natural handles, count0 and return0; STATE may lag raw receipts. This script never changes STATE.'}
    proof['runtime_continuation']=runtime_barrier_proof()
    proof['runtime_followup']=later_status_proof()
    proof['unproven']=['Exact AP76 license completion and stopping PC after six Has calls',
      'Exact AP76 getfunc task creation/entry/trace-lock state and why no325; parent prerequisite or scheduling remains to measure',
      'Original CP current capability bytes, asynchronous cache initialization, field26/27 CP/AP naming mismatch, and native audio support',
      'Complete transitive backup/C2PA/crypt persistence and optional license branches in this VM',
      'After AP80b2 four-task barrier,path3,digital:actual0119 enum2 completion,later single-task barrier and final boot notify; no menu/audio/physicaldevice acceptance']
    (OUT/'boot-barrier-proof.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
    print(f'PASS: {len(CHECKS)} static instructions +45 probe pins +8 next-wait anchors, task/vtable bindings, AP76 receipts; AP80a four natural completions/count0/return0 and42 RAM records; AP80b1/b2 barrier repeats,path3 consumed,digital consumed,actual0119 enum2 captured; proof rebuilt')
if __name__=='__main__':main()
