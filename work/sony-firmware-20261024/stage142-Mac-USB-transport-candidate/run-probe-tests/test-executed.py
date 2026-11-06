#!/usr/bin/env python3
"""No real native loader, process or USB call is allowed in these probe tests."""
from pathlib import Path
from hashlib import sha256
import ctypes as C
import importlib.util
import io
import json
import plistlib
import subprocess
import tempfile
from contextlib import redirect_stdout
from types import SimpleNamespace
from unittest.mock import patch,Mock

HERE=Path(__file__).resolve().parent


def module(name,file):
    spec=importlib.util.spec_from_file_location(name,HERE/file)
    item=importlib.util.module_from_spec(spec);spec.loader.exec_module(item);return item


def main():
    p=module('probe_under_test','descriptor_probe.py')
    t=module('transport_for_guards','descriptor_transport.py')
    cases=[]
    with patch.object(C,'CDLL',side_effect=AssertionError('no native loading')), \
         patch.object(subprocess,'Popen',side_effect=AssertionError('no real subprocess')):
        assert not p.plan()['native_library_loaded_by_this_plan'];cases.append('plan local only')
        with redirect_stdout(io.StringIO()) as output:code=p.main(['--query-descriptors'])
        assert code==2 and json.loads(output.getvalue())['status']=='REFUSED_OR_FAILED_NO_AUTOMATIC_RETRY'
        assert not p.CLAIM.exists() and not p.RESULT.exists();cases.append('current authority refuses before cache fork or claim')
        try:t.load_live(0x12340000,0x0336)
        except t.TransportError:cases.append('service PID rejected before native load')
        else:raise AssertionError('service PID admitted')
    with tempfile.TemporaryDirectory(prefix='probe-fixtures-',dir=HERE/'work-tmp') as directory:
        root=Path(directory)
        fixed=p.plan()['target']['locationID']
        t_fake=SimpleNamespace(PROBE_ID=t.PROBE_ID,TransportError=t.TransportError,check_authority=lambda location:None)
        cache={'candidate_count':1,'unique_target_location':fixed,'candidates':[]}
        collector=SimpleNamespace(sanitize=lambda raw:cache)
        def modules(name,file):return t_fake if file=='descriptor_transport.py' else collector
        volume=plistlib.dumps({'VolumeUUID':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','WritableVolume':True})
        metadata={'status':'METADATA_RETURNED_NOT_AUTH_BACKUP_OR_RECOVERY','descriptors':{'synthetic_fixture':True}}
        with patch.object(p,'CLAIM',root/'claim.json'),patch.object(p,'RESULT',root/'result.json'), \
             patch.object(p,'local_module',side_effect=modules), \
             patch.object(subprocess,'check_output',return_value=volume), \
             patch.object(subprocess,'run',return_value=SimpleNamespace(stdout=b'fixture')) as cache_command, \
             patch.object(p,'run_bounded_worker',return_value=metadata.copy()) as bounded:
            result=p.execute_once()
            assert result['descriptors']['synthetic_fixture'] and not result['same_body_firmware_version_driver_ownership_recording_or_recovery_proven']
            assert bounded.call_count==1 and cache_command.call_count==1
            assert p.CLAIM.exists() and p.RESULT.exists();cases.append('synthetic allowed parent preserves claim and result')
            try:p.execute_once()
            except t.TransportError:pass
            else:raise AssertionError('one shot reran')
            assert bounded.call_count==1 and cache_command.call_count==1;cases.append('second attempt refused before cache or worker')
        for label,cache_case in [('absent',{'candidate_count':0,'unique_target_location':None}),
                                 ('moved',{'candidate_count':1,'unique_target_location':fixed+1}),
                                 ('ambiguous',{'candidate_count':2,'unique_target_location':fixed})]:
            collector.sanitize=lambda raw,result=cache_case:result
            with patch.object(p,'CLAIM',root/(label+'claim.json')),patch.object(p,'RESULT',root/(label+'result.json')), \
                 patch.object(p,'local_module',side_effect=modules),patch.object(subprocess,'check_output',return_value=volume), \
                 patch.object(subprocess,'run',return_value=SimpleNamespace(stdout=b'fixture')), \
                 patch.object(p,'run_bounded_worker',side_effect=AssertionError('must not start')):
                try:p.execute_once()
                except t.TransportError:pass
                else:raise AssertionError(label+' admitted')
                assert not p.CLAIM.exists();cases.append('cached '+label+' refuses before claim and worker')
        collector.sanitize=lambda raw:cache
        valid_claim={'probe_id':t.PROBE_ID,'locationID':fixed,'parent_pid':p.os.getppid(),'nonce':'fixture-nonce'}
        for label,change in [('nonce',{'nonce':'wrong'}),('parent',{'parent_pid':0}),
                             ('location',{'locationID':fixed+1}),('probe',{'probe_id':'wrong'})]:
            claim=valid_claim|change
            cpath=root/(label+'-worker-claim.json');cpath.write_text(json.dumps(claim))
            with patch.object(p,'CLAIM',cpath),patch.object(p,'RESULT',root/'unused-result.json'), \
                 patch.object(p,'local_module',return_value=t_fake), \
                 patch.object(C,'CDLL',side_effect=AssertionError('must not load')):
                try:p.worker(fixed,'fixture-nonce')
                except t.TransportError:pass
                else:raise AssertionError('worker claim '+label+' admitted')
                cases.append('worker rejects mismatched '+label)
    for label,returncode,outputs,want,kills in [
        ('metadata',0,[(json.dumps({'status':'METADATA_RETURNED_NOT_AUTH_BACKUP_OR_RECOVERY'}).encode(),b'')], 'METADATA_RETURNED_NOT_AUTH_BACKUP_OR_RECOVERY',0),
        ('error',2,[(b'ignored',b'fixture-error')],'WORKER_ERROR_NOT_CAMERA_HEALTH_PROOF',0),
        ('invalid JSON',0,[(b'not-json',b'')],'INVALID_WORKER_RESULT_UNKNOWN',0),
        ('wrong schema',0,[(b'[]',b'')],'UNEXPECTED_WORKER_RESULT_UNKNOWN',0),
        ('oversized',0,[(b'x'*65537,b'')],'OVERSIZED_WORKER_RESULT_UNKNOWN',0),
        ('timeout killed',-9,[subprocess.TimeoutExpired('fixture',15),(b'',b'')],'DEADLINE_CAMERA_STATE_UNKNOWN',1),
        ('timeout still unknown',None,[subprocess.TimeoutExpired('fixture',15),subprocess.TimeoutExpired('fixture',2)],'DEADLINE_CAMERA_STATE_UNKNOWN',1)]:
        child=SimpleNamespace(returncode=returncode,pid=777,communicate=Mock(side_effect=outputs),
                              kill=Mock(),stdout=io.BytesIO(),stderr=io.BytesIO())
        with patch.object(subprocess,'Popen',return_value=child) as launch:
            result=p.run_bounded_worker(['fixture-only'])
        assert result['status']==want and child.kill.call_count==kills and launch.call_count==1
        if label=='timeout still unknown':assert not result['worker_termination_observed']
        cases.append('bounded worker '+label)
    out=HERE/'run-probe-tests';out.mkdir(exist_ok=False)
    for target,source in [('probe-executed.py','descriptor_probe.py'),('test-executed.py','test_descriptor_probe.py')]:
        (out/target).write_bytes((HERE/source).read_bytes())
    report={'status':'PASS_PROBE_BOUNDARIES_WITH_SYNTHETIC_WORKER_NO_REAL_NATIVE_OR_USB',
            'cases':cases,'case_count':len(cases),'probe_sha256':sha256((HERE/'descriptor_probe.py').read_bytes()).hexdigest(),
            'test_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),
            'real_native_load_USB_driver_or_camera_operations':0,'one_shot_real_claim_created':False}
    with (out/'results.json').open('x') as handle:json.dump(report,handle,ensure_ascii=False,indent=2);handle.write('\n')
    print(json.dumps({'status':report['status'],'cases':len(cases),'real_USB_operations':0}))


if __name__=='__main__':main()
