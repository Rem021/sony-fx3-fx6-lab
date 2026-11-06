"""Bind current restart request and historical updater reboot separately, statically."""
from pathlib import Path
from hashlib import sha256
from io import BytesIO
import json,struct,os
from elftools.elf.elffile import ELFFile
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN
H=Path(__file__).resolve().parent;B=H.parent;R=B.parents[1]
OBJ=B/'stage201-updater-request-endpoint/originals/7.02-main/lib/libObj.so'
assert sha256(OBJ.read_bytes()).hexdigest()=='c4681d209a7fe2ed63752be3b0be89ab7b7ce400679c00068c8c6e47d39f83ae'
sources={'Obj':OBJ,'UPM':H/'originals/kmod/upm.ko','Core':H/'originals/lib/libupdatercorecommon.so','OldReboot':H/'historical/2.05/ud_reboot.elf'}
assert sha256(sources['UPM'].read_bytes()).hexdigest()=='ba0cca76ec8e19836697d69d0851c5a0bd2c2eea98ee2aa54d1eff3408f1ec8e'
assert sha256(sources['OldReboot'].read_bytes()).hexdigest()=='314725816b8a251500eb38b001ab8bd8449f6560753db4090658086331586d7a'
ELF={k:ELFFile(BytesIO(p.read_bytes())) for k,p in sources.items()}
def get(k,a,n,section=None):
    e=ELF[k]
    if section:return e.get_section_by_name(section).data()[a:a+n]
    raw=sources[k].read_bytes()
    seg=[s for s in e.iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=a and a+n<=s['p_vaddr']+s['p_filesz']];assert len(seg)==1
    s=seg[0];off=s['p_offset']+a-s['p_vaddr'];return raw[off:off+n]
md=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN);md.skipdata=True;cuts=[]
def pin(k,a,z,label,section=None,code=True):
    e=ELF[k];raw=get(k,a,z-a,section);assert len(raw)==z-a;notes={};symbols={}
    if section:
        rs=e.get_section_by_name('.rela'+section)
        if rs:
            st=e.get_section(rs['sh_link'])
            for r in rs.iter_relocations():
                s=st.get_symbol(r['r_info_sym']);idx=s['st_shndx'];sn=e.get_section(idx).name if isinstance(idx,int) else idx
                notes[r['r_offset']]=dict(symbol=s.name,section=sn,symbol_value=hex(s['st_value']),addend=hex(r['r_addend']),type=r['r_info_type'])
    else:
        rs=e.get_section_by_name('.rela.plt');plt=e.get_section_by_name('.plt')
        if rs and plt:
            st=e.get_section(rs['sh_link']);symbols={plt['sh_addr']+32+16*n:st.get_symbol(r['r_info_sym']).name for n,r in enumerate(rs.iter_relocations())}
    lines=[]
    if code:
        ins=list(md.disasm(raw,a));assert sum(i.size for i in ins)==len(raw)
        for i in ins:
            dst=int(i.op_str[1:],16) if i.mnemonic in ['bl','b'] and i.op_str.startswith('#') else -1
            extra=' ; '+symbols[dst] if dst in symbols else ''
            if i.address in notes:extra+=' ; relocation '+str(notes[i.address])
            if i.mnemonic=='ldr' and '[' not in i.op_str and '#' in i.op_str:
                lit=int(i.op_str.split('#')[-1],16)
                if lit in notes:extra+=' ; literal relocation '+str(notes[lit])
            lines.append(f'{i.address:08x} {i.bytes.hex()} {i.mnemonic:8} {i.op_str}{extra}')
    else:lines=[f'{a:08x} DATA {raw.hex()}']
    out=H/'pins'/(label+'.txt');out.parent.mkdir(exist_ok=True);out.open('x').write('\n'.join(lines)+'\n')
    cuts.append(dict(key=k,source=str(sources[k]),source_sha256=sha256(sources[k].read_bytes()).hexdigest(),section=section,address_kind='section_offset' if section else 'source_ELF_VA',start=hex(a),end_exclusive=hex(z),bytes=len(raw),sha256=sha256(raw).hexdigest(),data_not_code=not code,output=str(out)))
for args in [
 ('Obj',0xce4bc,0xce530,'AP-hot-request'),('Obj',0xce530,0xce5a4,'AP-cold-request'),('Obj',0xcdbbc,0xcdc68,'AP-power-message'),
 ('Obj',0xedc44,0xedcdc,'SEN604-dispatch'),('Obj',0x1dd6c8,0x1dd6f4,'SEN604-command-table',None,False),
 ('Obj',0xedfec,0xedff8,'SEN604-command5'),('Obj',0xed4a8,0xed4fc,'SEN604-reboot-wrapper'),
 ('Core',0xb6cc,0xb840,'Core-switch-updater'),
 ('UPM',0x378,0x3f8,'UPM-queue21-thread','.text'),('UPM',0x9628,0x97a0,'UPM-off-api','.text'),
 ('UPM',0x9450,0x9530,'UPM-state-dispatch','.text'),('UPM',0x6698,0x6b10,'UPM-active-off-state','.text'),
 ('OldReboot',0x4014f8,0x401524,'old-reboot-entry'),('OldReboot',0x401528,0x401530,'old-reboot-main-pointer',None,False),
 ('OldReboot',0x400d90,0x400db8,'old-reboot-power-selector'),('OldReboot',0x4019e0,0x4019ee,'old-reboot-power-table',None,False),
 ('OldReboot',0x401464,0x4014b8,'old-reboot-frame11-3'),('OldReboot',0x401214,0x401268,'old-reboot-SIO-write')]:pin(*args)
def sx(v,b):return v-(1<<b) if v&(1<<(b-1)) else v
def w(k,a,section=None):return struct.unpack('<I',get(k,a,4,section))[0]
def branch(k,a,t,section=None,link=False):
    word=w(k,a,section);assert word&0xfc000000==(0x94000000 if link else 0x14000000);assert a+sx(word&0x3ffffff,26)*4==t
checks=[]
branch('Obj',0xce52c,0xcdbbc);branch('Obj',0xce5a0,0xcdbbc);checks.append('hot/cold tail branches to common power-message builder')
for a,expected in [(0xce524,'61038052'),(0xce528,'80118052'),(0xce598,'81038052'),(0xce59c,'e0008052')]:
    assert get('Obj',a,4).hex()==expected
checks.append('hot fields0x8c/0x1b and cold7/0x1c are original constants')
assert get('Obj',0xcdbec,4).hex()=='20048052' and get('Obj',0xcdbfc,4).hex()=='4012b072'
assert get('Obj',0xcdc20,4).hex()=='20288052' and get('Obj',0xcdc24,4).hex()=='4012a072'
checks.append('queue0x80920021 and message0x00920141 original MOV/MOVK fields')
assert get('Obj',0xcdc28,4).hex()=='20580029' and get('Obj',0xcdc30,4).hex()=='35500129'
checks.append('message stores first word/reason and event/argument in16B layout')
assert get('UPM',0x384,4,'.text').hex()=='34048052' and get('UPM',0x388,4,'.text').hex()=='5412b072'
rs=ELF['UPM'].get_section_by_name('.rela.text');st=ELF['UPM'].get_section(rs['sh_link']);rel={r['r_offset']:st.get_symbol(r['r_info_sym']).name for r in rs.iter_relocations()}
assert rel[0x39c]=='osal_rcv_msg_tmo' and rel[0x3e4]=='k_upm_api_off_factor_async';checks.append('matching queue21 thread receives then calls off-factor API')
assert rel[0x9760]=='k_upm_off_factor_handler' and rel[0x94c0]=='k_upm_off_factor_handler_active';checks.append('off API and state-specific off dispatch bound by relocation')
table=[0xedcdc+struct.unpack_from('<h',get('Obj',0x1dd6c8,44),2*i)[0]*4 for i in range(22)]
assert table[1]==0xedd44 and table[5]==0xedfec
branch('Obj',0xedff0,0xed4a8,link=True);checks.append('SEN604 command5 branches to wrapper invoking historical script path')
assert struct.unpack('<Q',get('OldReboot',0x401528,8))[0]==0x400d30
word=w('OldReboot',0x401510);assert word&0xff00001f==0x58000000 and 0x401510+sx((word>>5)&0x7ffff,19)*4==0x401528
checks.append('historical reboot ELF entry literal identifies main0x400d30')
power_table=[0x400db8+struct.unpack_from('<h',get('OldReboot',0x4019e0,14),2*i)[0]*4 for i in range(7)];assert power_table[6]==0x401030
checks.append('power IC7 selects historical source Darwin branch at0x401030')
assert get('OldReboot',0x40148c,16).hex()=='200280522043053960008052e0060039';checks.append('historical reboot constructs frame first bytes0x11/3, separate from update0x11/4')
script=(H/'historical/2.05/us_reboot.sh').read_text();assert 'ud_pd_firmup.elf b ||' in script and 'ud_reboot.elf      ||' in script;checks.append('historical shell orders PD helper b before reboot helper')
put=lambda n,v:(H/n).open('x').write(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
put('restart-route-proof.json',dict(selected_original_ranges=cuts,raw_checks=checks,raw_check_count=len(checks),
    current_AP_restart_request=dict(logical_queue='0x80920021',message_first_word='0x00920141',hot_fields=[140,27,'nonzero caller argument'],cold_fields=[7,28,'nonzero caller argument'],
      receiver_section_offset='UPM.text+0x378',consumer='k_upm_api_off_factor_async',later='k_upm_off_factor_handler, selected by existing runtime state',
      request_enqueue_return_not_completed_restart=True,actual_request_sent=False),
    SEN604=dict(table_VA='0x1dd6c8',command1_target='0xedd44',command5_target='0xedfec',reboot_wrapper='0xed4a8',script='/usr/bin/us_reboot.sh',
      mode_setting_and_reboot_are_separate_commands=True,command5_runtime_script_availability_unverified=True),
    historical_p1_reboot=dict(version='2.05 reference, not current installed p1',main='0x400d30',power_IC7_target='0x401030',logical_frame=[17,3],frame_bytes=128,
      needs_running_AP_Linux_SIO_GPIO_and_Backup=True,not_bootstrap_for_dead_AP=True,current_body_power_IC_observed=False),
    limitations=['no claim that current update preparation invokes the hot/cold wrapper; caller linkage remains separate',
      'current UPM route requires live kernel queues, state machine and semaphore progress; no hardware power/reset receipt',
      'historical p1 helper source does not attest current p1, bus delivery, power IC or actual reboot',
      'GPL7.00 GPIO reset reference not matched to current7.02 runtime; do not convert it to a user-actionable entry',
      'early AP p1/p3 selection, independent inverse writes and target HEVC recording remain unproven'],
    original_or_guest_execution=False,root_or_device_operations=0))
put('analysis-corrections.json',dict(corrections=[
    'Initial restart filename scan covered p15 only; checked saved p3-initrd/p7/Ubody inventories separately before discussing script availability.',
    'UPM rodata0x2c8 was explored as a handler table. Its relocation actually targets rodata.str1.8+0x10e8, the name UPM_CMD_OFF_FACTOR, not code. Disassembly of text+0x10e8 in an exploratory locator is not consumer evidence.',
    'Actual queue21 consumer was instead bound by receive-thread code and text relocation at0x3e4.',
    'GitHub API requests ended in TLS/timeout errors; no HEAD/tree freshness claim from failed requests. Web-read main documentation and saved fixed commits are labeled separately.',
    'WFI-selfloop search is a locator filter only; absence of a selected GPIO signature is not absence of a reset implementation.'
],original_or_guest_execution=False,root_or_device_operations=0))
print(json.dumps(dict(source_ranges=len(cuts),raw_checks=len(checks),SEN604_command5=hex(table[5]),historical_power_IC7=hex(power_table[6]),device_execution=0)))
