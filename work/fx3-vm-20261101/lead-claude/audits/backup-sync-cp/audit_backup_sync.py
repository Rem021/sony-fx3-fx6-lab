#!/usr/bin/env python3
"""Read-only FX3 CP Backup sync audit; only adjacent proof JSON is written."""
import sys
sys.dont_write_bytecode = True
import hashlib, io, json, plistlib, re, struct, subprocess
from pathlib import Path
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM, CS_ARCH_ARM, CS_MODE_THUMB
from elftools.elf.elffile import ELFFile

ROOT = Path('/Volumes/KAFU2T/AI/Projects/Mac')
VM = ROOT/'work/fx3-vm-20261101/menu-repair-01'
RT = VM/'runtime'
LIB = VM/'original-uipc/ap-projection/regular-files/usr/lib'
RUN = RT/'runs/ap99r2cpdate600-9391e358'
OUT = Path(__file__).resolve().parent
assert OUT == ROOT/'work/fx3-vm-20261101/lead-claude/audits/backup-sync-cp'
UUID = 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID'] == UUID
PATHS = {
 'ap': LIB/'appFw.so', 'libbackup': LIB/'libbackup.so',
 'backup': VM/'original-uipc/original-modules/backup.ko',
 'cp': ROOT/'work/sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin',
 'kernel': ROOT/'work/sony-firmware-20261024/stage47-runtime-provider-binding/official-files/nflasha3/vmlinux.bin',
 'seed': VM/'original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin',
 'ram': RUN/'backup-reserved-ram.bin', 'serial': RUN/'serial.log',
 'owner': RT/'helpers/fx3-cp-backup-reset-v3-date99.c',
 'core': RT/'helpers/fx3-cp-backup-reset-core-v1.h',
 'profile': RT/'helpers/fx3-cp-backup-profile-v1.h',
 'init': RT/'ap99-r2-user-backup-nread/init-reviewed.sh', 'command': RUN/'command.json',
}
PINS = {
 'ap':'545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f',
 'libbackup':'6a3c5f6067620c00d790cbe520844acdbb721fa5d0e7433b00a227f922ab9d0d',
 'backup':'8a8d8c949699c130c116d0006806d8b7f92b20869c92a72876529a2001d60c4d',
 'cp':'c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba',
 'kernel':'da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c',
 'seed':'bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2',
 'ram':'2cb74fbfd8a1a4662da8084aea16199231701d90406e2d0d247883fcb0cc3fe4',
 'serial':'304d314a1f401ae2372e0b324ba70622ad033b6c5c68c22f590c5c30e5072804',
 'owner':'0278c729278abe31acd836ff0741ace144717f75738c9fd040cf066938536276',
 'core':'bf84adc665f2dc109d9c275cefa88ec520602c55cc4d65ec95f5ef06fde22463',
 'profile':'6d297bb203960bc01af5b4c67570f218f69ab5640f65d9d1806ce90138b233d6',
 'init':'37f6d91e55ef8ad61931d0bf980ee62cb9e0bb4c943a208d29e82fb7920faec3',
 'command':'e374494479cb218bae1b15d320cef626cd4fcc6fd6801ab69abe3af3909a1f0f',
}
SERIAL_LF = 61400
KBASE = 0xffffff8008080000
CPBASE = 0x108000
SOURCES = {}
def sha(b): return hashlib.sha256(b).hexdigest()
def source(name):
    b = PATHS[name].read_bytes()
    if name == 'serial':
        lines = b.split(b'\n'); assert len(lines) > SERIAL_LF
        b = b'\n'.join(lines[:SERIAL_LF])+b'\n'
    assert sha(b) == PINS[name], f'input drift: {name}'
    SOURCES[name] = {'path':str(PATHS[name]),'bytes':len(b),'sha256':sha(b)}
    if name == 'serial': SOURCES[name]['LF_prefix_lines'] = SERIAL_LF
    return b

class Image:
    def __init__(self, name):
        self.name = name; self.raw = source(name); self.reloc = {}; self.plt = {}; self.symbols = {}
        self.cs = Cs(CS_ARCH_ARM,CS_MODE_THUMB) if name == 'cp' else Cs(CS_ARCH_ARM64,CS_MODE_ARM)
        self.cs.skipdata = True
        if name in ('cp','kernel'): return
        self.elf = ELFFile(io.BytesIO(self.raw))
        self.segs = [s for s in self.elf.iter_segments() if s['p_type']=='PT_LOAD']
        sy = self.elf.get_section_by_name('.symtab' if name=='backup' else '.dynsym')
        if sy: self.symbols = {s.name:dict(s.entry) for s in sy.iter_symbols() if s.name}
        if name == 'backup':
            self.text = self.elf.get_section_by_name('.text')
            for r in self.elf.get_section_by_name('.rela.text').iter_relocations():
                s = sy.get_symbol(r['r_info_sym'])
                self.reloc[r['r_offset']] = {'symbol':s.name,'section':s['st_shndx'],
                    'value':hex(s['st_value']),'addend':r['r_addend'],'type':r['r_info_type']}
        rel = self.elf.get_section_by_name('.rela.plt')
        if rel:
            sy = self.elf.get_section(rel['sh_link']); a = self.elf.get_section_by_name('.plt')['sh_addr']
            self.plt = {a+32+16*i:sy.get_symbol(r['r_info_sym']).name for i,r in enumerate(rel.iter_relocations())}
    def offset(self, a, n):
        if self.name=='cp': o = a-CPBASE
        elif self.name=='kernel': o = a-KBASE
        elif self.name=='backup': o = self.text['sh_offset']+a; assert a+n<=self.text['sh_size']
        else:
            s=next(s for s in self.segs if s['p_vaddr']<=a and a+n<=s['p_vaddr']+s['p_filesz'])
            o=s['p_offset']+a-s['p_vaddr']
        assert 0<=o and o+n<=len(self.raw)
        return o
    def read(self,a,n): o=self.offset(a,n); return self.raw[o:o+n]
    def dis(self,a,n):
        out=[]
        for i in self.cs.disasm(self.read(a,n),a):
            r={'va':hex(i.address),'raw':i.bytes.hex(),'asm':(i.mnemonic+' '+i.op_str).strip()}
            if i.address in self.reloc:r['relocation']=self.reloc[i.address]
            if i.mnemonic in ('b','bl') and i.op_str.startswith('#'):
                t=int(i.op_str[1:],16)
                if t in self.plt:r['symbol']=self.plt[t]
            out.append(r)
        return out
    def window(self,a,n):
        return {'start':hex(a),'bytes':n,'file_offset':hex(self.offset(a,n)),
                'raw':self.read(a,n).hex(),'instructions':self.dis(a,n)}

BLOCKS = {
 'backup':[(0x11c0,0x970),(0x2ba8,0xf8),(0x3010,0x128),(0x5988,0x110),
           (0x5d40,0x10c),(0x5e30,0x1c),(0x6800,0x298),(0x7030,0x190),
           (0x7e40,0x40),(0x5880,0x110),(0x6540,0x168),(0x7b70,0x20)],
 'cp':[(0x4986b4,0x44),(0x498832,0x1c),(0x4988dc,0x86),(0x4989d4,0x134),
       (0xa85434,0x36),(0xa85482,0x90),(0x498550,0x68),(0xa878d2,8)],
 'ap':[(0x2b04674,0x19c),(0x2b2378c,0x9c),(0x2ebf650,0x34),(0x2b22cc8,0x28)],
 'libbackup':[(0x2294,0x34),(0x1a10,0x138)],
 'kernel':[(0xffffff80083220c8,0x168),(0xffffff8008321ff0,0xd8),
           (0xffffff8008321e80,0x100),(0xffffff80083227d4,0x28),
           (0xffffff800839bb98,0x38)],
}
CHECKS = {
 'backup':{0x2bb0:'mov w4, w0',0x2bc4:'mov w3, #3',0x2bc8:'mov x6, #1',
  0x2bcc:'mov x5, #0',0x2bd8:'mov w2, #0x30',0x2be0:'bl #0x11c0',
  0x2be8:'cbnz w3, #0x2c78',0x2bf0:'cbnz w0, #0x2c58',0x2c08:'mov x4, #0',
  0x2c1c:'bl #0x11c0',0x2c20:'ldr w19, [x29, #0x2c]',0x2c74:'b #0x2bf4',
  0x2c90:'b #0x2bec',0x1690:'mov w23, #0x28',0x1694:'mov w19, #1',
  0x169c:'str w1, [x29, #0x1b8]',0x16a0:'str wzr, [x29, #0x1e0]',
  0x16a4:'str w3, [x29, #0x260]',0x16a8:'str wzr, [x29, #0x2e0]',
  0x12b8:'orr w21, w1, w21, lsl #28',0x13a0:'stp w26, wzr, [x23]',
  0x13b0:'stp w0, w27, [x23, #0x10]',0x13bc:'stp w19, w24, [x23, #0x18]',
  0x151c:'mov w2, #-1',0x154c:'ldr w0, [x19, #4]',0x19cc:'mov w0, #-5',
  0x19d0:'mov w27, #-0x3fa',0x304c:'mov x0, #0x2800',0x306c:'mov w0, #3',
  0x30e8:'mov w0, #1',0x7044:'mov w1, #1',0x7054:'mov w0, #4',
  0x7074:'ldr w0, [x21]',0x707c:'str x0, [x20, #0xe8]',
  0x7090:'stp x0, x1, [x20, #0xf0]',0x7088:'str xzr, [x20, #0x100]',
  0x7124:'mov w1, #0x7530',0x5e34:'mov w0, #0x90b',0x5e38:'movk w0, #0x803e, lsl #16',
  0x6870:'strb w22, [x20, #9]',0x68c8:'strb w22, [x19, #9]'},
 'cp':{0x4986f2:'tbb [pc, r0]',0x498840:'ldr r1, [r1, #0x1c]',
  0x498844:'beq #0x4988dc',0x498846:'cmp r1, #3',0x49884a:'movs r0, #1',
  0x4988de:'bl #0xa8544c',0x4988e4:'str r1, [r4, #0x20]',
  0x4988e6:'ldr r0, [r4, #0x24]',0x49891c:'cmp.w r4, #0x100',
  0x498916:'blx #0x52ee34',0x498920:'bne #0x498912',
  0x498936:'blx #0x540320',0x498940:'blx #0x52f17c',
  0xa85456:'strb r0, [r1, #9]',0xa85488:'cmp r1, #1',
  0xa854be:'add r0, r1',0xa8550e:'add r0, r2',
  0x4989f8:'mov.w r2, #0x1000',0x4989fe:'blx #0x558400',
  0x498ac2:'bl #0x49f80c',0x498a24:'bl #0x49f140',0x498ae2:'bl #0x49f908'},
 'ap':{0x2b22ccc:'sub w0, w0, #1',0x2b046c4:'mov w1, #0xd',0x2b046f8:'bl #0x1592d30',
  0x2b04798:'mov w1, #0xe',0x2b047cc:'bl #0x1592d30',
  0x2b237b8:'cbz w0, #0x2b237fc',0x2b237e4:'strb wzr, [x0, #0xf20]',
  0x2b237f8:'bl #0x1593f80',0x2b23820:'bl #0x2ebf66c',0x2ebf678:'bl #0x15936e0'},
 'libbackup':{0x22a0:'mov w2, #0x10',0x22b8:'bl #0x1530'},
 'kernel':{0xffffff8008322104:'ldr x2, [x20, #0x18]',
  0xffffff80083221f8:'bl #0xffffff8008321ff0',0xffffff800832200c:'cbz w1, #0xffffff8008321ff8',
  0xffffff80083227f0:'ldp x2, x1, [x28, #0x18]',0xffffff80083227f4:'mov w0, w22',
  0xffffff80083227f8:'blr x2',0xffffff800839bba8:'orr x0, x0, #0x400000000'},
}
RELOCS = {0x2bec:'backupfile_get_cp_data',0x3070:'backup_get_cp_data',0x30f0:'backupfile_save',
 0x7048:'Data_getAdrs',0x706c:'Data_getSize',0x7078:'arch_p32_to_p64',
 0x7084:'arch_va_to_phys',0x70b0:'__udif_cache_ctrl',0x70bc:'pcidma_transfer_async',
 0x70e8:'__udif_cache_ctrl',0x712c:'osal_wai_sem_tmo',0x7198:'backupfile_cb_getcp',
 0x5e40:'osal_sig_sem',0x6888:'Data_CalChecksum',0x6894:'Data_SetChecksum',
 0x68d0:'Data_SetCount',0x68d8:'Data_CheckIn',0x68f0:'Data_CalChecksum',
 0x68fc:'Data_SetChecksum',0x6930:'backupfile_load',0x5d7c:'filp_open',0x5d98:'vfs_write',
 0x6a70:'Backup_bin_start',0x6a80:'Backup_bin_size',0x7e70:'Backup_sync_all'}

def u32(b,a=0): return struct.unpack_from('<I',b,a)[0]
def bank(b,at):
    h=struct.unpack_from('<12I',b,at); n=h[6]+h[7]
    assert h[3]==0x344b42 and at+n<=len(b)
    raw=b[at:at+n]
    return raw,{'offset':hex(at),'bytes':n,'header_u32':[hex(x) for x in h],
      'sha256':sha(raw),'stored_checksum':hex(h[8]),
      'calculated_checksum':hex(sum(raw[:32])+sum(raw[36:]) & 0xffffffff)}

def request(q,mode):
    assert mode in (0,3) and q&0xffff0000==0x803e0000
    # Native op30 has one scalar and one zero-sized pointer; +24 ends up zero.
    return struct.pack('<10I',0x30,0,0x903e0811,q,1,1,1,1,mode,0)
def response(req):
    assert len(req)==40
    words=list(struct.unpack('<10I',req));q=words[3];mode=words[8]
    assert req==request(q,mode)
    out=bytearray(4096);out[:40]=req
    struct.pack_into('<I',out,4,0)
    if mode==3:struct.pack_into('<I',out,32,1)
    return bytes(out)

def rebuild(check=False):
    ims={k:Image(k) for k in BLOCKS}
    proof={'scope':'offline static audit and in-memory packet/data contract only; no QEMU or guest execution',
      'volume_UUID':UUID,'address_domains':{'ap':'ELF image VA','backup':'ET_REL .text offset',
       'cp':'Thumb VA, file offset VA-0x108000','kernel':'Image VA, file offset VA-0xffffff8008080000'}}
    proof['code']={k:[im.window(a,n) for a,n in BLOCKS[k]] for k,im in ims.items()}
    proof['instruction_checks']=[]
    for k,rows in CHECKS.items():
        for a,expected in rows.items():
            actual=ims[k].dis(a,4 if k!='cp' else 6)[0]
            assert actual['asm']==expected,(k,hex(a),actual,expected)
            proof['instruction_checks'].append({'image':k,**actual})
    m=ims['backup'];proof['relocation_checks']=[]
    for a,n in RELOCS.items():
        assert m.reloc[a]['symbol']==n,(hex(a),n,m.reloc.get(a))
        proof['relocation_checks'].append({'text_offset':hex(a),**m.reloc[a]})
    init=m.elf.get_section_by_name('.init.text'); initrel=m.elf.get_section_by_name('.rela.init.text')
    sy=m.elf.get_section(initrel['sh_link']); rr={r['r_offset']:{'symbol':sy.get_symbol(r['r_info_sym']).name,
      'addend':r['r_addend']} for r in initrel.iter_relocations()}
    proof['module_init']={'section':'.init.text','file_offset':hex(init['sh_offset']),
      'raw':init.data().hex(),'instructions':[{'offset':hex(i.address),'raw':i.bytes.hex(),
       'asm':(i.mnemonic+' '+i.op_str).strip(),'relocation':rr.get(i.address)} for i in m.cs.disasm(init.data(),0)],
      'Backup_save_reference':rr[0x268]}
    assert rr[0x268]['symbol']=='Backup_save'
    assert m.symbols['backup_get_cp_data']['st_value']==0x2ba8
    assert m.symbols['Backup_sync_all']['st_value']==0x3010
    table=m.elf.get_section_by_name('.rodata').data()[0x80:0x96]
    proof['kernel_wrapper_jump_table']={'section':'.rodata+0x80','raw':table.hex(),
      'targets':{hex(op):hex(0x138c+4*struct.unpack_from('<h',table,2*(op-0x29))[0]) for op in range(0x29,0x34)}}
    assert proof['kernel_wrapper_jump_table']['targets']['0x30']=='0x168c'
    cp=ims['cp'];table=cp.read(0x4986f6,14)
    proof['CP_jump_table']={'va':'0x4986f6','raw':table.hex(),
      'targets':{hex(op):hex(0x4986f6+2*table[op-0x27]) for op in range(0x27,0x35)}}
    assert proof['CP_jump_table']['targets']['0x30']=='0x498832'
    ap=ims['ap'];t=ap.read(0x3806ad0,34)
    proof['daemon_jump_table']={'va':'0x3806ad0','raw':t.hex(),
      'index':'type-1','targets':{str(i):hex(0x2b22cf0+4*struct.unpack_from('<h',t,2*(i-1))[0]) for i in (13,14)}}
    assert proof['daemon_jump_table']['targets']=={'13':'0x2b2378c','14':'0x2b23804'}
    ram=source('ram');seed=source('seed');apraw,aph=bank(ram,0)
    at=(len(apraw)+4095)&~4095;assert at==0xd2000
    raw,h=bank(ram,at);sraw,sh=bank(seed,at)
    assert len(raw)==0x14e5ec and raw==sraw
    assert h['stored_checksum']==h['calculated_checksum']
    assert sha(raw)=='5dc5883fb86d87d14c1c3d530d4d65d903361c189a64edabcd1f636df289f5b7'
    # CP lock3 changes exactly SuspendComp before DMA. This is a software-only
    # projection from saved bytes; it is not installed into any guest storage.
    frozen=bytearray(raw);frozen[9]=1;payload=bytes(frozen)
    dest=bytearray(len(raw));dest[:]=payload;assert bytes(dest)==payload
    unlock=request(0x803e6124,0);lock=request(0x803e6123,3)
    for req in (lock,unlock):
        rep=response(req);assert len(rep)==4096 and rep[40:]==bytes(4056)
        assert u32(rep,4)==0 and u32(rep,12)==u32(req,12)
        assert u32(rep,32)==(1 if u32(req,32)==3 else 0)
    proof['storage']={'AP_bank':aph,'CP_software_current_bank':h,
      'same_as_seed_in_this_saved_run':True,'physical_backing':'0x4040d2000',
      'native_CP_primary_mapping_unproven':True,'lock3_changes':[{'offset':'0x9','before':raw[9],'after':payload[9]}],
      'lock3_snapshot_sha256':sha(payload),'copied_readback_sha256':sha(dest),
      'all_other_bytes_preserved':raw[:9]==payload[:9] and raw[10:]==payload[10:],
      'lock3_checksum_stale_until_native_save':u32(payload,32)!=(sum(payload[:32])+sum(payload[36:])&0xffffffff)}
    proof['packet_contract']={'status_offset':4,'reply_source':'0x003e0811','reply_destination':'actual request+0x0c Q',
      'request_bytes':40,'reply_bytes':4096,'data_in_reply':False,'request_pages':1,
      'receive_timeout':-1,'example_Qs_are_synthetic_not_captured':True,
      'lock3_request':lock.hex(),'lock3_reply_first40':response(lock)[:40].hex(),
      'unlock0_request':unlock.hex(),'unlock0_reply_first40':response(unlock)[:40].hex(),
      'zero_tail_is_software_difference_not_native_opaque_tail':4056,
      'no_pagination_for_this_transaction':True,
      'wrapper_rejects_page_count_gt1':{'API_status':-5,'wrapper_return':-1018}}
    proof['DMA_contract']={'descriptor_bytes_written_by_backup':40,
      'fields':{'0x0/u8':0,'0x1/u8':4,'0x2/u8':0,'0x4/u32':'0x14e5ec',
       '0x8/u64':'0x404000000 (remote CP source, NOT AP first bank)',
       '0x10/u64':'0x4040d2000 (AP local destination)',
       '0x18/u64':'loaded backup.text+0x5e30 (backupfile_cb_getcp)',
       '0x20/u64':0},
      'native_struct_driver_private_fields':'pcidma_transfer_async also uses +0x28..0x3a; do not treat object as only40B allocation',
      'software_source':'current shared CP backing 0x4040d2000; current design aliases AP snapshot',
      'copy_bytes':len(raw),'semaphore':'0x803e090b','semaphore_timeout_native_units':'0x7530 (30000)',
      'callback_ABI':'callback(0, descriptor.context) after verified real copy, exactly once',
      'hardware_init_blacklisted':True,'native_start_can_return0_without_starting':'pcidma_start gates +0x14/+0x18; not proof of completion',
      'get_cp_data_masks_prior_failures':'initial lock status and DMA error logged; return value is final unlock status'}
    for n in ('owner','core','profile','init','command'):source(n)
    owner=PATHS['owner'].read_text();core=PATHS['core'].read_text()
    assert 'rd32(message)!=0x33' in owner and '#define CP_BANK_PHYS 0x4040d2000UL' in core
    proof['existing_backend']={'owner_path':str(PATHS['owner']),
      'only_backup_opcode_implemented':'0x33 reset; 0x30 routes to UNHANDLED, no reply/free',
      'storage_setup_is_lazy_seed_digest_pinned':True,
      'new_lock_suspendcomp_would_require_expected_digest_lifecycle_update':True}
    b=source('serial');lines=b.split(b'\n');snips=[]
    for a,z in [(52,57),(824,824),(1121,1125),(14287,14293),(14420,14424),
                (21310,21322),(28694,28704),(44932,44942),(61364,61374)]:
        snips.append({'first_LF':a,'last_LF':z,'lines':[x.decode(errors='replace').rstrip('\r') for x in lines[a-1:z]]})
    proof['serial_evidence']=snips
    for a in (28698,44936,61368): assert b'backup_get_cp_data' in lines[a-1]
    for a in (28699,44937,61369): assert b'Backup_sync_all' in lines[a-1]
    assert b'__boottime___udif_init_pcidma' in lines[823]
    proof['native_files']=[]
    for n in ('Backup_pri_file','Backup_sec_file'):
        s=m.symbols[n];sec=m.elf.get_section(s['st_shndx']);off=sec['sh_offset']+s['st_value']
        name=m.raw[off:off+100].split(b'\0',1)[0].decode();assert name=='/setting/Backup.bin'
        proof['native_files'].append({'symbol':n,'section':sec.name,'offset':hex(s['st_value']),
          'file_offset':hex(off),'path':name})
    proof['daemon_after_sync']={'type13':'subsystem path2ebf650 unless16f0bd0 nonzero',
      'type14':'2b23820 ->2ebf66c -> Backup_sync_all',
      'notification':'if request wait byte nonzero, clear8e29f20 under mutex8e5dbd8; notify_one at2b237f8 on8e31a60',
      'notify_is_not_file_save_success_receipt':True,
      'save_before_notify':'Backup_sync_all calls backupfile_save(1) after get_cp_data final return0',
      'file_dependencies':'backing header; configured primary/secondary paths; file mode; checksum/count/cookie/write completion; actual filp_open/vfs_write full lengths',
      'current_profile':'Backup_load=1 Backup_save=0; explicit Backup_sync_all still calls backupfile_save; no Backup_save test in that saved function',
      'Backup_save_init_use':'init.text+19c..1b0 loads flag and prints when zero; does not suppress explicit sync calls'}
    proof['unproven']=[
      'AP99 op30 full raw request/Q/header capacity was not saved in selected serial; schema here is original-code-derived.',
      'AppFw precise user PC2b046f8/2b047cc is coordinator stack attribution, not established by serial kernel futex stack alone.',
      'Native CP primary address-domain binding and actual CP execution; software backend aliases CP profile and AP snapshot.',
      'No op30/DMA backend was implemented, installed or executed here; copy and reply vectors run only in host bytearrays.',
      'Actual DMA descriptor/cache/return/callback/semaphore, bank readback, final unlock and native save/readback.',
      'Mapping software DMA at a safe scoped interception point, original allocator/source ownership/retry behavior and concurrency integration.',
      'Original52ee34/52f17c/540320 lower-level lock/cache implementation names not independently bound; observable call/arguments preserved.',
      'Model-setting notify and first draw after repair, persisted force0 and next boot behavior, runtime health and camera acceptance.']
    proof['method_reference']='https://www.capstone-engine.org/lang_python.html (checked2026-11-02; API only)'
    proof['sources']=SOURCES
    encoded=json.dumps(proof,ensure_ascii=False,indent=2)+'\n';target=OUT/'backup-sync-proof.json'
    if check:assert target.read_text()==encoded,'proof differs from rebuild'
    else:target.write_text(encoded)
    print(f'PASS backup-sync audit: {len(proof["instruction_checks"])} instructions; {len(RELOCS)} relocations; op30 lock/DMA/unlock; 3 frozen waits; host-only vectors')

def main():
    if len(sys.argv)==1:return rebuild()
    if sys.argv[1]=='--check':return rebuild(True)
    mode,name,a,n=sys.argv[1:];im=Image(name)
    assert mode=='dis'
    for row in im.dis(int(a,16),int(n,16)):print(row['va'],row['asm'],row.get('symbol',''),row.get('relocation',{}))
if __name__=='__main__':main()
