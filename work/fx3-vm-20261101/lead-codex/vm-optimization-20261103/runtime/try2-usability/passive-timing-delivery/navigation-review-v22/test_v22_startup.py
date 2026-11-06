"""Execute the production startup/cleanup body with a forbidden real Popen.

Preflight is excluded at the AST boundary (journal initialization). Real local
HTTP, locks, log monitor, health classifier and receipt code remain in use.
This does not test QEMU, firmware, candidate preflight or successful startup.
"""
import ast
import contextlib
import fcntl
import importlib.util
import io
import json
import os
from pathlib import Path
import signal
import socket
import sys
import tempfile
import types
import urllib.request

HERE = Path(__file__).resolve().parent
PARENT = HERE
sys.path.insert(0, str(PARENT))

def load(name):
    path = PARENT / name
    spec = importlib.util.spec_from_file_location(name[:-3], path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def body_function(module):
    tree = ast.parse(Path(module.__file__).read_text())
    main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
    start = next(i for i,n in enumerate(main.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='journal' for t in n.targets))
    main.body = main.body[start:]
    main.name = 'exercise_startup'
    main.args = ast.parse('def f(run, ns, args, env, checks, observer_sources, candidate_path, candidate, locks, snapshots): pass').body[0].args
    code = compile(ast.fix_missing_locations(ast.Module(body=[main], type_ignores=[])), module.__file__, 'exec')
    namespace = dict(vars(module))
    exec(code, namespace)
    return namespace

def exercise(filename, scenario, expected_fixed):
    module = load(filename)
    ns = body_function(module)
    servers, states, checkpoints, launches = [], [], [], []
    real_start = module.start_server
    real_wait = module.wait_for_final_receipt
    def start(state, port):
        states.append(state)
        result = real_start(state, port)
        servers.append(result)
        return result
    def wait(state):
        # Real final status and authenticated ACK over HTTP before shutdown.
        with urllib.request.urlopen(state.url+'/api/status', timeout=2) as response:
            final = json.load(response)
        assert final['phase']=='finished' and final['result']['health_pass'] is False
        assert final['error'] and not final['ready']
        data = json.dumps({'receipt_id':final['final_receipt_id']}).encode()
        request = urllib.request.Request(state.url+'/api/final-ack', data=data,
                   headers={'Content-Type':'application/json','X-Trial-Token':state.token})
        with urllib.request.urlopen(request, timeout=2) as response:
            assert json.load(response)['acknowledged'] is True
        return real_wait(state, timeout=0)
    class Exited:
        pid = 2147483647
        returncode = 7
        def poll(self): return self.returncode
    def popen(*args, **kwargs):
        launches.append('stub_only')
        if scenario=='spawn_error': raise OSError('fixture process spawn denied')
        if scenario=='early_exit': return Exited()
        raise AssertionError('port collision must precede process creation')
    def kill(pid, sig):
        assert pid==Exited.pid and sig==0
        raise ProcessLookupError('fixture process never existed')
    def killpg(*args): raise AssertionError('no process group exists in this fixture')
    ns.update(start_server=start, wait_for_final_receipt=wait,
              checkpoint=lambda value: checkpoints.append(value),
              subprocess=types.SimpleNamespace(Popen=popen,TimeoutExpired=module.subprocess.TimeoutExpired),
              os=types.SimpleNamespace(**{**vars(os),'kill':kill,'killpg':killpg}))
    saved_signals = {s:signal.getsignal(s) for s in (signal.SIGINT,signal.SIGTERM)}
    with tempfile.TemporaryDirectory(prefix='fixture-', dir=HERE) as temp:
        root=Path(temp);run=root/'run';run.mkdir()
        lockdirs=[root/'frozen',root/'runtime']
        held=[]
        for directory in lockdirs:
            directory.mkdir();path=directory/'.run.lock';path.touch()
            handle=path.open('rb');fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB);held.append(handle)
        ns.update(FROZEN=lockdirs[0],ROOT=lockdirs[1])
        manifest=root/'candidate.json';manifest.write_text('{}')
        blocker=socket.socket()
        if scenario=='port_collision':
            blocker.bind(('127.0.0.1',0));blocker.listen();port=blocker.getsockname()[1]
        else: port=0
        args=types.SimpleNamespace(seconds=60,max_steps=32,internal_hoststep=False,port=port,exit_at_phase=None)
        failure=None;code=None
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                code=ns['exercise_startup'](run,args,[],{},[],[],manifest,{},held,[])
        except Exception as exc:
            failure=repr(exc)
        finally:
            for sig,handler in saved_signals.items():signal.signal(sig,handler)
            blocker.close()
        try:
            if expected_fixed:
                assert failure is None, failure
                assert code==2
                receipt=json.loads((run/'receipt.json').read_text())
                assert receipt['health_pass'] is False and receipt['lifecycle_pass'] is False
                assert receipt['key_steps']==0 and receipt['standby_ready'] is False
                assert receipt['native_shutdown_after_ready'] is False
                assert receipt['host_observer_error'] and receipt['stop_cause']=='host_error'
                assert receipt['date99_raw_serial_evidence']['reason']=='serial_log_not_created'
                assert receipt['cleanup']['API16_restored'] is False
                assert all(x['free_at_close'] for x in receipt['locks'])
                assert all(not thread.is_alive() for _,thread in servers)
                assert states[0].phase=='finished'
                if scenario=='port_collision': assert not launches and receipt['qemu_pid'] is None
                if scenario=='spawn_error': assert receipt['qemu_pid'] is None
                if scenario=='early_exit': assert receipt['qemu_exit']==7 and receipt['process_reaped']
                return {'source':filename,'scenario':scenario,'passed':True,'exit':code,
                        'original_error':receipt['host_observer_error'],'real_qemu_started':False,
                        'server_threads_closed':True,'locks_free':True,'health_pass':False}
            assert failure and 'UnboundLocalError' in failure, failure
            assert not (run/'receipt.json').exists()
            return {'source':filename,'scenario':scenario,'baseline_bug_reproduced':failure,
                    'receipt_missing':True,'real_qemu_started':False}
        finally:
            # Baseline intentionally leaks final HTTP lifecycle on the exception;
            # fixture cleanup is separate and is never counted as production pass.
            for server,thread in servers:
                if thread.is_alive():server.shutdown()
                server.server_close();thread.join(timeout=2)
            for handle in held:
                if not handle.closed:fcntl.flock(handle,fcntl.LOCK_UN);handle.close()

rows=[]
for scenario in ['port_collision','spawn_error','early_exit']:
    rows.append(exercise('run_trial_v22_navigation_review.py',scenario,True))
(HERE/'v22-startup-test-receipt.json').write_text(json.dumps({'scope':'v22 production startup and cleanup body; fake process only; real HTTP and flock','cases':rows},ensure_ascii=False,indent=2)+'\n')
print('3 v22 startup receipts verified; no VM launched')
