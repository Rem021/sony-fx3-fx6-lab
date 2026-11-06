#!/usr/bin/env python3
"""Static FX3 service lifetime/exit audit; no Sony code or transport execution."""
from pathlib import Path
from hashlib import sha256
import ast
import importlib.util
import json

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parents[1]
REF = BASE / 'stage134-backup-reader-scope-and-service-extension'


def pinned(path, receipt):
    member = next(x for x in receipt['files'] if x['path'] == path.relative_to(ROOT).as_posix())
    assert path.stat().st_size == member['bytes'] and sha256(path.read_bytes()).hexdigest() == member['sha256']
    return member


def main():
    receipt_path = REF / 'final-receipt.json'
    assert sha256(receipt_path.read_bytes()).hexdigest() == '5ece0e5dea69b1c88e812ae42e46a07abf95316a2a6f02c34a5784b7ff6eec1d'
    receipt = json.loads(receipt_path.read_text())
    source = REF / 'audit_readers.py'
    inputs = [pinned(source, receipt)]
    spec = importlib.util.spec_from_file_location('fixed_local_elf_reader', source)
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    core = reader.Image('libsencore.so', 'a2907111c4a22314dcb12c25889e0e3142764c6a4a910a746e43908f76e7c410')
    names = [
        '_ZN19WorkerThreadManager6cancelEv', '_ZN19WorkerThreadManager4joinEv',
        '_ZN6Thread6createEPFPvS0_ES0_PK14pthread_attr_t', '_ZN6Thread6cancelEv', '_ZN6Thread4joinEPPv',
        '_ZN3Usb12handle_inputER20InitiationDispatcher',
        '_ZN3Usb4stopEPFv13__USBIF_EVENTP17usbif_event_paramiE',
        '_ZN3Usb13stop_callbackE13__USBIF_EVENTP17usbif_event_parami',
        '_ZN3Usb19synch_stop_callbackE13__USBIF_EVENTP17usbif_event_parami',
        '_ZN3Usb15spin_wait_whileENS_10state_typeE', '_ZN3Usb22finalize_usb_interfaceEv',
        '_Z12SenserIfStopR20InitiationDispatcher', 'senser_stop',
        '_ZN19WorkerThreadManager11run_workersEv',
        '_ZN10CoreModule9nin_startER13NinCooperator', '_ZN10CoreModule4stopER20InitiationDispatcher',
        'NinThread', '_Z12SenserThreadPv']
    functions = [core.function(n) for n in names]
    instructions = {int(i['pc'], 16): i for f in functions for i in f['instructions']}

    calls = [(0xc1b4, '_ZN6Thread6cancelEv'), (0xc1c4, '_ZN6Thread6cancelEv'),
             (0xc1e0, '_ZN6Thread4joinEPPv'), (0xc1ec, '_ZN6Thread4joinEPPv'),
             (0xc1f0, '_Z23CleanupMassDataHandlersv'), (0xc1fc, '_Z25UnloadSenserPluginModulesv'),
             (0x15524, 'pthread_create'), (0x1557c, 'pthread_cancel'), (0x155e0, 'pthread_join'),
             (0xc660, '_ZN19WorkerThreadManager6cancelEv'),
             (0xc908, '_ZNK3Usb4pushENS_10event_typeE'),
             (0xcc08, 'usleep'), (0xcd78, '_ZN19WorkerThreadManager4joinEv'),
             (0xcd0c, '_ZN19WorkerThreadManager11run_workersEv'),
             (0xce00, '_ZN3Usb4stopEPFv13__USBIF_EVENTP17usbif_event_paramiE'),
             (0xce0c, '_ZN19WorkerThreadManager4joinEv'),
             (0xce18, '_ZN3Usb15spin_wait_whileENS_10state_typeE'),
             (0xce54, 'usbif_destroy'), (0xce74, 'senif_destroy'),
             (0xcf40, '_ZN3Usb22finalize_usb_interfaceEv'),
             (0xcf4c, '_ZN20InitiationDispatcher14remove_handlerER14IoEventHandler'),
             (0xcf5c, '_ZN3Usb13close_channelEv'),
             (0xb114, '_Z12SenserIfStopR20InitiationDispatcher'),
             (0xc37c, '_ZN6Thread4joinEPPv'),
             (0xc394, '_ZN19WorkerThreadManager10run_workerEiPFPvS0_ES0_'),
             (0xc3b0, '_ZN19WorkerThreadManager10run_workerEiPFPvS0_ES0_'),
             (0xbc68, 'pthread_setcancelstate'), (0xbc88, 'pthread_testcancel'),
             (0xbc94, 'pthread_setcancelstate'), (0xb860, 'pthread_setcancelstate'),
             (0xb864, 'pthread_testcancel'), (0xb870, 'pthread_setcancelstate')]
    checked = [core.expect_call(pc, name) for pc, name in calls]
    assertions = {
        0xc1b0: 'add x0, x0, #8', 0xc1b8: 'add x0, x19, #0x10',
        0xc1dc: 'add x0, x0, #8', 0xc1e4: 'add x0, x19, #0x10',
        0x155dc: 'mov x1, #0', 0x155e4: 'cbz w0, #0x15608',
        0x15608: 'mov x0, #-1', 0x1560c: 'str x0, [x19]',
        0xc650: 'mov w1, #3', 0xc654: 'str w1, [x0, #0x10]',
        0xc67c: 'mov w1, #0xd', 0xc688: 'blr x3',
        0xc8d0: 'cbz w2, #0xc8e4', 0xc8f8: 'str wzr, [x0, #0x10]',
        0xc904: 'mov w1, #3', 0xc914: 'cbz w2, #0xc928', 0xc93c: 'str wzr, [x0, #0x10]',
        0xcc00: 'b.ne #0xcc10', 0xcc04: 'mov w0, #0xa', 0xcc0c: 'b #0xcbf8',
        0xcd80: 'cbz x0, #0xcd88', 0xcd84: 'blr x0', 0xcd98: 'blr x0',
        0xce14: 'mov w1, #3', 0xce3c: 'blr x1',
        0xc380: 'ldr x20, [x20, #0xf18]',
        0xbc64: 'mov w0, #0', 0xbc90: 'mov w0, #1',
        0xb85c: 'mov w0, #0', 0xb86c: 'mov w0, #1'}
    for pc, expected in assertions.items():
        assert instructions[pc]['asm'] == expected, (hex(pc), instructions[pc])
    # Full instruction order, not merely call labels: these callers ignore join status.
    for lo, hi in [(0xc1e0, 0xc1ec), (0xc1ec, 0xc1f0), (0xc37c, 0xc394)]:
        middle = [instructions[p] for p in range(lo + 4, hi, 4)]
        assert not any(i['asm'].split()[0].startswith(('b.', 'cb', 'tb')) for i in middle)
    wait = next(f for f in functions if f['name'] == '_ZN3Usb15spin_wait_whileENS_10state_typeE')
    assert [i['PLT_symbol'] for i in wait['instructions'] if i['PLT_symbol']] == ['usleep']

    jumps = core.read(0x16ae0, 7)
    targets = [0xcc9c + int.from_bytes(bytes([x]), 'little', signed=True) * 4 for x in jumps]
    assert targets == [0xcc9c, 0xcd14, 0xcc54, 0xcd70, 0xccb0, 0xcd14, 0xccd4]
    bindings = []
    for rel in core.elf.get_section_by_name('.rela.dyn').iter_relocations():
        if rel['r_offset'] in (0x6af00, 0x6af10, 0x6af18, 0x6af28, 0x6af80):
            symbol = core.dynsym.get_symbol(rel['r_info_sym'])
            bindings.append({'GOT': hex(rel['r_offset']), 'symbol': symbol.name,
                             'target': hex(symbol['st_value'] + rel['r_addend'])})
    assert len(bindings) == 5
    assert core.string(0x5527f) == 'NinThread' and core.string(0x55273) == 'senser_stop'

    # Parse fixed upstream source without importing or executing it.
    sony, command = REF / 'upstream/sony.py', REF / 'upstream/usb-commands.py'
    inputs.extend([pinned(sony, receipt), pinned(command, receipt)])
    st, ct = ast.parse(sony.read_text()), ast.parse(command.read_text())
    cls = next(x for x in st.body if isinstance(x, ast.ClassDef) and x.name == 'SonySenserAuthDevice')
    stop = next(x for x in cls.body if isinstance(x, ast.FunctionDef) and x.name == 'stop')
    shell = next(x for x in ct.body if isinstance(x, ast.FunctionDef) and x.name == 'senserShellCommand')
    exception = stop.body[0].handlers[0]
    assert isinstance(exception.type, ast.Name) and exception.type.id == 'GenericUsbException'
    assert len(exception.body) == 1 and isinstance(exception.body[0], ast.Pass)
    assert isinstance(stop.body[0], ast.Try)
    def is_call(node, method):
        return isinstance(node, ast.Expr) and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute) and node.value.func.attr == method
    tries = [x for x in ast.walk(shell) if isinstance(x, ast.Try) and any(is_call(y, 'stop') for y in x.finalbody)]
    assert len(tries) == 1
    cleanup = tries[0]
    with_statement = next(x for x in shell.body if isinstance(x, ast.With))
    branch = next(x for x in with_statement.body if isinstance(x, ast.If) and cleanup in x.body)
    auth = next(x for x in branch.body if is_call(x, 'authenticate'))
    assert auth.lineno < cleanup.lineno
    assert not any(is_call(x, 'authenticate') for x in cleanup.body)
    host_review = {
        'fixed_commit': 'a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0',
        'stop_function_lines': [stop.lineno, stop.end_lineno],
        'stop_swallows_GenericUsbException': True,
        'stop_does_not_read_body_worker_completion_or_reenumeration': True,
        'second_authenticate_line': auth.lineno, 'finally_protection_starts_line': cleanup.lineno,
        'authentication_failure_outside_local_stop_finally': True,
        'MSC_first_auth_and_reenumeration_also_outside_stop_finally': True,
        'source_only_not_executed': True,
        'not_a_claim_that_every_Python_exception_or_device_runtime_is_covered': True}

    result = {
        'status': 'PASS_STATIC_SERVICE_EXIT_LIFETIME_NOT_DEVICE_RETURN_OR_RECOVERY',
        'core_sha256': sha256(core.raw).hexdigest(), 'pinned_inputs': inputs,
        'functions': functions, 'checked_PLT_calls': checked,
        'jump_table': {'VA': '0x16ae0', 'raw': jumps.hex(),
                       'event_targets': {str(n): hex(v) for n, v in enumerate(targets)}},
        'GOT_bindings': bindings, 'host_source_review': host_review,
        'findings': [
            {'id': 'normal_auth_join', 'fact': 'Event6 starts run_workers: join object+8 before starting command workers 0 and1; join return ignored.',
             'limit': 'Successful join can wait for auth tail; actual success, process state and USB-to-event binding not established.'},
            {'id': 'cancel_is_request', 'fact': 'Worker.cancel targets Thread objects +8/+16; Thread.cancel calls pthread_cancel without any join.',
             'limit': 'No bounded cancellation latency or completed writers established by request return.'},
            {'id': 'join_and_cleanup', 'fact': 'Worker.join invokes two plain pthread_join wrappers, then mass-data cleanup and plugin unload; wrapper returns are ignored.',
             'limit': 'No internal timeout; cleanup/unload bodies and all external threads not closed by this review.'},
            {'id': 'callback_not_success', 'fact': 'Both stop callbacks log nonzero status, then still clear USB state to0; async callback also pushes event3, whose handler invokes join before callbacks.',
             'limit': 'State0 or a callback alone is not successful interface stop or successful join proof.'},
            {'id': 'finalize_sequence', 'fact': 'Finalize can wait for state1, stop state2, join workers, wait for state3, virtual close, destroy USB and Senser interfaces. SenserIfStop then removes handler/closes channel.',
             'limit': 'spin_wait_while has usleep(10) retry and no deadline; pthread_join is plain join. Actual time bounds or return-to-MSC not proved.'},
            {'id': 'cooperative_windows', 'fact': 'NinThread and SenserThread call setcancelstate with0, testcancel, then state1 before receive/work; numeric arguments pinned.',
             'interpretation': 'Under normal Linux pthread constants this is an enabled checkpoint followed by a disabled section; a host timeout cannot assume immediate camera cancellation.',
             'limit': 'Actual libc behavior, I/O unblock and cancellation cleanup not executed or wholly traced.'},
            {'id': 'host_cleanup_gap', 'fact': 'Fixed PMCA stop swallows GenericUsbException; local finally starts after service authenticate, leaving auth failure outside that cleanup.',
             'limit': 'No conclusion that all failures leave service mode, nor that physical damage occurred.'}],
        'new_device_USB_cache_or_Fastboot_enumeration': 0,
        'new_camera_Windows_or_downloaded_Sony_code_execution': False,
        'live_service_plan_or_authentication_released': False,
        'safe_return_or_independent_recovery_proven': False,
        'goal_complete': False, 'persistent_write_release': False}
    with (HERE / 'service-exit-review.json').open('x') as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    print(json.dumps({'status': result['status'], 'whole_original_functions': len(functions),
                      'PLT_calls_checked': len(checked), 'host_sources_parsed_not_imported': 2,
                      'camera_operations': 0}))


if __name__ == '__main__':
    main()
