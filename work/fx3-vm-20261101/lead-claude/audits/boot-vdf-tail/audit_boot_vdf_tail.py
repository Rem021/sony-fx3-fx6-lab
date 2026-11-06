#!/usr/bin/env python3
"""Static original-image audit. Never runs guest code; writes only adjacent proof."""
from pathlib import Path
import hashlib, io, json, plistlib, re, struct, subprocess, sys
from capstone import Cs, CS_ARCH_ARM64, CS_ARCH_ARM, CS_MODE_ARM, CS_MODE_THUMB
from elftools.elf.elffile import ELFFile

ROOT = Path('/Volumes/KAFU2T/AI/Projects/Mac')
OUT = Path(__file__).resolve().parent
BASE = ROOT/'work/fx3-vm-20261101/menu-repair-01'
LIB = BASE/'original-uipc/ap-projection/regular-files/usr/lib'
PATHS = {'ap': LIB/'appFw.so', 'cp': ROOT/'work/sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin'}
DATA = {k:p.read_bytes() for k,p in PATHS.items()}
ELFS = {'ap':ELFFile(io.BytesIO(DATA['ap']))}
SYMS = {}
e=ELFS['ap']; tab=e.get_section_by_name('.dynsym'); sec=e.get_section_by_name('.rela.plt'); plt=e.get_section_by_name('.plt')
for j,r in enumerate(sec.iter_relocations()): SYMS[plt['sh_addr']+32+j*16]=tab.get_symbol(r['r_info_sym']).name

def read(k, a, n):
    if k=='cp':
        assert 0x108000<=a and a+n<=0x108000+len(DATA[k])
        return DATA[k][a-0x108000:a-0x108000+n]
    s=next(s for s in ELFS[k].iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=a and a+n<=s['p_vaddr']+s['p_filesz'])
    o=s['p_offset']+a-s['p_vaddr']; return DATA[k][o:o+n]

def string(k,a,n=500):
    try: return read(k,a,n).split(b'\0')[0].decode()
    except (StopIteration, UnicodeDecodeError, AssertionError): return None

def dis(k,a,n):
    c=Cs(CS_ARCH_ARM,CS_MODE_THUMB) if k=='cp' else Cs(CS_ARCH_ARM64,CS_MODE_ARM)
    c.skipdata=True  # Thumb ranges include literal/TBB tables; .byte is data, not executable proof.
    out=[]; regs={}
    for i in c.disasm(read(k,a,n),a):
        op=i.mnemonic+' '+i.op_str
        r={'va':hex(i.address),'bytes':i.bytes.hex(),'instruction':op}
        if k=='ap':
            m=re.fullmatch(r'adrp x(\d+), #(0x[0-9a-f]+)',op)
            if m:regs[int(m[1])]=int(m[2],16)
            m=re.fullmatch(r'add x(\d+), x(\d+), #(0x[0-9a-f]+)',op)
            if m and int(m[2]) in regs:
                v=regs[int(m[2])]+int(m[3],16);regs[int(m[1])]=v;s=string(k,v)
                if s and all(c.isprintable() or c in '\r\n\t' for c in s):r.update(string_address=hex(v),string=s)
            m=re.fullmatch(r'b[l]? #(0x[0-9a-f]+)',op)
            if m and int(m[1],16) in SYMS:r['symbol']=SYMS[int(m[1],16)]
        out.append(r)
        if i.mnemonic in ('bl','blr','b','br','ret','cbz','cbnz','tbz','tbnz') or i.mnemonic.startswith('b.'): regs.clear()
        elif i.mnemonic not in ('adrp','add'):
            m=re.match(r'x(\d+)(?:,|$)',i.op_str)
            if m:regs.pop(int(m[1]),None)
    return out

def volume_check():
    p=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
    assert p['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'

def main():
    volume_check()
    if len(sys.argv)>1:
        for spec in sys.argv[1:]:
            k,a,n=spec.split(':')
            for r in dis(k,int(a,16),int(n,16)):print(r['va'],r['instruction'],r.get('symbol',r.get('string','')))
    else: reconstruct()

def reconstruct():
    assert hashlib.sha256(DATA['ap']).hexdigest()=='545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f'
    assert hashlib.sha256(DATA['cp']).hexdigest()=='c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba'
    proof={'scope':'Read-only static original AP/CP and existing AP78b receipts. No QEMU, guest execution, hardware or runtime edits.',
           'address_rule':'AP ELF VA; CP Thumb VA=file offset+0x108000; serial lines split only at LF.',
           'sources':{}, 'blocks':{}, 'dispatch':[], 'checks':[], 'requests':REQUESTS,
           'unproven':UNPROVEN, 'reply_candidates':REPLIES}
    for k,p in PATHS.items():proof['sources'][k]={'path':str(p.relative_to(ROOT)),'bytes':len(DATA[k]),'sha256':hashlib.sha256(DATA[k]).hexdigest()}
    for k,blocks in BLOCKS.items():
        proof['blocks'][k]={}
        for a,n in blocks:
            records=dis(k,a,n)
            assert records and sum(len(bytes.fromhex(r['bytes'])) for r in records)==n,(k,hex(a),n)
            proof['blocks'][k][hex(a)]={'raw':read(k,a,n).hex(),'instructions':records,'literal_tables_may_be_present':k=='cp'}
    for k,a,want in CHECKS:
        got=dis(k,a,4)[0]
        assert got['instruction']==want,(k,hex(a),want,got)
        proof['checks'].append({'image':k,**got})
    for cmd,internal,handler in ((0x142,0x97,0x1aba9e),(0x15a,0xa1,0x1abbbe),(0x145,0x8f,0x1ab970),
                                (0x11b,0x1f,0x1ab818),(0x160,0xa4,0x1abc00),(0x165,0xa7,0x1abc84),
                                (0x150,0x9b,0x1abb30),(0x119,0x24,0x1ab894)):
        slot=0x1aca08+2*(cmd-0x100);t=0x1aca08+2*struct.unpack('<H',read('cp',slot,2))[0]
        case=dis('cp',t,6);assert case[0]['instruction']==f'movs r0, #{internal:#x}'
        slot2=0x1ab6a6+2*(internal-0x1f);t2=0x1ab6a6+2*struct.unpack('<H',read('cp',slot2,2))[0]
        assert t2==handler
        proof['dispatch'].append({'wire':hex(cmd),'wire_slot':hex(slot),'case':case,'internal':hex(internal),'internal_slot':hex(slot2),'handler':hex(t2)})
    proof['classes']={}
    for name in ('N3VDF31VdfDisplayCmdSetPanelResolutionE','N3VDF28VdfDisplayCmdSetPanelReverseE','14ProcMsgSetPath'):
        b=DATA['cp'];pos=b.index(name.encode()+b'\0');ref=b.index(struct.pack('<I',pos+0x108000));ti=ref+0x108000-4
        vt=b.index(struct.pack('<I',ti))+0x108000+4
        proof['classes'][name]={'name_va':hex(pos+0x108000),'typeinfo':hex(ti),'vtable':hex(vt),
                               'slots':{hex(s):hex(struct.unpack('<I',read('cp',vt+s,4))[0]) for s in (0,4,8,12,16,20)}}
    assert proof['classes']['N3VDF31VdfDisplayCmdSetPanelResolutionE']['slots']['0xc']=='0x5f4823'
    assert proof['classes']['N3VDF28VdfDisplayCmdSetPanelReverseE']['slots']['0x14']=='0x5f4911'
    proof['HDMI_vtables']=[{'vtable':hex(vt),'slots':{hex(s):hex(struct.unpack('<I',read('cp',vt+s,4))[0]) for s in (0x54,0x70,0x80)}}
                           for vt in (0xba5e60,0xba5f18,0xba5fd0,0xba6088,0xba6140,0xba61f8,0xba62b0,0xba6368,0xba6420)]
    proof['GOT']={hex(v):hex(struct.unpack('<Q',read('ap',v,8))[0]) for v in (0x47a6698,0x47c5b68)}
    assert proof['GOT']=={'0x47a6698':'0x2b60208','0x47c5b68':'0x2b5fc68'}
    proof['fps_init']={'table_va':'0x3917900','le32':list(struct.unpack('<5I',read('ap',0x3917900,20))),
                       'backup_id':'0x02cf1493','backup_read':'AP2ec1cb4; one byte; if value7 force index7 for all five calls, otherwise indices0,0,17,17,0'}
    assert proof['fps_init']['le32']==[0,0,17,17,0]
    proof['conditional_pin_request_families']=[
        {'order':'first pass of50 entries','entry':'2ebe12c→2e116e8','business':'1000/0002/24B/flags2','total_with_Dataflow':48,
         'fields':'four original pin input u32s: destination=in+0, body+8=in+4,+12=in+8,+16=in+12,+20=0',
         'expected_reply_header':'0010028020000200','expected_business_bytes':32,'status_offset':24,
         'wait':'2e117dc→2e10c80 timeout-1','failure':'status0 or -26..-24 branch mapping; errors reported; cannot claim disconnected without state change'},
        {'order':'second pass changed entry, query source then destination','entry':'2e113f0/2e11138→2e10d78',
         'business':'1000/0000/24B/flags2','total_with_Dataflow':48,
         'fields':'destination=in+0, body+8=in+4,+12=in+8,+16=in+12,+20=0',
         'expected_reply_header':'0010008020000200','expected_business_bytes':32,
         'status_offset':28,'descriptor_offsets':[8,12,16,20],
         'wait':'2e10e7c→2e10c80 timeout-1','failure':'status0 or -26..-24 branch handling; descriptor has independent validation2e106ec'},
        {'order':'after two successful valid descriptors unless already connected','entry':'2e11688/2e11390→2e10f98',
         'business':'1000/0001/40B/flags2','total_with_Dataflow':64,
         'fields':'destination=sourceDescriptor+0; body sourceDescriptor+4,+8,+12,+0 then destinationDescriptor+4,+8,+12,+0',
         'expected_reply_header':'0010018020000200','expected_business_bytes':32,'status_offset':24,
         'wait':'2e110a4→2e10c80 timeout-1','failure':'nonzero response status→local1, errors logged; no fabricated connection'},
    ]
    # Complete direct call/branch inventory: includes failure paths and model/log calls.
    seq=dis('ap',0x2b66f28,0x2b68330-0x2b66f28)
    proof['sequence_all_calls_and_branches']=[r for r in seq if r['instruction'].split(' ')[0] in ('bl','blr','b','br','ret','cbz','cbnz','tbz','tbnz') or r['instruction'].startswith('b.')]
    assert len(seq)==(0x2b68330-0x2b66f28)//4
    expected_calls={int(x['call'],16):int(x['wrapper'],16) for x in REQUESTS if 'call' in x and 'wrapper' in x}
    for call,target in expected_calls.items():
        assert dis('ap',call,4)[0]['instruction']==f'bl #{target:#x}',(hex(call),hex(target))
    proof['direct_service_call_bindings_checked']=len(expected_calls)
    log=BASE/'runtime/runs/ap78bboot-537976cc/serial.log';lb=log.read_bytes();ls=lb.decode(errors='replace').split('\n')
    proof['sources']['AP78b']={'path':str(log.relative_to(ROOT)),'bytes':len(lb),'sha256':hashlib.sha256(lb).hexdigest(),'LF_records':len(ls)}
    receipts=[]
    for i,l in enumerate(ls):
        if any(s in l for s in ('raw=0d2042010a0001800100','raw=0d205a010a0001800100','raw=0d20450118000180',
                                 'raw=0d201b010a0001800308','raw=0d2060010a0001800000','raw=0d2065010a0001800200')):
            receipts.append({'line':i+1,'text':l,'preceding_stack':[{'line':j+1,'text':ls[j]} for j in range(max(0,i-14),i)],
                             'following':[{'line':j+1,'text':ls[j]} for j in range(i+1,min(i+4,len(ls)))]})
    assert len(receipts)==6
    proof['AP78b_vdf_alignment']=receipts
    proof['AP78b_other_receipts']=[{'line':i+1,'text':l} for i,l in enumerate(ls) if any(s in l for s in ('FX3_TIMECODE_COMMIT','FX3_TIMECODE_REPLY_CONSUMED','FX3_DISPLAY_INFO_COMMIT','target=0x807b002b','target=0x9059000e','FX3_BOOT_REPLY_BOUND'))]
    proof['AP78b_gate_counts']={str(n):sum(f'FX3_BOOT_GATE_SAMPLE id={n} ' in l for l in ls) for n in (16,17,18,22,41)}
    assert proof['AP78b_gate_counts']=={'16':0,'17':0,'18':0,'22':0,'41':0}
    proof['AP78b_late_reply_headers_seen']={f'{op:x}':sum(f'tag1=0x{op:x}200d' in l or f'raw=0d20{op&255:02x}{op>>8:02x}' in l for l in ls) for op in (0x1142,0x115a,0x1145,0x111b,0x1160,0x1165)}
    # Only the captured 165 request is enabled in the finite illustrative model.
    state={'geometry':[640,480],'pending_hardware':False}
    reply=panel_model(bytes.fromhex('0d2065010a0001800200'),state)
    assert reply.hex()==REPLIES['VDF0165']['hex']
    assert state=={'geometry':[640,480],'pending_hardware':True,'selector':2,'size_enum':0,'valid':True}
    rejection=[]
    for p in (b'',bytes.fromhex('0d2065010a0001800201'),bytes.fromhex('0d2065010a0001800100'),
              bytes.fromhex('0d2065010c0001800200'),bytes.fromhex('0d2065010a0001000200'),
              bytes.fromhex('0d2065010a000180020000'),bytes.fromhex('0d206a010a0001800200')):
        before=state.copy()
        try:panel_model(p,state)
        except ValueError:assert state==before;rejection.append(p.hex())
        else:raise AssertionError('unexpected admission')
    proof['finite_software_contract']={'accepted':'0d2065010a0001800200','reply':reply.hex(),'state':state,
                                      'rejected':rejection,'not_runtime_implemented':True,'physical_panel':False}
    for key,v in REPLIES.items():
        if 'hex' in v:
            raw=bytes.fromhex(v['hex']);assert len(raw)==v['bytes'],key
            if v.get('standard_header'):assert struct.unpack_from('<H',raw,4)[0]==len(raw),key
    extra=['runtime/helpers/fx3-capid-v31.c','runtime/helpers/fx3-display-info.c','runtime/helpers/fx3-hdmi-registration-v3.c',
           'runtime/ap78b-timecode-getfunc/build-receipt.json','runtime/ap78b-timecode-getfunc/init-reviewed.sh']
    proof['existing_model_sources']={f:{'sha256':hashlib.sha256((BASE/f).read_bytes()).hexdigest(),'bytes':(BASE/f).stat().st_size} for f in extra}
    proof['external_reference']={'A7C2':{'commit':'b3d7c1fe','url':'https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fe/runtime/analysis/device-models/vdf-device.c',
                                       'checked':'2026-11-02 UTC','agreement':'request0200 and status590000; lines95-168; not used to derive FX3 byte contract'},
                               'tools':['https://www.capstone-engine.org/lang_python.html','https://github.com/ARM-software/abi-aa/blob/2025Q1/aapcs64/aapcs64.rst']}
    volume_check()
    (OUT/'boot-vdf-tail-proof.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'result':'PASS','instruction_checks':len(CHECKS),'direct_service_bindings':len(expected_calls),
                      'sequence_instructions':len(seq),'captured_requests':len(receipts),'unproven':len(UNPROVEN)},ensure_ascii=False))

def panel_model(request,state):
    if request!=bytes.fromhex('0d2065010a0001800200'):raise ValueError('outside captured boot subset')
    state.update(selector=2,size_enum=0,valid=True,pending_hardware=True)
    return bytes.fromhex('0d2065110c00018000005900')

REPLIES={
 'VDF0165':{'bytes':12,'hex':'0d2065110c00018000005900','standard_header':True,'status':'0x590000; original non-normalized VDF display success','evidence':'CP1adcc4/1adcda/1adcde,5c9d58..80; AP2de46c4..cc'},
 'ADF0325':{'bytes':28,'hex':'0d2025131c0001800000000080808080808080808080808080808080','standard_header':True,'status':'software muted capabilities; existing model; no original capability-cache claim','evidence':'AP2dec778..b48; CP1b0a80..1064; boot-barrier-remaining'},
 'HDMI010a':{'bytes':12,'hex':'00250a810c00010001000000','standard_header':True,'status':'1 accepted as success by AP; original inactive state writes1','evidence':'CP65c8da..924; AP2de578c..798'},
 'HDMI0101':{'bytes':12,'hex':'002501810c00010000000000','standard_header':True,'status':'0; inactive shadow accepted; no output connected','evidence':'CP65c440..4ac'},
 'HDMI0117':{'bytes':12,'hex':'002517810c00010000000000','standard_header':True,'status':'0; five serial requests, each needs its own reply','evidence':'CP219834..908'},
 'ADF0328_format_only':{'bytes':12,'hex':'0d2028130c00018000005800','standard_header':True,'status':'legacy status0 | ADF domain580000; NOT admitted until path0/1/3 and silent backend semantics validated','evidence':'CP1b1a8c..b0c,1adc88,5ca218..268'},
 'ADF0329_unused_sync_variant':{'bytes':12,'hex':'0d2029130c00018000005800','standard_header':True,'status':'format only; this boot invocation sets sync flag0, so no sync reply should be added','evidence':'AP2b67dbc,2df5e3c/2df5ecc; CP5ca26a..2ba'},
 'digital_level_format_candidate':{'bytes':24,'hex':'030000000000000000000000000000000000000000000000','status':'op3, software notification registration only; original callback status0 when disabled. Reply transport source/lifecycle remains unproven','evidence':'AP2df2f60..fc0; CP14535a/1454a6,4c8da4..e18'},
 'VDF0119_format_only':{'bytes':12,'hex':'0d2019110c00018000000000','standard_header':True,'status':'0 after normalizing590000; requires actual software orientation application/queue consumption, not mere receipt','evidence':'CP1aeca0..1aed00; old0101→f02e→6073b8'},
}

REQUESTS=[
 {'order':'0','name':'VDF timecode boundary','call':'0x2b66f28','wrapper':'0x2dd0754','implementation':'0x2debbb4','destination':'0x9059000e','command':'2001/0205 in Dataflow','bytes':52,'wait':'sync -1','fields':'sequence+1c4,+1c8; full packet preexisting AP78a whitelist','failure':'nonzero fatal at2b66f30','coverage':'AP78b21429/21431 consumed; audited in svc-9059000e'},
 {'order':'1','name':'black-frame notification','call':'0x2b67020','wrapper':'0x2dd0554','implementation':'0x2deb808','destination':'0x92840747','command':'0x142','bytes':10,'wait':'no-wait 2de66f4','fields':'constant true→byte8=1,byte9=0; source main ID','failure':'local transport assert; parent log only; no completion check','coverage':'AP78b21445..47 delegated'},
 {'order':'2','name':'OSD-mute notification','call':'0x2b6708c','wrapper':'0x2dd0594','implementation':'0x2deb868','destination':'0x92840747','command':'0x15a','bytes':10,'wait':'no-wait 2de66f4','fields':'constant true→0100; source main ID','failure':'parent log only','coverage':'AP78b21462..64 delegated'},
 {'order':'3','name':'shutter mute','call':'0x2b670d8','wrapper':'0x2dd05d4','implementation':'0x2deb8c8','destination':'0x92840747','command':'0x145','bytes':24,'wait':'no-wait 2de83b4','fields':'zeroed16B body; byte11=byte12=1; +16 u32 from global9684068(main ID)','failure':'parent log only; local transport assert','coverage':'AP78b21478..80 delegated'},
 {'order':'4','name':'EVF temperature subscribe','call':'0x2b67124','wrapper':'0x2dd0714','implementation':'0x2debb2c','destination':'0x9059000e','command':'2001/020b in Dataflow','bytes':40,'wait':'no-wait SendASync; free dynamic ID immediately','fields':'business16B +8 global9684068; +12,+13=1; outer24B','failure':'parent log only','coverage':'observer may dedup prior header to same9059000e; no independent full request captured for this invocation'},
 {'order':'5','name':'panel color','call':'0x2b67178','wrapper':'0x2dd0654','implementation':'0x2deb9b8','destination':'0x92840747','command':'0x11b','bytes':10,'wait':'no-wait 2de83b4','fields':'constant8→selector3/color8; header200d/11b/10/8001','failure':'parameter1..16 else status2; parent log only','coverage':'AP78b21494..96 delegated'},
 {'order':'6','name':'touch direction','call':'0x2b671cc','wrapper':'0x2ddfb74','implementation':'0x2eabfd0','destination':'0x807b002b','command':'op32=0','bytes':16,'wait':'no-wait2eace78; dynamic source released','fields':'u32[0,16,map(sequence+304),0], input0..4 maps through399ecb0','failure':'send error status→boot fatal2b671d4','coverage':'AP78b21497 send accepted/delegated; no physical touch proof'},
 {'order':'7','name':'panel-out notification','call':'0x2b67214','wrapper':'0x2dd06d4','implementation':'0x2debacc','destination':'0x92840747','command':'0x160','bytes':10,'wait':'no-wait2de66f4','fields':'constantfalse→0000; source mainID','failure':'parent log only','coverage':'AP78b21512..14 delegated'},
 {'order':'8','name':'panel resolution','call':'0x2b67384','wrapper':'0x2dd0694','implementation':'0x2deba54','destination':'0x92840747','command':'0x165','bytes':10,'wait':'sync2de70a8 -1; reply12','fields':'fixed payload0200; no geometry fields','failure':'reply+8 status→2de4574; nonzero→fatal2b6738c','coverage':'AP78b21515..30 original stack and no reply; next observed blocker','reply_key':'VDF0165'},
 {'order':'9','name':'OSD layout','call':'0x2b673e4','wrapper':'0x2dd0054','implementation':'0x2deb504','destination':'0x92840747','command':'0x150','bytes':20,'wait':'no-wait2de83b4','fields':'model294b8bc firstu32→mapping3963648; +8enum1/2,restzero','failure':'parent2b673ec nonzero fatal, but wrapper always status0 aftersend','coverage':'not reached in AP78b'},
 {'order':'10','name':'touch sensitivity','call':'0x2b6758c','wrapper':'0x2ddfaf4','implementation':'0x2eabcdc','destination':'0x807b002b','command':'op32=2','bytes':12,'wait':'no-wait2eace78','fields':'u32[2,12,(sequence+1f8==1?1:2)]; input0/1 only','failure':'send error→fatal2b67594','coverage':'not reached'},
 {'order':'11a concurrent after create2b67674','name':'ADF getfunc','call':'0x2b60264','wrapper':'0x2dd0c94','implementation':'0x2dec778','destination':'0x92840747','command':'0x325','bytes':8,'wait':'sync-1; reply28','fields':'fixed0d20250308000180','failure':'status→fatal2b6026c; then original MPR path mustfinish','coverage':'existingv31 model enabled; AP78b getfunc notcreated','reply_key':'ADF0325'},
 {'order':'11b','name':'HDMI definitionHD','call':'0x2b676a0','wrapper':'0x2dd1394','implementation':'0x2df7b14','destination':'0x909a015a','command':'2500/010a','bytes':12,'wait':'sync-1; reply12','fields':'constantbody00000000 from2df7914','failure':'reply+8→convert_hdmi_err; parentfatal2b676a8','coverage':'not reached; current HDMI models support127/102/109 only','reply_key':'HDMI010a'},
 {'order':'12','name':'HDMI init resolution','call':'0x2b67794','wrapper':'0x2dd1214','implementation':'0x2df6ce4','destination':'0x909a015a','command':'2500/0101','bytes':16,'wait':'sync-1; reply12','fields':'00000000 06050000 from2df6c98; no640x480pixels','failure':'parentfatal2b6779c','coverage':'not reached; not currently modeled','reply_key':'HDMI0101'},
 {'order':'13','name':'HDMI init frame rates×5','call':'0x2b678dc','wrapper':'0x2dd1254','implementation':'0x2df7188','destination':'0x909a015a','command':'2500/0117','bytes':12,'wait':'five serialsync-1; eachreply12','fields':'byte8=byte10=port0..4; byte9=byte11=0/17 table or7 ifBackup02cf1493==7','failure':'nonzero→fatal2b67c30','coverage':'not reached; not currently modeled','reply_key':'HDMI0117'},
 {'order':'14','name':'change_mode pin topology','call':'0x2b67a44','wrapper':'0x2de1f84','implementation':'0x2ebe9c0','destination':'state-dependent; Dataflow provider','command':'conditionalpin1000/0,1,2 and consumer/source checks','bytes':'business24..40 +outer24','wait':'local change_mode may call syncDataflow -1 up to50 changedpins','fields':'sequence+1c4,+1c8,+28c,+600,+620; topology tables selected bymode/option, old50-entry state9ab0d70','failure':'parent no directstatuscheck; lower helper assertions/errors','coverage':'not reached; actual selected50-entry topology and endpoints unobserved; not aVDF command'},
 {'order':'15','name':'four-task barrier','call':'0x2b67a6c','wrapper':'0x2b6353c','destination':'sequence internaldeque','command':'none','bytes':4,'wait':'conditionvariable - no wire reply','fields':'four distinct actual handles;token2000specialexit','failure':'mismatchassert; duplicates forbidden bymodelcontract','coverage':'AP78b not reached'},
 {'order':'16','name':'ADF systempath','call':'0x2b67aa0','wrapper':'0x2dd1014','implementation':'0x2dee6f0','destination':'0x92840747','command':'0x328','bytes':10,'wait':'sync-1; reply12','fields':'sequence+1e4,+1ec→pathbyte0/1/3; +9zero','failure':'reply+8converted; parentfatal2b67aa8','coverage':'not reached; not currently modeled','reply_key':'ADF0328_format_only'},
 {'order':'17 conditional','name':'ADF system soundrequest','call':'0x2b67dd4','wrapper':'0x2dd1794','implementation':'0x2df5de0','destination':'0x92840747','command':'0x329','bytes':16,'wait':'THIS call no-wait (input+8=0 at2b67dbc); syncvariant exists butunused','fields':'if2b5fea4(inputsequence+208..228) && sequence+1f0==0: body+8=1,+10model2946508+791,+12u32=0','failure':'parent logonly; original increments system_sound_request_num','coverage':'not reached; do not add1329 for this invocation'},
 {'order':'18','name':'digital levelnotify','call':'0x2b67b2c','wrapper':'0x2dd2194','implementation':'0x2df2f60','destination':'0x912f0335','command':'u32=3','bytes':24,'wait':'sync-1; reply24','fields':'true→op3,remaining20Bzero; note wrapper checks INPUT+16 (zero), not reply+16','failure':'parentfatal2b67b34 iflocalstatusnonzero; no timeout','coverage':'not reached; CPcallback145330 cases3/4; noVDF mapping','reply_key':'digital_level_format_candidate'},
 {'order':'19','name':'key rollquad subscribe','call':'0x2b67b70','wrapper':'0x2dd4534','implementation':'0x2e1407c','destination':'0x91170319','command':'4B 64800501','bytes':4,'wait':'no-waitosal_snd_msg','fields':'constantKEY_OTHER_ROLL_QUAD_POSITION','failure':'status→fatal2b67b78','coverage':'not reached'},
 {'order':'20','name':'video lightmode','call':'0x2b67ee8','wrapper':'0x2dd6b54','implementation':'0x2e38cb0','destination':'0x90030001','command':'imaging4051','bytes':12,'wait':'no-wait becauseoutptr0→2e2fdd0..fe00','fields':'u8type5,u16cmd4051,u32sequence+1c0,zero4Bpayload','failure':'parentlogonly; sendfailurelowerassert','coverage':'not reached; source80020002'},
 {'order':'21','name':'hotshoe videolight','call':'0x2b67f34','wrapper':'0x2dd6b94','implementation':'0x2e38c38','destination':'0x90030001','command':'imaging40c5','bytes':12,'wait':'no-wait','fields':'same type5/id+1c0,zero4Bpayload','failure':'parentlogonly','coverage':'not reached'},
 {'order':'22','name':'eyeAF','call':'0x2b67f6c','wrapper':'0x2dd6e94','implementation':'0x2e38480','destination':'0x90030001','command':'imaging4102','bytes':12,'wait':'no-wait','fields':'id+1c0; inputmode0→bodybyte1','failure':'parentlogonly','coverage':'not reached'},
 {'order':'23','name':'face regardlessmenu','call':'0x2b67fac','wrapper':'0x2dd6ed4','implementation':'0x2e38358','destination':'0x90030001','command':'imaging40ed','bytes':12,'wait':'no-wait','fields':'id+1c0; inputmode0→bodybyte1','failure':'parentlogonly','coverage':'not reached'},
 {'order':'24 conditional','name':'exposurebias','call':'0x2b6807c','wrapper':'0x2dd5a14','implementation':'0x2e3c5e8','destination':'0x90030001','command':'imaging4048','bytes':12,'wait':'no-wait','fields':'ifsequence+1fc==1: id+1c0,20,+200→conversion2e18b6c','failure':'parentlogonly','coverage':'not reached'},
 {'order':'25a concurrent','name':'panelreverse worker','call':'0x2b5fcb4','wrapper':'0x2dd0894','implementation':'0x2dec02c','destination':'0x92840747','command':'0x119','bytes':28,'wait':'sync-1; reply12; parentlater2b681e4 awaitsactualworkerhandle','fields':'sequence+304 enum0..5→bytes8..10 via3963654; restzero','failure':'worker logonly then completes; noresponse preventsworkerreturn','coverage':'not reached; childcreated2b680c0; notmodeled','reply_key':'VDF0119_format_only'},
 {'order':'25b','name':'DMM getunitsize','call':'0x2b680e4','wrapper':'0x2dda534','implementation':'0x2e4fecc','destination':'0x9061003c','command':'u16=0x18','bytes':40,'wait':'sendthenreceive-1 only ifsendreturns0','fields':'unit0x00050b58; secondaryCPflag1; requestbodyallzerootherwise','failure':'negative send→outsize0; parentlogonly; existingmodel rejects18 immediately-1024, so no waitentered','coverage':'not reached; currentremoteDMMsupports20..23/2a, not18; do not inventunitsize'},
 {'order':'26','name':'AF framesizeinfo','call':'0x2b6818c','wrapper':'0x2dd81d4','implementation':'0x2e31cd8','destination':'0x90030001','command':'imaging4139','bytes':184,'wait':'no-wait','fields':'id+1c0; copy176Bcachedglobal9684e20 tobody+8','failure':'parentnoresultcheck; lowerassertontransport','coverage':'not reached'},
 {'order':'27 conditional','name':'ObserveDictionaryInfraStatus','call':'0x2b681b8','wrapper':'0x2de2e04','implementation':'0x2de4394','destination':'none','command':'none','bytes':0,'wait':'localstubstrwzr;ret','fields':'onlyif16f0ea0!=0','failure':'none inactualstub','coverage':'not reached; noRPC'},
 {'order':'28','name':'await panelreverse','call':'0x2b681e4','wrapper':'0x2b63718','destination':'internaldeque','command':'none','bytes':4,'wait':'conditionvariable','fields':'handlefrom2b680c4;token2000specialexit','failure':'mismatchassert; noexternalcompletionpacket','coverage':'not reached'},
 {'order':'29','name':'notify main bootcontroller','call':'0x2b6838c','wrapper':'0x2aa1668','destination':'sequence+1b8 localCV','command':'none','bytes':0,'wait':'localnotify_one','fields':'afterrun_i returns, optional71 featuremounts/dev/nflasha30→/usr/data/lut at2b68384','failure':'not a service reply; noforcednotify','coverage':'AP78b id41=0'},
]

UNPROVEN=[
 'AP78b has no post165 execution: future request payloads/source IDs/port backup value and success receipts remain unobserved.',
 'change_mode can emit conditional Dataflow getpin/connect/disconnect across selected50-entry topology; current topology and provider states not captured. No exact safe positive reply can be given without truthful endpoint ownership.',
 'getfunc worker post325 MPR calls and their transitive storage/backend contracts remain as bounded in boot-barrier-remaining;1325 alone is not taskcompletion.',
 'Digital-level CPcallback and statusstore are bound, but full generic OSAL callback automatic reply transport/lifecycle not closed; candidate24B is explicitly format-only.',
 'ADF0328 original0202 system path completion/cache/hardware dependencies and full wiredecoder are not closed.1328 format is proven, success cannot be admitted solely from request arrival.',
 'VDF0119 f02e downstream true device reverse completion callback chain not fully closed.6073b8 constructs1101; physical rotation/frame acceptance unproven.',
 'VDF0165 size enum0 exact pixel meaning not recovered. No original link proves it changes or must numerically equal016a640x480; no dimensions in1165.',
 'No runtime/hardware/menu/firstdraw acceptance; bounded Python panelcontract checks are not originalcode execution.',
]

BLOCKS={
 'ap':[(0x2b66f28,0x1408),(0x2b68330,0x60),(0x2b6353c,0x148),(0x2b63718,0x1a0),(0x2b5fc68,0x98),
       (0x2deba54,0x78),(0x2deb808,0x3ac),(0x2de66f4,0x130),(0x2de70a8,0x2a0),(0x2de83b4,0x24c),(0x2de4574,0x170),
       (0x2deb504,0x8c),(0x2eabfd0,0x19c),(0x2eabcdc,0x17c),(0x2eace78,0xa0),
       (0x2df7b14,0x90),(0x2df7914,0x38),(0x2df6c98,0xf4),(0x2df7124,0xf4),(0x2de7348,0x1c),(0x2de5720,0xfc),(0x2ec1c90,0x3c),
       (0x2dee6f0,0x1ac),(0x2df5de0,0x100),(0x2df2f60,0xf4),(0x2e1407c,0xa0),(0x2e4fecc,0x274),(0x2dec02c,0x190),
       (0x2e38c38,0xf0),(0x2e38358,0x250),(0x2e3c5e8,0x7c),(0x2e31cd8,0xa0),(0x2e2fb90,0x2a4),(0x2de4394,8),
       (0x2ebe9c0,0x2fc),(0x2ebe188,0x524),(0x2ebe12c,0x5c),(0x2e113f0,0x2f8),(0x2e10d78,0x200),(0x2e116e8,0x1b8),
       (0x2e11138,0x2b8),(0x2e10f98,0x1a0),(0x2b60208,0x5d0),(0x2dec778,0x3d0)],
 'cp':[(0x1b58b4,0x104),(0x5c9d3a,0x52),(0x5f4822,0xc8),(0x60c5b6,0x5e),(0x5df0d6,0x38),(0x60f17c,0x2c),
       (0x1adbd4,0xc6),(0x1adcc4,0x22),(0x1ac752,0xc),
       (0x6599de,0x3b0),(0x2178e0,0x78),(0x217bb0,0x2a),(0x217f4c,0x70),(0x659f5e,0x32),(0x65a08e,0x36),(0x65a202,0x36),
       (0x65c8da,0x4c),(0x65c440,0x6e),(0x219834,0xd6),
       (0x1b1a8c,0x82),(0x1b1b48,0x14a),(0x5ca218,0xa4),(0x1b3e74,0x2de),(0x5f48ee,0x9c),(0x1aeca0,0x6e),(0x6073b8,0x74),
       (0x4c8908,0xcc),(0x4c8ee0,0x28),(0x145330,0x1ec),(0x4c8da4,0x7e)],
}

CHECKS=[
 ('ap',0x2debaa0,'mov w0, #2'),('ap',0x2debab0,'bl #0x2de70a8'),('ap',0x2debab4,'ldr w0, [x29, #0x38]'),
 ('ap',0x2de72fc,'mov w2, #-1'),('ap',0x2de7300,'bl #0x1592de0'),('ap',0x2de7314,'bl #0x1591c40'),
 ('ap',0x2de46c4,'cmp w0, #0x590, lsl #12'),('ap',0x2de46cc,'mov w19, #0'),
 ('ap',0x2deb854,'bl #0x2de66f4'),('ap',0x2deb8b4,'bl #0x2de66f4'),('ap',0x2deb924,'bl #0x2de83b4'),
 ('ap',0x2deba14,'bl #0x2de83b4'),('ap',0x2debb18,'bl #0x2de66f4'),('ap',0x2debb98,'bl #0x2e109d0'),
 ('ap',0x2deb574,'bl #0x2de83b4'),('ap',0x2eacea0,'bl #0x1592f10'),
 ('ap',0x2b67674,'bl #0x2b63224'),('ap',0x2b67a6c,'bl #0x2b6353c'),('ap',0x2b680c0,'bl #0x2b63224'),
 ('ap',0x2b681e4,'bl #0x2b63718'),('ap',0x2b6838c,'bl #0x2aa1668'),
 ('ap',0x2df7b88,'bl #0x2de70a8'),('ap',0x2df6d70,'bl #0x2de70a8'),('ap',0x2df71f8,'bl #0x2de7348'),
 ('ap',0x2dee798,'bl #0x2de70a8'),('ap',0x2b67dbc,'strb wzr, [x29, #0xf8]'),('ap',0x2df5ed4,'bl #0x2de66f4'),
 ('ap',0x2df2fbc,'bl #0x2de70a8'),('ap',0x2df2fc0,'ldr w19, [x29, #0x50]'),
 ('ap',0x2e2fdd0,'cbz x22, #0x2e2fe00'),('ap',0x2de4394,'str wzr, [x1]'),('ap',0x2dec0ec,'bl #0x2de70a8'),
 ('cp',0x1b58c2,'mov.w r1, #0x118'),('cp',0x5f4828,'mov.w r0, #0x118'),('cp',0x5f488c,'cmp r0, #3'),
 ('cp',0x5f489c,'bl #0x60c5b6'),('cp',0x5f48b4,'blx ip'),('cp',0x5f48c4,'blx r2'),
 ('cp',0x1adcc4,'ldr r0, [r0, #8]'),('cp',0x1adcda,'mov.w r2, #0x590000'),('cp',0x1adcde,'orrs r0, r2'),
 ('cp',0x5c9d58,'movw r0, #0x1165'),('cp',0x5c9d7a,'str r5, [sp, #0xc]'),
 ('cp',0x65c918,'str r1, [sp, #0xc]'),('cp',0x65c902,'movw r1, #0x810a'),
 ('cp',0x65c488,'movw r1, #0x8101'),('cp',0x2198e0,'movw r1, #0x8117'),
 ('cp',0x5ca236,'movw r0, #0x1328'),('cp',0x5ca288,'movw r0, #0x1329'),
 ('cp',0x1aecb0,'cmp.w r6, #0x590000'),('cp',0x1aecd8,'movw r0, #0x1119'),
 ('cp',0x5f4946,'movt r0, #0xf02e'),('cp',0x6073e0,'movw r0, #0x1101'),
 ('cp',0x14535c,'bl #0x4c8da4'),('cp',0x1454a6,'str.w r5, [r8, #0x10]'),
]

if __name__=='__main__': main()
