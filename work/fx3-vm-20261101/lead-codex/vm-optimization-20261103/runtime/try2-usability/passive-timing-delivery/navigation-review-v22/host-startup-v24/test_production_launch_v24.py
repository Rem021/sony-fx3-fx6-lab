"""Execute the production runner body with real loopback HTTP and locks, fake Popen.

The AST boundary skips immutable candidate preflight and command construction.
No QEMU process or guest is started by this fixture.
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
import sys
import tempfile
import threading
import time
import types
import urllib.error
import urllib.request

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def load_runner():
    path = HERE/'run_trial_v22_navigation_review.py'
    spec = importlib.util.spec_from_file_location('runner_v24_fixture', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    tree = ast.parse(path.read_text())
    main = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'main')
    start = next(i for i, node in enumerate(main.body) if isinstance(node, ast.Assign)
                 and any(isinstance(target, ast.Name) and target.id == 'journal' for target in node.targets))
    main.body = main.body[start:]
    main.name = 'production_body'
    main.args = ast.parse('def f(run, ns, args, env, checks, observer_sources, candidate_path, candidate, locks, snapshots): pass').body[0].args
    namespace = dict(vars(module))
    exec(compile(ast.fix_missing_locations(ast.Module(body=[main], type_ignores=[])), str(path), 'exec'), namespace)
    return module, namespace


def post(state, path, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(state.url+path, body,
                                 {'Content-Type':'application/json', 'X-Trial-Token':state.token,
                                  'Origin':state.url})
    try: response = urllib.request.urlopen(req, timeout=2)
    except urllib.error.HTTPError as error: response = error
    with response:
        return response.status, json.load(response)


def run_case(scenario):
    module, namespace = load_runner()
    servers, states, launches, actions, action_errors = [], [], [], [], []
    real_start = module.start_server
    real_wait = module.wait_for_final_receipt
    launch_id = 'a'*8+'-'+'b'*4+'-'+'c'*4+'-'+'d'*4+'-'+'e'*12
    action_thread = None

    def action(state):
        try:
            if scenario == 'timeout':
                return
            if scenario == 'start_without_ready':
                actions.append(('start_rejected',post(state, '/api/start', {'request_id':launch_id})[0]))
                return
            if scenario != 'cancel':
                actions.append(('ready', post(state, '/api/browser-ready', {})[0]))
                actions.append(('start', post(state, '/api/start', {'request_id': launch_id})[0]))
                if scenario == 'normal_duplicate':
                    actions.append(('duplicate', post(state, '/api/start', {'request_id': launch_id})[0]))
                    with urllib.request.urlopen(state.url+'/api/status', timeout=2) as response:
                        status = json.load(response)
                    assert status['launch_request_id'] == launch_id
            if scenario in ('cancel', 'accepted_then_end'):
                actions.append(('stop', post(state, '/api/stop', {})[0]))
        except Exception as exc:
            action_errors.append(repr(exc))

    def start(state, port):
        nonlocal action_thread
        states.append(state)
        result = real_start(state, port)
        servers.append(result)
        action_thread = threading.Thread(target=action, args=(state,), daemon=True)
        action_thread.start()
        return result

    def wait(state):
        with urllib.request.urlopen(state.url+'/api/status', timeout=2) as response:
            final = json.load(response)
        assert final['phase']=='finished' and final['result']['health_pass'] is False
        assert final['ready'] is False and final['final_receipt_id']
        assert post(state, '/api/final-ack', {'receipt_id':final['final_receipt_id']})[1]['acknowledged']
        return real_wait(state, timeout=0)

    def popen(*unused_args, **unused_kwargs):
        launches.append('fake-popen')
        raise OSError('fixture fake Popen: QEMU deliberately forbidden')

    namespace.update(start_server=start, wait_for_final_receipt=wait,
                     checkpoint=lambda value: None,
                     subprocess=types.SimpleNamespace(Popen=popen,
                          TimeoutExpired=module.subprocess.TimeoutExpired))
    saved_signals = {sig:signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
    with tempfile.TemporaryDirectory(prefix='prod-launch-', dir=HERE) as temporary:
        root = Path(temporary)
        frozen, runtime = root/'frozen', root/'runtime'
        frozen.mkdir(); runtime.mkdir()
        for folder in (frozen,runtime): (folder/'.run.lock').touch()
        owner = None
        if scenario == 'second_lock_conflict':
            owner = (runtime/'.run.lock').open('rb')
            fcntl.flock(owner, fcntl.LOCK_EX|fcntl.LOCK_NB)
        namespace.update(FROZEN=frozen, ROOT=runtime)
        run=root/'run';run.mkdir()
        candidate=root/'candidate.json';candidate.write_text('{}')
        ns=types.SimpleNamespace(seconds=60,max_steps=4096,internal_hoststep=False,
                                 port=0,exit_at_phase=None,launch_wait_seconds=.25)
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                exit_code=namespace['production_body'](run,ns,[],{},[],[],candidate,{},[],[])
            if action_thread is not None: action_thread.join(timeout=2)
            assert not action_errors, action_errors
            assert exit_code==2
            receipt=json.loads((run/'receipt.json').read_text())
            assert receipt['qemu_pid'] is None and receipt['key_steps']==0
            assert receipt['health_pass'] is False
            assert states[0].phase=='finished'
            assert all(not thread.is_alive() for _,thread in servers)
            expected_spawns=1 if scenario=='normal_duplicate' else 0
            assert len(launches)==expected_spawns, (scenario,launches)
            assert receipt['locks'][0]['free_at_close'] is True
            if scenario=='second_lock_conflict':
                assert receipt['locks'][1]['free_at_close'] is False
                assert '占用运行锁' in receipt['host_observer_error']
            else:
                assert receipt['locks'][1]['free_at_close'] is True
            if scenario in ('cancel','accepted_then_end'):
                assert 'browser_cancelled_before_guest_launch' in receipt['host_observer_error']
            if scenario=='timeout':
                assert 'browser_launch_handshake_timeout_no_guest_spawn' in receipt['host_observer_error']
            if scenario=='start_without_ready':
                assert actions==[('start_rejected',409)]
                assert 'browser_launch_handshake_timeout_no_guest_spawn' in receipt['host_observer_error']
            if scenario=='normal_duplicate':
                assert actions==[('ready',200),('start',202),('duplicate',200)], actions
            return {'scenario':scenario,'production_body_executed':True,
                    'fake_popen_count':len(launches),'actions':actions,
                    'first_lock_free_at_receipt':receipt['locks'][0]['free_at_close'],
                    'second_lock_free_at_receipt':receipt['locks'][1]['free_at_close'],
                    'HTTP_threads_reaped':True,'guest_started':False,
                    'error':receipt['host_observer_error']}
        finally:
            for sig, handler in saved_signals.items(): signal.signal(sig,handler)
            for server, thread in servers:
                if thread.is_alive(): server.shutdown()
                server.server_close();thread.join(timeout=2)
            if owner is not None:
                fcntl.flock(owner,fcntl.LOCK_UN);owner.close()
                probe=(runtime/'.run.lock').open('rb')
                fcntl.flock(probe,fcntl.LOCK_EX|fcntl.LOCK_NB)
                fcntl.flock(probe,fcntl.LOCK_UN);probe.close()


cases=[run_case(name) for name in ('timeout','start_without_ready','cancel','accepted_then_end',
                                  'second_lock_conflict','normal_duplicate')]
result={'status':'PASS','scope':'v24 production startup/cleanup body after immutable preflight',
        'real_QEMU_started':False,'cases':cases}
(HERE/'production-launch-test-receipt.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
