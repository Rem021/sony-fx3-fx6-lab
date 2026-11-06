#!/usr/bin/env python3
"""Existing host processes and own short-lived process; no admin or USB."""
from pathlib import Path
from hashlib import sha256
import ctypes as C
import errno
import json
import os
import subprocess
import entry_binding as E

HERE=Path(__file__).resolve().parent


def main():
    out=HERE/'artifacts/host-identity-reference'
    argv=['xcrun','clang','-std=c11','-Wall','-Wextra','-Werror',
        str(HERE/'host_identity_reference.c'),'-o',str(out)]
    build=subprocess.run(argv,capture_output=True,text=True)
    if build.returncode:
        (HERE/'host-reference-build-failure.json').write_text(json.dumps({'argv':argv,'stderr':build.stderr},indent=2)+'\n')
        raise AssertionError('host reference compile failed')
    deps=subprocess.check_output(['otool','-L',str(out)],text=True)
    assert 'IOKit' not in deps and 'libusb' not in deps
    ipc=E.IPC();cases=[];reference=[]
    for pid in [os.getpid(),1]:
        measured=ipc.identity(pid);assert measured is not None
        independent=json.loads(subprocess.check_output([str(out),str(pid)],text=True))
        assert independent['short_return']==independent['short_size']
        assert measured['uid']==independent['short_uid']
        assert measured['birth_sec']>0 and 0<=measured['birth_usec']<1000000
        if pid==os.getpid():
            assert independent['full_return']==independent['full_size']
            assert (measured['uid'],measured['birth_sec'],measured['birth_usec'])==(
                independent['full_uid'],independent['full_birth_sec'],independent['full_birth_usec'])
        else:assert measured['uid']==0 and measured['path']=='/sbin/launchd'
        reference.append({'new_kernel_identity':measured,'separate_BSD_reference':independent})
        cases.append({'name':'own_microsecond_identity_matches_original_full_BSD' if pid!=1 else 'existing_root_identity_matches_short_BSD_and_path',
            'pid':pid,'old_full_info_errno':independent['full_errno']})

    real=ipc.fx3_entry_pid_info;count=0
    def changed(pid,uid,sec,usec):
        nonlocal count
        rc=real(pid,uid,sec,usec);count+=1
        if rc==0 and count==2:C.cast(usec,C.POINTER(C.c_uint64)).contents.value+=1
        return rc
    ipc.fx3_entry_pid_info=changed
    try:ipc.identity(os.getpid())
    except OSError as error:assert error.errno==errno.EAGAIN
    else:raise AssertionError('mixed process incarnation accepted')
    ipc.fx3_entry_pid_info=real
    cases.append({'name':'changed_identity_across_path_lookup_is_rejected','errno':errno.EAGAIN})

    def unavailable(pid,uid,sec,usec):C.set_errno(errno.EPERM);return -1
    ipc.fx3_entry_pid_info=unavailable
    try:ipc.identity(os.getpid())
    except OSError as error:assert error.errno==errno.EPERM
    else:raise AssertionError('metadata failure accepted as exit')
    ipc.fx3_entry_pid_info=real
    cases.append({'name':'live_metadata_failure_retains_errno_and_is_not_exit','errno':errno.EPERM})

    child=subprocess.Popen(['/usr/bin/true']);pid=child.pid;assert child.wait()==0
    assert ipc.identity(pid) is None
    cases.append({'name':'actual_own_reaped_process_is_absent','pid':pid})

    no_such=0x7fffffff
    assert ipc.identity(no_such) is None
    cases.append({'name':'nonexistent_pid_is_absent_without_a_signal','pid':no_such})
    report={'status':'PASS_CROSS_UID_KERNEL_IDENTITY_NOT_ROOT_HELPER_OR_DEVICE_ACCEPTANCE',
        'checks':len(cases),'cases':cases,'reference':reference,'build_argv':argv,
        'reference_source_sha256':sha256((HERE/'host_identity_reference.c').read_bytes()).hexdigest(),
        'reference_executable_sha256':sha256(out.read_bytes()).hexdigest(),'reference_dependencies':deps,
        'root_process_launched':False,'root_helper_or_IOKit_executed':False,'administrator_prompt_requested':False,'new_device_operations':0}
    with (HERE/'kernel-identity-tests.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps({'checks':len(cases),'existing_root_PID_metadata_verified':True,'root_or_device_operations':0}))


if __name__=='__main__':main()
