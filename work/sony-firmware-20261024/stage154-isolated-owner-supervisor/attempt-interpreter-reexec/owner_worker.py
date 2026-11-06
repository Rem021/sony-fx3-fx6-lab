#!/usr/bin/env python3
"""Fixture-only isolated worker. No live-I/O branch or privileged launch exists."""
from pathlib import Path
from hashlib import sha256
import ctypes as C
import json
import os
import re
import secrets
import sys
import time
import owner_binding as B
from shared_job import FixtureAPI,Shared,checked_build,put_once


def main():
    if len(sys.argv)!=3:raise B.Rejected('one job directory and nonce required')
    directory=Path(sys.argv[1]);nonce=sys.argv[2]
    if not re.fullmatch('[0-9a-f]{32}',nonce):raise B.Rejected('invalid job nonce')
    spec=json.loads((directory/'spec.json').read_text())
    if spec['nonce']!=nonce or spec['mode']!='fixture':raise B.Rejected('this worker accepts own fixtures only')
    build=checked_build()
    if spec['build_sha256']!=sha256((Path(__file__).parent/'build-receipt.json').read_bytes()).hexdigest():raise B.Rejected('build receipt changed')
    api=FixtureAPI()
    if spec['fixture_sha256']!=api.fixture_sha:raise B.Rejected('fixture differs')
    shared=Shared(directory/'shared.bin',api,expected_identity=spec['shared_identity'])
    control=B.Control.from_buffer(shared.mapping,0)
    result=B.Result.from_buffer(shared.mapping,api.result_offset)
    gate=B.FixtureGate.from_buffer(shared.mapping,api.gate_offset)
    if control.abi!=2:raise B.Rejected('shared control ABI differs')
    if api.fx3_ipc_install_handlers(shared.address)!=0:raise B.Rejected('cooperative signal setup failed')
    config=B.Config(abi=2,arm=0x4f574e33,location=0x02100000,capture_permitted=1,vid=0x054c,pid=0x0da1,
        work_deadline_ns=spec['work_deadline_ns'],final_deadline_ns=spec['final_deadline_ns'])
    config.privacy_key[:]=secrets.token_bytes(32)  # Never written to a receipt.
    options=spec['fixture']
    api.fx3_owner_fixture_reset(options.get('fail_phase',0),options.get('option',0)|512,0)
    if options.get('block_phase',0):api.fx3_owner_fixture_block(options['block_phase'],C.byref(gate))
    put_once(directory/'worker-ready.json',{'nonce':nonce,'pid':os.getpid(),'fixture_only':True})
    rc=api.run(C.byref(config),C.byref(result),C.byref(control))
    if rc!=result.status:raise B.Rejected('native result and return differ')
    put_once(directory/'native-returned.json',{'nonce':nonce,'native_return_low32':rc,'not_worker_exit':True})
    delay=options.get('receipt_delay_s',0)
    if type(delay) not in (int,float) or not 0<=delay<=1:raise B.Rejected('invalid fixture receipt delay')
    if delay:time.sleep(delay)
    if options.get('exit_without_receipt'):os._exit(0)
    report={'nonce':nonce if not options.get('bad_receipt_nonce') else '0'*32,'mode':'fixture',
        'fixture_sha256':api.fixture_sha,'build_sha256':spec['build_sha256'],'pid':os.getpid(),
        'native_function_returned':True,'native_return':rc,'native_result_sha256':sha256(shared.result_bytes()).hexdigest(),
        'result':B.public_result(result),'calls':{str(n):api.fx3_owner_fixture_calls(n) for n in range(1,13)},
        'actual_IOKit_or_camera_operations':0,'physical_driver_or_camera_acceptance':False}
    put_once(directory/'worker-result.json',report)
    # Keep the signal target/mapping valid through process exit; no destructor
    # closes the mapping while an asynchronous handler could still use it.
    os._exit(0)


if __name__=='__main__':
    try:main()
    except BaseException as error:
        print(type(error).__name__+': '+str(error),file=sys.stderr,flush=True)
        os._exit(2)
