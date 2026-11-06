#!/usr/bin/env python3
"""Run only the fixed C fixture executable; never run the IOKit/native helper."""
from pathlib import Path
from hashlib import sha256
import json
import os
import subprocess
import time
import entry_binding as E

HERE=Path(__file__).resolve().parent


def wait_for(check,seconds=3):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        if check():return
        time.sleep(.01)
    raise AssertionError('fixture condition not observed')


def main():
    build=json.loads((HERE/'helper-build-receipt.json').read_text())
    helper=HERE/build['fixture']['path']
    assert sha256(helper.read_bytes()).hexdigest()==build['fixture']['sha256']
    assert 'IOKit' not in build['fixture']['dependencies'] and 'libusb' not in build['fixture']['dependencies']
    ipc=E.IPC();frames=[];processes=[];cases=[]
    root=HERE/'runs/helper-fixture-tests';root.mkdir(mode=0o700,exist_ok=False)
    def frame(name,**kwargs):
        directory=root/name;directory.mkdir(mode=0o700)
        f=E.Frame(directory/'shared.bin',ipc,**kwargs);frames.append(f);return f
    def launch(f,nonce=None,path=None):
        p=subprocess.Popen([str(helper),str(path or f.path),nonce or f.nonce.hex()],stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        processes.append((p,f));return p
    def finish(p):
        out,err=p.communicate(timeout=3)
        return p.returncode,out.decode(),err.decode()
    try:
        f=frame('normal');p=launch(f);code,out,err=finish(p);r=json.loads(out)
        assert code==0 and r['mode']=='fixture' and r['native_return']==0
        assert r['nonce']==f.nonce.hex() and r['result_sha256']==sha256(f.result_bytes()).hexdigest()
        assert f.grant.attempt_claimed==f.grant.native_started==f.grant.native_completed==1
        cases.append({'name':'fixed_executable_normal','exit':code,'receipt':r})
        old=sha256(f.mapping[:]).hexdigest();code,out,err=finish(launch(f))
        assert code==66 and not out and 'consumed_or_wrong_grant' in err and sha256(f.mapping[:]).hexdigest()==old
        cases.append({'name':'separate_process_replay_denied_without_overwriting_result','exit':code})

        f=frame('concurrent',block_phase=4);first=launch(f)
        wait_for(lambda:f.entered()==4)
        assert first.poll() is None and f.pending()==4
        uid=E.C.c_uint32();sec=E.C.c_uint64();usec=E.C.c_uint64()
        assert ipc.fx3_entry_pid_info(f.grant.native_pid,E.C.byref(uid),E.C.byref(sec),E.C.byref(usec))==0
        assert (f.grant.native_pid,uid.value,sec.value,usec.value)==(first.pid,os.getuid(),f.grant.birth_sec,f.grant.birth_usec)
        old=sha256(f.mapping[:]).hexdigest();code,out,err=finish(launch(f))
        assert code==66 and first.poll() is None and f.pending()==4 and sha256(f.mapping[:]).hexdigest()==old
        f.stop();f.release_fixture();code,out,err=finish(first);r=json.loads(out)
        assert code==0 and r['native_return'] in (1,2) and r['fixture_calls'][4]==r['fixture_calls'][6]==0
        assert r['fixture_calls'][9]==r['fixture_calls'][10]==1
        cases.append({'name':'concurrent_replay_and_kernel_birth_identity','receipt':r,'single_native_pid_preserved':True})

        f=frame('wrong-body',expected_tag=bytes([0x42])*32,observed_tag=bytes([0x41])*32)
        code,out,err=finish(launch(f));r=json.loads(out)
        assert code==0 and r['native_return']==2 and r['fixture_calls'][0]==1
        assert r['fixture_calls'][1]==r['fixture_calls'][3]==r['fixture_calls'][6]==0
        cases.append({'name':'preselected_body_mismatch_blocks_client_capture_and_claim','receipt':r})

        for name,change in [
            ('missing-body-tag',lambda f:f.grant.expected_body_tag.__setitem__(slice(None),bytes(32))),
            ('missing-privacy-key',lambda f:f.grant.privacy_key.__setitem__(slice(None),bytes(32))),
            ('wrong-mode',lambda f:setattr(f.grant,'mode',0)),
            ('wrong-owner',lambda f:setattr(f.grant,'owner_uid',os.getuid()+1))]:
            f=frame(name);change(f);f.mapping.flush();code,out,err=finish(launch(f))
            assert code==65 and not out and f.grant.attempt_claimed==0
            cases.append({'name':name,'rejected_before_native_claim':True})
        f=frame('wrong-nonce');code,out,err=finish(launch(f,'00'*16))
        assert code==66 and f.grant.attempt_claimed==0
        cases.append({'name':'wrong-nonce','rejected_before_native_claim':True})
        f=frame('wrong-mode-file');os.chmod(f.path,0o644);code,out,err=finish(launch(f))
        assert code==65 and f.grant.attempt_claimed==0
        cases.append({'name':'wrong-file-permissions','rejected_before_mapping_and_claim':True})
        f=frame('symlink');link=f.path.with_name('symlink.bin');link.symlink_to(f.path)
        code,out,err=finish(launch(f,path=link));assert code==65 and f.grant.attempt_claimed==0
        cases.append({'name':'final-symlink','rejected':True})
        f=frame('hardlink');link=f.path.with_name('hardlink.bin');os.link(f.path,link)
        code,out,err=finish(launch(f));assert code==65 and f.grant.attempt_claimed==0
        cases.append({'name':'hardlinked-frame','rejected':True})
        outside=E.Frame(HERE/'outside-fixture-shared.bin',ipc);frames.append(outside)
        code,out,err=finish(launch(outside));assert code==65 and outside.grant.attempt_claimed==0
        cases.append({'name':'outside-reviewed-job-root','rejected':True})
    finally:
        for p,f in processes:
            if p.poll() is None:
                f.stop();f.release_fixture();p.communicate(timeout=3)
        for f in frames:f.close()
    report={'status':'PASS_FIXED_FIXTURE_EXECUTABLE_NOT_NATIVE_IOKIT_OR_ADMIN_ACCEPTANCE','checks':len(cases),'cases':cases,
        'fixture_process_count':len(processes),'all_fixture_processes_terminal':all(p.poll() is not None for p,f in processes),
        'native_IOKit_helper_or_admin_script_executed':False,'new_device_operations':0}
    with (HERE/'fixed-helper-tests.json').open('x') as f:json.dump(report,f,ensure_ascii=False,indent=2)
    (HERE/'helper-test-executed.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps({'fixed_helper_checks':len(cases),'fixture_processes':len(processes),'real_native_or_admin_executed':False}))


if __name__=='__main__':main()
