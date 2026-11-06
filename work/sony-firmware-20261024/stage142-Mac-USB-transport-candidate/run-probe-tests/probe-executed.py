#!/usr/bin/env python3
"""Default: local plan only. Real metadata requires a separate one-shot release."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import importlib.util
import json
import os
import plistlib
import subprocess
import sys
import uuid

HERE=Path(__file__).resolve().parent
CLAIM=HERE/'descriptor-probe-claim.json'
RESULT=HERE/'descriptor-probe-result.json'


def local_module(name,filename):
    spec=importlib.util.spec_from_file_location(name,HERE/filename)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def plan():
    cache=json.loads((HERE/'current-cache-target.json').read_text())
    build=json.loads((HERE/'native-build-receipt.json').read_text())
    return {'status':'PREPARED_NOT_RELEASED_FOR_REAL_USB',
        'probe_id':'stage142-fx3-msc-descriptors-v1',
        'target':{'locationID':cache['unique_target_location'],'VID':0x054c,'PID':0x0da1},
        'cached_target_time':cache['created_utc'],'fresh_cache_must_match_before_worker':True,
        'native_library':build['library'],
        'explicit_device_GET_DESCRIPTOR_budget':1,
        'configuration_descriptor_and_interface_metadata_APIs':True,
        'total_OS_generated_wire_requests_not_measured_or_guaranteed':True,
        'worker_deadline_seconds':15,'kill_completion_wait_seconds':2,
        'one_shot_claim_retained_even_if_USB_result_unknown':True,
        'no_device_open_interface_claim_or_driver_detach':True,
        'no_vendor_authentication_service_mode_media_or_firmware_commands':True,
        'native_library_loaded_by_this_plan':False,'goal_complete':False}


def save_exclusive(path,value):
    with path.open('x') as handle:
        json.dump(value,handle,ensure_ascii=False,indent=2);handle.write('\n')
        handle.flush();os.fsync(handle.fileno())


def run_bounded_worker(argv):
    child=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        out,err=child.communicate(timeout=15)
        if child.returncode!=0:
            return {'status':'WORKER_ERROR_NOT_CAMERA_HEALTH_PROOF','returncode':child.returncode,
                    'stderr_bytes':len(err),'stderr_sha256':sha256(err).hexdigest()}
        if len(out)>65536:return {'status':'OVERSIZED_WORKER_RESULT_UNKNOWN'}
        try:value=json.loads(out)
        except (ValueError,UnicodeDecodeError):return {'status':'INVALID_WORKER_RESULT_UNKNOWN'}
        if not isinstance(value,dict) or value.get('status')!='METADATA_RETURNED_NOT_AUTH_BACKUP_OR_RECOVERY':
            return {'status':'UNEXPECTED_WORKER_RESULT_UNKNOWN'}
        return value
    except subprocess.TimeoutExpired:
        try:child.kill()
        except ProcessLookupError:pass
        ended=False
        try:child.communicate(timeout=2);ended=True
        except subprocess.TimeoutExpired:
            # Do not wait indefinitely or launch replacement workers.
            child.stdout.close();child.stderr.close()
        return {'status':'DEADLINE_CAMERA_STATE_UNKNOWN','worker_termination_observed':ended,
                'worker_pid':child.pid,'no_retry_or_driver_recovery_attempted':True}


def execute_once():
    p=plan();target=p['target'];location=target['locationID']
    t=local_module('descriptor_transport_for_probe','descriptor_transport.py')
    t.check_authority(location)  # Current authority rejects HERE before cache query, fork or CDLL.
    if CLAIM.exists() or RESULT.exists():raise t.TransportError('one-shot already attempted; no automatic rerun')
    volume=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T'],timeout=10))
    if volume['VolumeUUID']!='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B' or not volume['WritableVolume']:
        raise t.TransportError('wrong or unwritable evidence volume')
    collector=local_module('descriptor_probe_cache_only','cached_target_selection.py')
    raw=subprocess.run(['/usr/sbin/ioreg','-a','-p','IOUSB','-l','-w','0'],
                       capture_output=True,check=True,timeout=15).stdout
    cache=collector.sanitize(raw)
    if cache['candidate_count']!=1 or cache['unique_target_location']!=location:
        raise t.TransportError('fresh cached target is absent, ambiguous or moved')
    nonce=uuid.uuid4().hex
    claim={'probe_id':t.PROBE_ID,'locationID':location,'parent_pid':os.getpid(),'nonce':nonce,
           'created_utc':datetime.now(timezone.utc).isoformat(),'fresh_cache':cache,
           'claim_does_not_prove_USB_execution_or_completion':True}
    save_exclusive(CLAIM,claim)
    report=run_bounded_worker([sys.executable,'-B',str(Path(__file__).resolve()),'--_worker',str(location),nonce])
    report.update({'probe_id':t.PROBE_ID,'created_utc':datetime.now(timezone.utc).isoformat(),
                   'same_body_firmware_version_driver_ownership_recording_or_recovery_proven':False})
    save_exclusive(RESULT,report)
    return report


def worker(location,nonce):
    t=local_module('descriptor_transport_worker','descriptor_transport.py')
    t.check_authority(location)
    claim=json.loads(CLAIM.read_text())
    if claim.get('probe_id')!=t.PROBE_ID or claim.get('locationID')!=location or \
       claim.get('parent_pid')!=os.getppid() or claim.get('nonce')!=nonce or RESULT.exists():
        raise t.TransportError('worker does not match the single parent claim')
    report=t.query_descriptors(t.load_live(location),location)
    return {'status':'METADATA_RETURNED_NOT_AUTH_BACKUP_OR_RECOVERY','descriptors':report}


def main(argv=None):
    args=sys.argv[1:] if argv is None else argv
    try:
        if args in ([],['--plan']):value=plan()
        elif args==['--query-descriptors']:value=execute_once()
        elif len(args)==3 and args[0]=='--_worker':value=worker(int(args[1]),args[2])
        else:raise ValueError('use --plan or a separately authorized --query-descriptors')
        print(json.dumps(value,ensure_ascii=False));return 0
    except Exception as exc:
        print(json.dumps({'status':'REFUSED_OR_FAILED_NO_AUTOMATIC_RETRY','error':str(exc),
                          'camera_health_or_completion_proven':False},ensure_ascii=False));return 2


if __name__=='__main__':raise SystemExit(main())
