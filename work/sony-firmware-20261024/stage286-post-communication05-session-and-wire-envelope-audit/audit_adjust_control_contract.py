"""Stage 286: Offline static & wire-envelope audit of AdjustControlFunc (0x40) and SubsystemCommunicationCommand after Stage 285 COMPLETE."""
from pathlib import Path
from hashlib import sha256
import io, json, plistlib, struct, subprocess
from elftools.elf.elffile import ELFFile
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM

H = Path(__file__).resolve().parent
B = H.parent
R = B.parents[1]

v = plistlib.loads(subprocess.check_output(['diskutil', 'info', '-plist', '/Volumes/KAFU2T']))
assert v.get('MountPoint') == '/Volumes/KAFU2T'
assert v.get('VolumeUUID', '').upper() == 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'


class SavedELF:
    def __init__(self, path: Path, pinned_sha256: str):
        self.path = path
        self.raw = path.read_bytes()
        self.digest = sha256(self.raw).hexdigest()
        assert self.digest == pinned_sha256, (path, self.digest, pinned_sha256)
        self.elf = ELFFile(io.BytesIO(self.raw))
        self.sy = self.elf.get_section_by_name('.dynsym')
        self.symbols = {s.name: s for s in self.sy.iter_symbols()}
        base = self.elf.get_section_by_name('.plt')['sh_addr']
        self.plt = {
            base + 32 + 16 * i: self.sy.get_symbol(r['r_info_sym']).name
            for i, r in enumerate(self.elf.get_section_by_name('.rela.plt').iter_relocations())
        }
        self.md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)

    def read(self, va: int, count: int) -> bytes:
        seg = next(
            s for s in self.elf.iter_segments()
            if s['p_type'] == 'PT_LOAD' and s['p_vaddr'] <= va and va + count <= s['p_vaddr'] + s['p_filesz']
        )
        off = seg['p_offset'] + va - seg['p_vaddr']
        return self.raw[off:off + count]

    def capture(self, label: str, va: int, count: int, symbol: str | None = None) -> dict:
        if symbol is not None:
            s = self.symbols[symbol]
            assert (s['st_value'], s['st_size']) == (va, count), (symbol, hex(s['st_value']), s['st_size'], hex(va), count)
        data = self.read(va, count)
        rows = []
        for insn in self.md.disasm(data, va):
            row = dict(pc=hex(insn.address), word=insn.bytes.hex(), asm=(insn.mnemonic + ' ' + insn.op_str).strip())
            if insn.mnemonic in ('bl', 'b') and insn.op_str.startswith('#'):
                tgt = self.plt.get(int(insn.op_str[1:], 16))
                if tgt:
                    row['target_symbol'] = tgt
            rows.append(row)
        assert len(rows) * 4 == count
        return dict(
            image=self.path.name,
            label=label,
            VA=hex(va),
            bytes=count,
            sha256=sha256(data).hexdigest(),
            symbol=symbol,
            symbol_boundary_verified=bool(symbol),
            instructions=rows,
        )


def main() -> None:
    # 1. Verify Stage 285 real-hardware COMPLETE artifacts
    s285 = B / 'stage285-service-access-communication05-execution'
    live_summary = json.loads((s285 / 'live-final-summary.json').read_text())
    priv_record = json.loads((s285 / 'private-record.json').read_text())
    runtime_review = json.loads((s285 / 'actual-runtime-review.json').read_text())
    user_confirm = json.loads((s285 / 'user-screen-confirmation.json').read_text())

    assert live_summary['status'] == 'HOST_RETURN_CONTROLLED_PORT_ASSOCIATION'
    assert live_summary['helper_terminal_observed'] is True
    assert live_summary['bounded_service_read_observed'] is True
    assert priv_record['phase'] == 'COMPLETE'
    assert priv_record['native_return'] == 0
    assert priv_record['global_guard_result'] == 0
    assert priv_record['result']['owner_retained'] == 0
    assert priv_record['result']['cleanup_error'] == 0
    assert priv_record['result']['clock_invalid'] == 0
    assert runtime_review['flow_frame_count'] == 124
    assert user_confirm['camera_screen_and_controls_normal'] is True

    # 2. Load pinned official 7.02 shared libraries
    core = SavedELF(
        B / 'stage2/extraction/files/nflasha15/lib/libsencore.so',
        'a2907111c4a22314dcb12c25889e0e3142764c6a4a910a746e43908f76e7c410',
    )
    jit = SavedELF(
        B / 'stage184-community-recovery-and-standalone-service/evidence/standalone-commands/originals/lib/libJiritsu.so',
        'bdef58b24a3b67b4d14d4f0214b89aae0fcad19f114b4188c328f9d2c092f1d9',
    )

    captures = [
        core.capture('SenserThread', 0xb7ac, 1068, '_Z12SenserThreadPv'),
        core.capture('SendResponse', 0xb4c0, 396, '_Z12SendResponseP12SenserPacketP10PacketData'),
        core.capture('Inconcurrent_lock', 0xdd00, 124, '_ZN12Inconcurrent10resource_t4lockEPK12SenserPacket'),
        core.capture('Inconcurrent_unlock', 0xdd7c, 4, '_ZN12Inconcurrent10resource_t6unlockEv'),
        core.capture('Command_Execute', 0xdb08, 96, '_ZN7Command7ExecuteEP12SenserPacket'),
        core.capture('MakeOsalMessage', 0xf038, 168, '_Z15MakeOsalMessageP26SubsystemCommunicationInfo'),
        core.capture('ReceiveOsalMessage', 0xf0e0, 1912, '_Z18ReceiveOsalMessageP26SubsystemCommunicationInfoPj'),
        core.capture('Subsystem_DoExecute', 0xf894, 416, '_ZN29SubsystemCommunicationCommand9DoExecuteEP12SenserPacket'),
        core.capture('Subsystem_Dtor', 0xfa34, 176, '_ZN29SubsystemCommunicationCommandD1Ev'),
        core.capture('Subsystem_TransactionStart', 0xfb0c, 2080, '_ZN29SubsystemCommunicationCommand16TransactionStartEPK12SenserPacketPKvS4_'),
        core.capture('AdjustControlFunc', 0x10344, 424, '_Z17AdjustControlFuncPK12SenserPacket'),
        jit.capture('packet_set_error', 0x8400, 36, 'packet_set_error'),
        jit.capture('packet_set_process_end', 0x8424, 40, 'packet_set_process_end'),
        jit.capture('packet_set_process_res_raw_data', 0x844c, 72, 'packet_set_process_res_raw_data'),
        jit.capture('packet_set_process_req_raw_data', 0x8494, 60, 'packet_set_process_req_raw_data'),
        jit.capture('packet_set_fin_del_data', 0x84d0, 40, 'packet_set_fin_del_data'),
        jit.capture('adj_cmd_set_file_path', 0x89b4, 292, 'adj_cmd_set_file_path'),
        jit.capture('adj_cmd_set_file2', 0x9528, 1120, 'adj_cmd_set_file2'),
        jit.capture('adj_cmd_get_file2', 0x9e74, 1064, 'adj_cmd_get_file2'),
        jit.capture('cmd_high_capacity_send_file', 0xab88, 344, 'cmd_high_capacity_send_file'),
        jit.capture('cmd_high_capacity_get_file', 0xb0ac, 460, 'cmd_high_capacity_get_file'),
        jit.capture('osal_callback_range', 0xb278, 0xb4d4 - 0xb278, None),
    ]

    checks = []

    def check_asm(obj: SavedELF, pc: int, expected_asm: str, expected_sym: str | None = None) -> None:
        insn = next(obj.md.disasm(obj.read(pc, 4), pc))
        found = (insn.mnemonic + ' ' + insn.op_str).strip()
        assert found == expected_asm, (obj.path.name, hex(pc), found, expected_asm)
        sym = None
        if insn.mnemonic in ('bl', 'b') and insn.op_str.startswith('#'):
            sym = obj.plt.get(int(insn.op_str[1:], 16))
        if expected_sym is not None:
            assert sym == expected_sym, (obj.path.name, hex(pc), sym, expected_sym)
        checks.append(dict(image=obj.path.name, pc=hex(pc), word=insn.bytes.hex(), asm=found, target_symbol=sym))

    # Key instruction checks in libsencore.so
    for pc, asm_str, sym in [
        # AdjustControlFunc: reads 4 bytes (category, command), locks Inconcurrent::resource_t, calls TransactionStart
        (0x10348, 'mov x2, #4', None),
        (0x1036c, 'bl #0xa580', '_Z9SerializePFiPhmEPvm'),
        (0x10388, 'mov x0, #0x318', None),
        (0x103b4, 'bl #0xa700', '_ZN12Inconcurrent10resource_t4lockEPK12SenserPacket'),
        (0x1043c, 'mov w1, #-0x60', None),
        (0x10474, 'bl #0xa8d0', '_ZN29SubsystemCommunicationCommand16TransactionStartEPK12SenserPacketPKvS4_'),
        # Inconcurrent::resource_t::lock / unlock
        (0xdd14, 'bl #0xae70', 'pthread_mutex_trylock'),
        (0xdd60, 'bl #0xa0a0', 'pthread_mutex_lock'),
        (0xdd68, 'cmp w0, #0x100, lsl #12', None),
        (0xdd7c, 'b #0xa2a0', 'pthread_mutex_unlock'),
        # TransactionStart: inline payload read (up to 0x124 bytes), auth level check, Phase 1 OSAL send/receive, Phase 4 MemoryData setup
        (0xfc50, 'ldrh w0, [x21]', None),
        (0xfc58, 'ldrh w0, [x21, #2]', None),
        (0xfc6c, 'subs w0, w0, #4', None),
        (0xfc74, 'cmp w0, #0x124', None),
        (0xfc8c, 'bl #0xa580', '_Z9SerializePFiPhmEPvm'),
        (0xfe20, 'cmp w2, #2', None),
        (0xfe28, 'tbz w3, #0xf, #0xfbd0', None),
        (0xfe48, 'ccmp w2, #1, #0, ne', None),
        (0xff9c, 'mov w0, #1', None),
        (0xffa8, 'bl #0xaaa0', '_Z15MakeOsalMessageP26SubsystemCommunicationInfo'),
        (0xffb4, 'bl #0xacb0', 'osal_snd_sync_msg'),
        (0x1001c, 'bl #0xaa10', '_Z18ReceiveOsalMessageP26SubsystemCommunicationInfoPj'),
        (0x1003c, 'cmp w0, #4', None),
        (0x1009c, 'bl #0xa000', '_ZN10MemoryDataC1EPFiPhmEPvmPFvS3_E'),
        # DoExecute: Phase 4 OSAL send/receive & response MemoryData construction
        (0xf9f4, 'cmp w0, #4', None),
        (0xfa00, 'bl #0xaaa0', '_Z15MakeOsalMessageP26SubsystemCommunicationInfo'),
        (0xfa0c, 'bl #0xacb0', 'osal_snd_sync_msg'),
        (0xf918, 'bl #0xaa10', '_Z18ReceiveOsalMessageP26SubsystemCommunicationInfoPj'),
        (0xf9c4, 'bl #0xa000', '_ZN10MemoryDataC1EPFiPhmEPvmPFvS3_E'),
        # ~SubsystemCommunicationCommand: Phase 16 (0x10) cleanup & Inconcurrent unlock
        (0xfa7c, 'bl #0xad00', '_ZN12Inconcurrent10resource_t6unlockEv'),
        (0xfaac, 'cmp w0, #0x10', None),
        (0xfab8, 'bl #0xaaa0', '_Z15MakeOsalMessageP26SubsystemCommunicationInfo'),
        (0xfac4, 'bl #0xacb0', 'osal_snd_sync_msg'),
        (0xfad0, 'bl #0xa7f0', '_Z11FreeOsalMsgjPv'),
        # SendResponse: sets response header version = 3 at offset 8
        (0xb4d0, 'mov w0, #3', None),
        (0xb4e0, 'strb w0, [x19, #8]', None),
    ]:
        check_asm(core, pc, asm_str, sym)

    # Key instruction checks in libJiritsu.so
    for pc, asm_str, sym in [
        # packet_set_* response builders
        (0x8424, 'mov w3, #8', None),
        (0x8454, 'mov w2, #8', None),
        (0x849c, 'mov w3, #2', None),
        (0x84d0, 'mov w3, #0x20', None),
        # adj_cmd_set_file2 operation branches (0=mount/file, 1=/mnt, 0xFF=RAM cache slot) and dlopen/dlclose check
        (0x957c, 'cmp w0, #1', None),
        (0x9584, 'cbz w0, #0x95a0', None),
        (0x9588, 'cmp w0, #0xff', None),
        (0x95bc, 'bl #0x5b70', 'sys_mount'),
        (0x968c, 'bl #0x5a80', '_Znam'),
        (0x96c0, 'bl #0x5ac0', 'memcpy'),
        (0x9908, 'bl #0x6120', 'dlopen'),
        (0x9928, 'bl #0x61f0', 'dlclose'),
        # adj_cmd_get_file2 operation branches (0=mount/file, 1=media_mount, 0xFF=RAM cache slot)
        (0x9edc, 'cmp w1, #1', None),
        (0x9ee4, 'cbz w1, #0x9ef8', None),
        (0x9ee8, 'cmp w1, #0xff', None),
        (0x9f18, 'bl #0x5b70', 'sys_mount'),
        (0x9fc4, 'bl #0x5ac0', 'memcpy'),
    ]:
        check_asm(jit, pc, asm_str, sym)

    # 3. Verify all 19 queue 0x016f0480 command records in libsencore.so
    queue_records = []
    base = 0x17698
    for idx in range(0x6c6):
        va = base + idx * 0x48
        rec = core.read(va, 0x48)
        cat, flags = struct.unpack_from('<HH', rec, 0)
        q = struct.unpack_from('<I', rec, 0x44)[0]
        if q == 0x016f0480:
            name = rec[4:0x44].split(b'\0', 1)[0].decode('latin1')
            cmd_lo = flags & 0xff
            outer_idx = jit.read(0x11b2c + cmd_lo - 1, 1)[0]
            outer_signed = outer_idx if outer_idx < 128 else outer_idx - 256
            outer_target = 0xb2b8 + 4 * outer_signed
            queue_records.append(dict(
                table_index=idx,
                VA=hex(va),
                category=hex(cat),
                flags=hex(flags),
                command_low_byte=cmd_lo,
                name=name,
                queue=hex(q),
                requires_level_2_or_3=bool((flags & 0xe000) == 0x4000),
                jiritsu_outer_target=hex(outer_target),
            ))
    assert len(queue_records) == 19

    # 4. Build comprehensive wire-envelope & session contract report
    contract = dict(
        status='POST_COMMUNICATION05_ADJUST_CONTROL_WIRE_AND_SESSION_CONTRACT_PINNED',
        stage285_real_hardware_baseline=dict(
            grant_id=user_confirm['grant_id'],
            terminal_status=live_summary['status'],
            private_record_phase=priv_record['phase'],
            native_return=priv_record['native_return'],
            flow_frame_count=runtime_review['flow_frame_count'],
            read0_request_bytes=12,
            read0_response_header_bytes=12,
            read0_response_header_version=3,
            read0_response_body_bytes=88,
            post_stop_msc_return_verified=True,
            driver_release_0da1_9_verified=True,
            user_screen_confirmed_normal=True,
            achieved_auth_table='A or B (level 2 or 3 proven on hardware because pFunc 0x10 ProductInfo is absent from table C)',
        ),
        adjust_control_wire_protocol=dict(
            pFunc=0x40,
            handler='_Z17AdjustControlFuncPK12SenserPacket',
            handler_VA='0x10344',
            present_in_pFunc_tables=['A', 'B', 'C'],
            category_0x1001_gate=dict(
                table_flags_mask='0x4000 (flags 0x4001..0x4013)',
                auth_level_check_VA='0xfe20..0xfe4c',
                allowed_auth_levels=[2, 3],
                level_1_rejected=True,
                hardware_satisfaction='Proven in Stage 285 via pFunc 0x10 read0 success (which also requires level 2 or 3)',
            ),
            senser_request_envelope=dict(
                header_bytes=12,
                header_layout='<IHHBBBB (size, pFunc=0x0040, seq, version, flag=0, reserved=0, res=0)',
                adjust_Selector_bytes=4,
                adjust_selector_layout='<HH (category=0x1001, command)',
                inline_payload_read_in_TransactionStart='min(size - 4, 0x124) bytes read into this+0x40 at 0xfc74..0xfc8c',
                remaining_payload_read_in_SenserThread='if size - 4 > 0x124, Phase 1 allocates DMM and SenserThread reads remaining bytes into MemoryData before Command::Execute (DoExecute)',
            ),
            senser_response_envelope=dict(
                header_bytes=12,
                header_layout='<IHHBBBB (payload_size, pFunc=0x0040, seq, version=3, flag, reserved=0, res)',
                producer='_Z12SendResponseP12SenserPacketP10PacketData (0xb4c0)',
                version_byte_at_offset_8=3,
                res_byte_at_offset_11='1 on normal PacketData response; 0x82 (-0x7e) or error code on failure',
            ),
            three_phase_osal_lifecycle=dict(
                phase_1_init=dict(
                    caller='SubsystemCommunicationCommand::TransactionStart (0xff9c..0x10038)',
                    osal_msg_byte0=1,
                    send_file_behavior='cmd_high_capacity_send_file (0xabc4) frees any prior *0x46bd0, creates DmmMgr(CheckUnitType(2*(size-4))), stores at *0x46bd0, returns 0x10 -> packet_set_process_req_raw_data (msg[0]=2) -> ReceiveOsalMessage maps/DMAs inline payload into DMM and sets next phase = 4',
                    get_file_behavior='cmd_high_capacity_get_file (0xb0dc) frees any prior *0x46bd0, creates DmmMgr(CheckUnitType(size-4)), stores at *0x46bd0, returns 0x10 -> packet_set_process_req_raw_data (msg[0]=2) -> ReceiveOsalMessage copies 3-byte inner request into DMM and sets next phase = 4',
                ),
                phase_4_execute=dict(
                    caller='SubsystemCommunicationCommand::DoExecute (0xf9f0..0xf9c8)',
                    osal_msg_byte0=4,
                    send_file_behavior='Dispatches command 6..16 (15=adj_cmd_set_file_path, 16=adj_cmd_set_file2), writes 4-byte business status at [msg+0x1c], frees DMM buffer and destroys *0x46bd0 (0xac68..0xac88), returns 0 -> packet_set_process_end (msg[0]=8, size=4) -> ReceiveOsalMessage sets phase=0x10 (or 0 if no out-of-line DMM) and returns 4-byte status buffer',
                    get_file_behavior='Dispatches command 8..17 (17=adj_cmd_get_file2), allocates DMM for response (4-byte status + payload), returns 0x11 -> packet_set_process_res_raw_data (msg[0]=8, dmm_addr, total_size) -> ReceiveOsalMessage DMAs/copies response from DMM into host reply buffer and sets next phase = 0x10',
                ),
                phase_16_cleanup=dict(
                    caller='SubsystemCommunicationCommand::~SubsystemCommunicationCommand (0xfaa4..0xfad4)',
                    osal_msg_byte0=0x10,
                    behavior='When phase==0x10 (after get_file Phase 4), sends msg[0]=0x10 to libJiritsu -> cmd_high_capacity_get_file (0xb214) calls dmm_free(), destroys *0x46bd0, zeroes *0x46bd0, returns 0x12 -> packet_set_fin_del_data (msg[0]=0x20), then FreeOsalMsg and Inconcurrent::resource_t::unlock()',
                ),
            ),
        ),
        concurrency_and_state_ownership=dict(
            senser_worker_threads=dict(
                count=2,
                spawner='WorkerThreadManager::run_workers (0xc34c) spawns worker 0 and worker 1 running SenserThread (0xb7ac)',
                usb_receive_serialization='Serialize(SenserIfReceive, ...) holds a mutex across each USB receive, and Inconcurrent::resource_t::lock (0xdd00) serializes AdjustControlFunc instances inside libsencore.so',
                single_host_client_implication='When our root helper holds exclusive IOKit USBDeviceOpenSeize on 054C:0336 and sends requests strictly sequentially (waiting for each 12B response header + payload before sending the next request), two SenserThread workers never concurrently execute AdjustControlFunc from USB',
            ),
            queue_0x016f0480_writers=dict(
                libsencore_records=len(queue_records),
                other_internal_camera_producers_proven_absent=False,
                implication='Sequential USB requests prevent USB-side interleaving across SET_FILE_PATH (15) -> SET_FILE2 (16) / GET_FILE2 (17), while single-command operations (or in-memory slot 0xFF operations) avoid multi-step path dependencies',
            ),
            operation_modes_comparison=dict(
                operation_0_filesystem=dict(
                    byte_0x28=0,
                    calls_sys_mount=True,
                    mount_source='/dev/nflasha6',
                    mount_target='/tmp/jiritsu',
                    consumes_selected_path_0x467c8=True,
                    set_file2_dlopen_trigger='Only when resolved path equals /tmp/jiritsu/libJit.so AND /tmp/jbusy exists (0x9754..0x977c, 0x98d0..0x9928)',
                ),
                operation_1_media=dict(
                    byte_0x28=1,
                    calls_sys_media_mount_on_get=True,
                    base_path='/mnt',
                    consumes_selected_path_0x467c8=True,
                ),
                operation_0xFF_ram_slot=dict(
                    byte_0x28=0xFF,
                    calls_sys_mount=False,
                    touches_filesystem=False,
                    uses_selected_path_0x467c8_for_lookup=False,
                    clears_selected_path_0x467c8_on_exit=True,
                    backing_store='In-memory slot table at *0x46bd8 (allocated in jiritsu_init 0x6e58..0x6e74), indexed by slot byte [x19, #0x29], max 5 MiB (0x500000), mode [x19, #0x2a] <= 0x11',
                    does_not_call_dlopen=True,
                ),
            ),
        ),
        stage244_conditions_reevaluation=dict(
            condition_1_bounded_native_control_session_and_same_body_identity=dict(
                status='SATISFIED_ON_HARDWARE_IN_STAGE285',
                evidence='Stage 285 (fx3-702-service-access-communication-20261101-05) completed MSC->SERVICE->read0(12B+12B+88B)->STOP->same-port MSC return->0da1:9 release->COMPLETE with user screen confirmation.',
            ),
            condition_2_exclusive_state_ownership_or_bounded_return_route=dict(
                status='STATICALLY_PINNED_SINGLE_CLIENT_AND_SLOT_0xFF_DISTINCTION',
                evidence='Inconcurrent::resource_t::lock (0xdd00..0xdd78) + sequential single-client USB requests prevent USB worker interleaving, and DMM lifecycle (Phase 1 -> Phase 4 -> Phase 16) is self-contained per command. Furthermore, operation 0xFF provides a pure RAM cache-slot read/write path without sys_mount, whereas operation 0 (including /tmp/jiritsu/libJit.so dlopen) calls sys_mount("/dev/nflasha6", "/tmp/jiritsu").',
            ),
            condition_3_precise_side_effect_contract_and_exit_receipts=dict(
                status='SERVICE_EXIT_PROVEN_MOUNT_SIDE_EFFECT_REMAINS_DISTINCT',
                evidence='SERVICE session exit and automatic MSC return (when camera USB mode is fixed to Mass Storage) are proven on hardware in Stage 285. Any future candidate that uses operation 0 (sys_mount) or dlopen (/tmp/jiritsu/libJit.so) must explicitly account for /tmp/jbusy and /tmp/jiritsu mount behavior rather than claiming zero-side-effect read-only operation.',
            ),
        ),
        sources=[
            dict(path=str(core.path.relative_to(R)), sha256=core.digest, bytes=len(core.raw)),
            dict(path=str(jit.path.relative_to(R)), sha256=jit.digest, bytes=len(jit.raw)),
        ],
        captured_functions_count=len(captures),
        instruction_checks_count=len(checks),
        queue_016f0480_records=queue_records,
        original_code_executed=False,
        new_live_usb_or_root_operations=0,
    )

    decision = dict(
        stage='stage286-post-communication05-session-and-wire-envelope-audit',
        milestone=2,
        communication_diagnostic_phase_complete=True,
        communication_diagnostic_evidence='stage285-service-access-communication05-execution',
        next_milestone2_subphase='Evaluate whether to run a bounded non-mountingAdjustControl (0x40) probe or proceed to explicit prerequisite analysis for `/tmp/jbusy` and `/tmp/jiritsu` mount boundaries',
        camera_connection_needed_for_this_stage=False,
        new_live_trial_authorized=False,
        first_flash_released=False,
    )

    (H / 'captured-functions.json').write_text(json.dumps(captures, ensure_ascii=False, indent=2) + '\n')
    (H / 'adjust-control-wire-and-session-contract.json').write_text(json.dumps(contract, ensure_ascii=False, indent=2) + '\n')
    (H / 'decision.json').write_text(json.dumps(decision, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(
        status=contract['status'],
        captured_functions=len(captures),
        instruction_checks=len(checks),
        queue_records=len(queue_records),
        new_live_operations=0,
    )))


if __name__ == '__main__':
    main()
