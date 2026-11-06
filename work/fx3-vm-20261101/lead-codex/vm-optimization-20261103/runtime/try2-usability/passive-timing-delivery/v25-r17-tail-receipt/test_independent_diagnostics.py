#!/usr/bin/env python3
"""Execute the actual runner finally AST with fake QMP/process; no VM."""
import ast
import json
import os
import shlex
import signal
import subprocess
import tempfile
import time
from pathlib import Path

import quiesced_diag_readback
import optional_paused_snapshots

HERE = Path(__file__).resolve().parent
source = ast.parse((HERE/'run_trial_v25_diag_r3.py').read_text())
main = next(n for n in source.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
finals = [n.finalbody for n in ast.walk(main) if isinstance(n, ast.Try) and n.finalbody]
target = next(body for body in finals if 'trial.update(ready=False' in ast.unparse(body))
code = compile(ast.Module(body=target, type_ignores=[]), '<actual-runner-finally>', 'exec')
assigns=[n for n in ast.walk(main) if isinstance(n,ast.Assign) and len(n.targets)==1
         and isinstance(n.targets[0],ast.Name)]
diag_assign=next(n for n in assigns if n.targets[0].id=='diagnostic_readback_pass')
health_assign=next(n for n in assigns if n.targets[0].id=='health_pass'
                   and 'diagnostic_readback_pass' in ast.unparse(n.value))
assert ast.unparse(diag_assign.value)=="shutdown.get('diag_snapshot', {}).get('consistent') is True"
assert ast.unparse(health_assign.value)=='bool(health_pass and diagnostic_readback_pass)'
diag_gate=compile(ast.Expression(diag_assign.value),'<runner-diagnostic-gate>','eval')
health_gate=compile(ast.Expression(health_assign.value),'<runner-health-gate>','eval')
B_RING = (HERE.parents[1]/'runs/v25procdiag-web-r6-d4254d75/osd-ring-final.bin').resolve()
assert B_RING.is_file() and B_RING.stat().st_size == quiesced_diag_readback.SIZE


class Process:
    pid = 987654321
    def __init__(self): self.rc = None; self.waits = 0
    def poll(self): return self.rc
    def wait(self, timeout=None): self.waits += 1; self.rc = 0; return 0


class Transport:
    def __init__(self, unknown=False): self.send_unknown=unknown; self.defaults=[]
    def set_default_timeout(self, value): self.defaults.append(value)


class Trial:
    def __init__(self): self.stop=type('Stop',(),{'set':lambda self:None})()
    def update(self, **kw): self.last=kw


class Monitor:
    selected=['FX3_FILE100_OBSERVER_READY']
    def poll(self): pass


def scenario(name, *, ring='zero', pause=True, optional='ok', unknown=False,
             native_file_error=False, parsed_write_error=False, receipt_write_error=False,
             pause_recheck_false=False):
    with tempfile.TemporaryDirectory() as temp:
        run=Path(temp)
        if parsed_write_error: (run/'osd-ring-final-diag.json').mkdir()
        if receipt_write_error: (run/'osd-ring-final-readback-receipt.json').mkdir()
        p=Process();transport=Transport(unknown)
        calls=[];restores=[];status_calls=[]
        def qmp(cmd, arguments=None, *, timeout=None):
            calls.append((cmd,timeout,arguments))
            if cmd=='query-status':
                status_calls.append(True)
                now_paused=pause and not (pause_recheck_false and len(status_calls)>=3)
                return {'return':{'running':not now_paused,
                                  'status':'paused' if now_paused else 'running'}}
            if cmd=='stop': return {'return':{}}
            if cmd=='human-monitor-command':
                parts=shlex.split(arguments['command-line'])
                assert parts[0]=='pmemsave'
                address=int(parts[1],0);size=int(parts[2],0);path=Path(parts[3])
                if address==quiesced_diag_readback.ADDRESS:
                    if ring=='qmp_error':return {'error':{'class':'GenericError'}}
                    payload=(B_RING.read_bytes() if ring=='valid' else b'\0'*size if ring=='zero' else b'bad')
                else:
                    if optional=='qmp_error':return {'error':{'class':'GenericError'}}
                    if optional=='timeout':
                        transport.send_unknown=True
                        raise TimeoutError('QMP reply identity unknown')
                    payload=b'U'*size
                path.write_bytes(payload)
                return {'return':''}
            if cmd=='quit': p.rc=0;return {'return':{}}
            raise AssertionError(cmd)
        def restore(*args,**kwargs):
            restores.append(True)
            return {'passed':True,'reason':'guest_acknowledged_and_original_bytes_verified'}
        def native_file(*args):
            if native_file_error:raise OSError('native file artifact write failed')
            return {'passed':True}
        shutdown={};journal=[]
        env={'trial':Trial(),'p':p,'qmp':qmp,'transport':transport,'run':run,
             'shutdown':shutdown,'journal':journal,'snapshots':[
                 {'name':'osd-ring-final.bin','address':quiesced_diag_readback.ADDRESS,'size':quiesced_diag_readback.SIZE},
                 {'name':'ui-gate-counters.bin','address':0x41dc00000,'size':65536},
                 {'name':'capid-reserved-ram.bin','address':0x41d800000,'size':4096}],
             'ring_reader':None,'early_stop_reason':None,'log_monitor':Monitor(),
             'native_file_reads':[],'input_gate':None,'s':None,
             'is_proven_prelaunch':lambda x:False,
             'capture_quiesced_diag':quiesced_diag_readback.capture,
             'capture_optional_paused_snapshots':optional_paused_snapshots.capture,
             'capture_optional_guest_tasks':lambda *x:None,
             'capture_optional_vcpus':lambda *x:None,
             'capture_native_file':native_file,'restore_native_api':restore,
             'subprocess':subprocess,'os':os,'signal':signal,'time':time}
        exec(code,env)
        diag=shutdown['diag_snapshot'];opt=shutdown['optional_snapshots']
        ui=[x for x in opt.get('items',[]) if x['name']=='ui-gate-counters.bin']
        assert shutdown.get('quit_sent') and p.rc==0 and p.waits==1,name
        pmem=[shlex.split(x[2]['command-line']) for x in calls if x[0]=='human-monitor-command']
        if pmem:
            assert int(pmem[0][1],0)==quiesced_diag_readback.ADDRESS
            assert int(pmem[0][2],0)==quiesced_diag_readback.SIZE
        if opt.get('attempted'):
            assert int(pmem[1][1],0)==0x41dc00000 and int(pmem[1][2],0)==65536
        if not transport.send_unknown:assert restores and shutdown['API16_restored'] is True,name
        else:assert not restores and shutdown['restore_error']=='transport_send_unknown_before_restore'
        if ring=='zero':
            assert diag['readback_complete'] and diag['bytes']==16777216 and not diag['parse_valid']
            assert diag['consistent'] is False and 'parse_error' in diag
            if pause_recheck_false:assert not opt['attempted'] and not opt['paused_reproved']
            else:assert ui and ui[0]['status']==('failed' if optional in ('qmp_error','timeout') else 'complete')
            diagnostic_readback_pass=eval(diag_gate,{'shutdown':shutdown})
            assert diagnostic_readback_pass is False
            assert eval(health_gate,{'health_pass':True,
                                     'diagnostic_readback_pass':diagnostic_readback_pass}) is False
        if ring=='valid':
            assert diag['consistent'] is (not parsed_write_error and not receipt_write_error)
            assert diag['parse_valid'] and diag['readback_complete']
            assert ui and ui[0]['status']=='complete'
        if ring=='bad' and pause and not unknown:
            assert not diag['readback_complete'] and not opt['attempted']
        if ring=='qmp_error' or not pause or unknown:assert not opt['attempted']
        if optional=='qmp_error':assert ui and ui[0]['status']=='failed' and restores
        if optional=='timeout':
            assert ui and ui[0]['status']=='failed' and not restores
            assert len(pmem)==2  # core ring once, UI once; no second optional read
        if native_file_error:assert 'optional_native_file_error' in shutdown and restores
        if parsed_write_error:assert 'parsed_artifact_write_error' in diag and 'parse_error' not in diag
        if receipt_write_error:assert 'receipt_write_error' in diag and diag['parse_valid']
        print('PASS actual cleanup',name)


scenario('zero_complete_optional_ui')
scenario('valid_equivalent',ring='valid')
scenario('nonpaused',pause=False,ring='bad')
scenario('pause_recheck_refused',pause_recheck_false=True)
scenario('unknown',unknown=True,ring='bad')
scenario('bad_length',ring='bad')
scenario('core_qmp_error',ring='qmp_error')
scenario('optional_qmp_error',optional='qmp_error')
scenario('optional_timeout_unknown',optional='timeout')
scenario('native_file_write_error',ring='valid',native_file_error=True)
scenario('parsed_artifact_write_error',ring='valid',parsed_write_error=True)
scenario('receipt_write_error',ring='valid',receipt_write_error=True)

clock_ticks=iter([0.0,0.001,0.02])
with tempfile.TemporaryDirectory() as temp:
    qcalls=[]
    def qmp_budget(cmd,args=None,*,timeout=None):
        qcalls.append((cmd,timeout));return {'return':{'running':False,'status':'paused'}}
    r=optional_paused_snapshots.capture(qmp_budget,Transport(),Path(temp),
        [{'name':'ui-gate-counters.bin','address':0x41dc00000,'size':65536}],budget=.01,
        clock=lambda:next(clock_ticks))
    assert r['paused_reproved'] and r['items'][0]['status']=='not_attempted_budget_exhausted'
    assert [x[0] for x in qcalls]==['query-status']
print('PASS absolute optional QMP budget; no VM')
