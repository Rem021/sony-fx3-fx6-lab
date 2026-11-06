"""Build host-only final-receipt candidate from pinned v4/v13, without VM use."""
import difflib
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent

def sha(data):
    return hashlib.sha256(data).hexdigest()

def replace_once(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new, 1)

web_source = PARENT/'trial_web_v4_resilient.py'
web = web_source.read_text()
assert sha(web.encode()) == 'a32439c86507289f46442b474ced37434ea3da3d912be371e4a9010477ef6d04'
original_web = web
web = replace_once(web, '        self.result = None\n', '''        self.result = None
        # Delivery acknowledgement, never a new VM cleanup assertion.
        self.final_receipt_id = secrets.token_urlsafe(16)
        self.final_receipt_seen = threading.Event()
        self.final_receipt_close = threading.Event()
''')
web = replace_once(web, "                    'frame': self.frame, 'result': self.result,", "                    'frame': self.frame, 'result': self.result,\n                    'final_receipt_id': self.final_receipt_id if self.phase == 'finished' else None,")
web = replace_once(web, '    def take(self):\n', '''    def request_stop(self):
        with self.lock:
            # Another tab or delayed request must not undo a terminal receipt.
            if self.phase == 'finished':
                return 200, {'finished': True}
            self.ready = False
            self.phase = 'stopping'
            self.message = '正在结束试用并回收资源…'
            self.stop.set()
            return 202, {'stopping': True}

    def acknowledge_final(self, body):
        with self.lock:
            if self.phase != 'finished' or body.get('receipt_id') != self.final_receipt_id:
                return 409, {'error': '最终结果尚未生成或回执不匹配。'}
            self.final_receipt_seen.set()
            self.final_receipt_close.set()
            return 200, {'acknowledged': True}

    def take(self):
''')
web = replace_once(web, "                state.update(ready=False, phase='stopping', message='正在结束试用并回收资源…')\n                state.stop.set()\n                return self.reply(202, {'stopping': True})", "                code, result = state.request_stop()\n                return self.reply(code, result)\n            if self.path == '/api/final-ack':\n                code, result = state.acknowledge_final(body)\n                return self.reply(code, result)")
web = replace_once(web, '     finished=true;disableKeys();endButton.disabled=true;return;', '''     finished=true;disableKeys();endButton.disabled=true;
     // Confirm delivery only after displaying the authoritative final status.
     // A lost ACK never overrides that status or initiates another operation.
     if(s.final_receipt_id)void post('/api/final-ack',{receipt_id:s.final_receipt_id}).catch(()=>{});
     return;''')
web += '''

def wait_for_final_receipt(state, timeout=30.0):
    """Keep final status readable across one bounded 24s browser request cycle.

    Locks and QEMU are already cleaned up by the caller. This wait is bounded
    even if the browser is closed; acknowledgement proves receipt, not success.
    """
    if not 0 <= timeout <= 30:
        raise ValueError('final receipt grace must be within 0..30 seconds')
    with state.lock:
        if state.phase != 'finished':
            raise RuntimeError('cannot acknowledge an unfinished session')
    started = time.monotonic()
    closed = state.final_receipt_close.wait(timeout)
    acknowledged = state.final_receipt_seen.is_set()
    return {'acknowledged': acknowledged, 'wait_seconds': time.monotonic()-started,
            'end_reason': 'browser_ack' if acknowledged else 'local_exit' if closed else 'timeout',
            'maximum_wait_seconds': timeout, 'scope': 'browser_receipt_delivery_only'}
'''
web_path = PARENT/'trial_web_v5_final_receipt.py'
web_path.write_text(web)
(HERE/'resilient_trial.js').write_text(web.split('<script>')[1].split('</script>')[0].strip()+'\n')
(HERE/'web.diff').write_text(''.join(difflib.unified_diff(original_web.splitlines(True),web.splitlines(True),fromfile=web_source.name,tofile=web_path.name)))
runner_source = PARENT/'run_trial_v13_web_resilient.py'
runner = runner_source.read_text()
assert sha(runner.encode()) == '68da75829e08d38e5908eed7e9e824b2dd52e7482340aa35f24ad1fd1da5c50f'
original_runner = runner
runner = runner.replace('trial_web_v4_resilient', 'trial_web_v5_final_receipt')
runner = replace_once(runner, 'from trial_web_v5_final_receipt import TrialState, start_server', 'from trial_web_v5_final_receipt import TrialState, start_server, wait_for_final_receipt')
runner = runner.replace('web-resilient-STATE.json','web-final-receipt-STATE.json').replace('try2webinternal','try2finalinternal').replace("'try2web'", "'try2final'")
runner = replace_once(runner, '        nonlocal stop_cause\n', '''        nonlocal stop_cause
        if trial.phase == 'finished':
            trial.final_receipt_close.set()
            return
''')
runner = replace_once(runner, '        time.sleep(2)\n        server.shutdown()', '''        final_delivery = wait_for_final_receipt(trial)
        (run/'trial-web-final-receipt.json').write_text(json.dumps(final_delivery, ensure_ascii=False, indent=2)+'\\n')
        server.shutdown()''')
runner_path = PARENT/'run_trial_v14_final_receipt.py'
runner_path.write_text(runner)
(HERE/'runner.diff').write_text(''.join(difflib.unified_diff(original_runner.splitlines(True),runner.splitlines(True),fromfile=runner_source.name,tofile=runner_path.name)))
(HERE/'build-receipt.json').write_text(json.dumps({'scope':'host_only_no_guest_or_default_entry_changes',
    'web_source':str(web_source),'web_source_sha256':sha(original_web.encode()),'web_candidate':str(web_path),'web_candidate_sha256':sha(web.encode()),
    'runner_source':str(runner_source),'runner_source_sha256':sha(original_runner.encode()),'runner_candidate':str(runner_path),'runner_candidate_sha256':sha(runner.encode())},indent=2)+'\n')
print('Built v5 web / v14 runner; no QEMU invocation')
