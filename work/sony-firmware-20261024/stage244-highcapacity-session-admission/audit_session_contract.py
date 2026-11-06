"""Static saved-file checks only; never execute Sony code or open USB."""
from pathlib import Path
from hashlib import sha256
import io, json, struct, plistlib, subprocess
from elftools.elf.elffile import ELFFile
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM

H = Path(__file__).resolve().parent
B = H.parent
R = B.parents[1]
v = plistlib.loads(subprocess.check_output(['diskutil', 'info', '-plist', '/Volumes/KAFU2T']))
assert v.get('MountPoint') == '/Volumes/KAFU2T'
assert v.get('VolumeUUID', '').upper() == 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'

class SavedELF:
    def __init__(self, path, pinned):
        self.path, self.raw = path, path.read_bytes()
        self.digest = sha256(self.raw).hexdigest()
        assert self.digest == pinned
        self.elf = ELFFile(io.BytesIO(self.raw))
        self.sy = self.elf.get_section_by_name('.dynsym')
        self.symbols = {s.name: s for s in self.sy.iter_symbols()}
        base = self.elf.get_section_by_name('.plt')['sh_addr']
        self.plt = {base + 32 + 16*i: self.sy.get_symbol(r['r_info_sym']).name
                    for i, r in enumerate(self.elf.get_section_by_name('.rela.plt').iter_relocations())}
        self.md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
    def read(self, va, count):
        seg = next(s for s in self.elf.iter_segments() if s['p_type'] == 'PT_LOAD'
                   and s['p_vaddr'] <= va and va+count <= s['p_vaddr']+s['p_filesz'])
        off = seg['p_offset'] + va - seg['p_vaddr']
        return self.raw[off:off+count]
    def capture(self, label, va, count, symbol=None):
        if symbol:
            s = self.symbols[symbol]
            assert (s['st_value'], s['st_size']) == (va, count)
        data = self.read(va, count)
        rows = []
        for i in self.md.disasm(data, va):
            row = dict(pc=i.address, word=i.bytes.hex(), asm=i.mnemonic+' '+i.op_str)
            if i.mnemonic in ('bl', 'b') and i.op_str.startswith('#'):
                row['target_symbol'] = self.plt.get(int(i.op_str[1:],16))
            rows.append(row)
        assert len(rows)*4 == count
        return dict(label=label, VA=va, bytes=count, sha256=sha256(data).hexdigest(),
                    symbol=symbol, symbol_boundary_verified=bool(symbol), instructions=rows)

j = SavedELF(B/'stage184-community-recovery-and-standalone-service/evidence/standalone-commands/originals/lib/libJiritsu.so',
             'bdef58b24a3b67b4d14d4f0214b89aae0fcad19f114b4188c328f9d2c092f1d9')
c = SavedELF(B/'stage2/extraction/files/nflasha15/lib/libsencore.so',
             'a2907111c4a22314dcb12c25889e0e3142764c6a4a910a746e43908f76e7c410')
captures = [j.capture(n,a,z,s) for n,a,z,s in [
    ('registration',0x6d74,296,'jiritsu_init'),
    ('anonymous_OSAL_callback_range',0xb278,0xb4d4-0xb278,None),
    ('send_DMM_lifecycle',0xab88,344,'cmd_high_capacity_send_file'),
    ('get_DMM_lifecycle',0xb0ac,460,'cmd_high_capacity_get_file'),
    ('selected_path_setter',0x89b4,292,'adj_cmd_set_file_path'),
    ('selected_path_consumer',0x92e8,292,'get_access_filename'),
    ('GET_FILE2',0x9e74,1064,'adj_cmd_get_file2'),
    ('mount_wrapper',0x771c,24,'sys_mount'),
    ('CFileAccess_mount_wrapper',0xf8b4,24,'_ZN11CFileAccess5mountEPKcS1_S1_mPKv'),
    ('CFileAccess_selection_mount',0xf460,1108,'_ZN11CFileAccess15selection_mountEPKcS1_S1_S1_mPKv')]]
captures += [c.capture('command_message_bridge',0xf038,168,'_Z15MakeOsalMessageP26SubsystemCommunicationInfo'),
             c.capture('command_lookup_and_gate',0xfb0c,2080,'_ZN29SubsystemCommunicationCommand16TransactionStartEPK12SenserPacketPKvS4_')]
checks=[]
def asm(obj, pc, expected):
    i=next(obj.md.disasm(obj.read(pc,4),pc)); found=i.mnemonic+' '+i.op_str
    assert found==expected,(hex(pc),found,expected)
    checks.append(dict(source=obj.path.name,pc=pc,word=i.bytes.hex(),asm=found))
def call(obj,pc,target,kind='bl'):
    i=next(obj.md.disasm(obj.read(pc,4),pc))
    assert i.mnemonic==kind and obj.plt[int(i.op_str[1:],16)]==target,(hex(pc),i.op_str,target)
    checks.append(dict(source=obj.path.name,pc=pc,word=i.bytes.hex(),asm=i.mnemonic+' '+i.op_str,target_symbol=target))

for pc,expected in [
 (0x6da4,'adrp x2, #0xb000'),(0x6da8,'add x2, x2, #0x278'),
 (0x6dac,'mov w0, #0x480'),(0x6db4,'movk w0, #0x16f, lsl #16'),
 (0x6db8,'ldr x1, [x1, #0xfb8]'),
 (0xb290,'ldrh w0, [x19, #0x26]'),(0xb298,'cmp w0, #0x11'),
 (0xb434,'b #0xb370'),(0xb440,'b #0xb370'),(0xb44c,'b #0xb398'),
 (0xabc4,'ldr x21, [x19, #0xbd0]'),(0xac00,'str x20, [x19, #0xbd0]'),
 (0xac88,'str xzr, [x19, #0xbd0]'),(0xb0e4,'ldr x21, [x0, #0xbd0]'),
 (0xb124,'str x19, [x20, #0xbd0]'),(0xb140,'ldrh w0, [x0, #0x26]'),
 (0xb188,'tbz w19, #0x1f, #0xb130'),(0xb200,'ldr x1, [x0, #0xbd0]'),
 (0xb23c,'str xzr, [x19, #0xbd0]'),
 (0x8a28,'adrp x19, #0x46000'),(0x8a30,'ldr x0, [x19, #0x7c8]'),
 (0x8a48,'str x0, [x19, #0x7c8]'),(0x935c,'ldr x21, [x0, #0x7c8]'),
 (0x9fe0,'ldr x0, [x19, #0x7c8]'),(0x9fec,'str xzr, [x19, #0x7c8]'),
 (0xb2d0,'cmp w0, #0x10'),(0xb484,'cmp w0, #0x11'),(0xb4a0,'cmp w0, #0x12'),
 (0x7720,'mov x3, #0x490'),(0x772c,'movk x3, #0xc0ed, lsl #16')]: asm(j,pc,expected)
for pc,target in [
 (0x6dbc,'osal_reg_sync_msg_queue_cb'),(0xb37c,'cmd_high_capacity_send_file'),
 (0xb3a4,'cmd_high_capacity_get_file'),(0xabd0,'_ZN6DmmMgrD1Ev'),
 (0xabd8,'_ZdlPv'),(0xac68,'_ZN6DmmMgr8dmm_freeEv'),
 (0xb0f0,'_ZN6DmmMgrD1Ev'),(0xb0f8,'_ZdlPv'),
 (0xb21c,'_ZN6DmmMgr8dmm_freeEv'),(0xb230,'_ZN6DmmMgrD1Ev'),
 (0x8a38,'free'),(0x8a44,'calloc'),(0x9fe8,'free'),
 (0x9f18,'sys_mount'),(0xb498,'packet_set_process_res_raw_data'),
 (0xb4b4,'packet_set_fin_del_data'),(0xb4cc,'packet_set_process_end')]: call(j,pc,target)
call(j,0x7730,'_ZN11CFileAccess5mountEPKcS1_S1_mPKv','b')
call(j,0xf8c8,'_ZN11CFileAccess15selection_mountEPKcS1_S1_S1_mPKv','b')
call(j,0xf4b8,'strncmp')
call(j,0xf7d4,'mount')
for pc,expected in [(0xf8b4,'mov x5, x4'),(0xf8b8,'mov x4, x3'),
 (0xf8bc,'mov x3, x2'),(0xf8c0,'mov x2, x1'),(0xf8c4,'mov x1, #0'),
 (0xf46c,'mov x20, x2'),(0xf47c,'mov x26, x4'),(0xf48c,'mov x24, x0'),
 (0xf4b0,'mov x0, x20'),(0xf4bc,'cbnz w0, #0xf7c0'),
 (0xf7c0,'mov x4, x27'),(0xf7c4,'mov x3, x26'),(0xf7d0,'mov x0, x24')]: asm(j,pc,expected)
assert j.read(0x31375,5)==b'/mnt\0' and j.read(0x30e17,13)==b'/tmp/jiritsu\0'
for pc,expected in [(0xf07c,'ldrb w1, [x0, #0x26]'),(0xf080,'strh w1, [x0, #0x26]'),
 (0xfe08,'and w1, w3, #0xe000'),(0xfe10,'b.eq #0xfbc8'),
 (0xfe1c,'ldrb w2, [x0]'),(0xfe20,'cmp w2, #2'),(0xfe48,'ccmp w2, #1, #0, ne')]: asm(c,pc,expected)

reloc=next(r for r in j.elf.get_section_by_name('.rela.dyn').iter_relocations() if r['r_offset']==0x45fb8)
assert j.sy.get_symbol(reloc['r_info_sym']).name=='g_cbHandle'
tables=[]
for cmd,name in [(15,'JIRITSU_SET_FILE_PATH'),(16,'JIRITSU_SET_FILE2'),(17,'JIRITSU_GET_FILE2')]:
    va=0x31d94+(cmd-15)*0x48;data=c.read(va,0x48)
    queue,category,internal=struct.unpack_from('<IHH',data)
    text=data[8:].split(b'\0',1)[0].decode()
    assert (queue,category,internal,text)==(0x016f0480,0x1001,0x4000|cmd,name)
    outer=j.read(0x11b2c+cmd-1,1)[0];outer=outer if outer<128 else outer-256
    target=0xb2b8+4*outer
    assert target=={15:0xb42c,16:0xb438,17:0xb444}[cmd]
    tables.append(dict(command=cmd,name=name,core_VA=va,raw=data.hex(),
                       queue=queue,category=category,flags=internal,outer_dispatch_target=target))

report=dict(status='STATIC_SESSION_ROUTE_BOUND_CURRENT_RAM_GET_CANDIDATE_HELD',
 sources=[dict(path=str(x.path.relative_to(R)),sha256=x.digest,bytes=len(x.raw)) for x in (j,c)],
 source_ranges=len(captures),instruction_checks=checks,core_records=tables,
 registration=dict(queue=0x016f0480,callback=0xb278,call=0x6dbc,callback_handle_GOT=0x45fb8,
                   callback_handle_symbol='g_cbHandle',current_body_registration_executed_or_verified=False),
 DMM_lifecycle=dict(global_pointer=0x46bd0,phase1_replaces_previous_manager=True,
                    phase4_dispatches_file_operation=True,get_phase16_frees_manager=True,
                    code16_17_18_are_internal_callback_results_not_constructor_success=True,
                    cross_request_owner_or_authenticated_session_binding_proven=False),
 selected_path=dict(global_pointer=0x467c8,selector_frees_and_replaces_previous_value=True,
                    GET_consumes_and_frees_global_value=True,
                    own_module_nonce_or_directory_claim_is_not_native_global_path_lock=True,
                    lower_layer_exclusive_session_proven=False),
 conditional_interleaving=dict(kind='static conditional witness, not observed or executed',
   premises=['two authorized request sources may reach this callback',
             'no lower-layer lease spans the whole select/get exchange'],
   sequence=['A selects its own result path','B selects another path','A GET consumes the current global path selected by B'],
   conclusion='per-command serialization alone does not establish selected-path ownership',
   premises_proven_on_current_camera=False),
 read_side_effects=dict(operation0_calls_mount=True,
                      wrapper_chain=['sys_mount','CFileAccess::mount','CFileAccess::selection_mount','libc mount'],
                      target_is_not_mnt_prefix_so_selection_takes_libc_mount_branch=0xf7c0,
                      mount_flags=0xc0ed0490,
                      MS_RDONLY_requested=bool(0xc0ed0490&1),
                      effective_current_mount_state_or_actual_flash_write_proven=False,
                      host_reply_length_does_not_bound_whole_file_DMM_allocation=True),
 actual_authentication_USB_DMM_runtime_owner_normal_exit_or_restore_verified=False,
 original_Sony_Linux_glibc_or_downloaded_camera_code_executed=False,
 new_camera_USB_cache_admin_or_firmware_operations=0,
 previous_model_tests_repeated=0,probe_deployable=False,first_flash_released=False)
decision=dict(milestone=2,decision='HOLD_CURRENT_GET_FILE2_RAM_RESULT_ROUTE',
 camera_connection_needed_for_this_batch=False,
 positive_result='Pinned official command records, queue registration, low-byte bridge and callback dispatch now agree statically.',
 not_accepted=['send stage243 inner frames directly as a USB test',
               'treat native global DMM/path state as protected by our RAM directory claim',
               'describe operation0 as a proven RAM-only read with no persistent side effects'],
 required_new_evidence=['bounded native control session and authenticated same-body identity',
   'exclusive ownership of native selected-path and DMM state across the complete exchange, or another bounded return route',
   'precise side-effect contract and actual exit/USB return receipts'],
 next_scope='Specify a bounded communication-only admission probe without upload, file select/GET, mode transition or root195 launch; do not execute it before an exact program and action boundary exist.',
 milestone2_complete=False,remaining_milestones_before_persistent_first_flash=5,
 requirements_G01_to_G16_unchanged=True,persistent_write_release=False)
for name,value in [('original-ranges.json',captures),('static-contract.json',report),('decision.json',decision)]:
    with (H/name).open('x') as f: json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(dict(status=report['status'],source_ranges=len(captures),instruction_checks=len(checks),core_records=len(tables),new_camera_operations=0)))
