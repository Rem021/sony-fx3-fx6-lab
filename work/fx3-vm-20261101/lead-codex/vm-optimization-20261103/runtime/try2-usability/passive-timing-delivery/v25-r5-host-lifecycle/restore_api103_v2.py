"""Acknowledged restoration when bound; never resume an already-original VM.
No host writes to original code. Existing guest unbind helper performs restore.
"""
from pathlib import Path
import json,struct,time,hashlib
PHYS=0x41d400000;API=0xffffff80083220c8
ORIGINAL=bytes.fromhex('000b00b4fd7bbba9fd030091f35301a9');CONTROL=0x100c1ea9
def restore_native_api(qmp,gate,run,timeout=20,poll=.25,clock=time.monotonic,sleep=time.sleep):
    if not 0<timeout<=30 or not 0<poll<=1:raise ValueError('bounded cleanup parameters')
    run=Path(run);dest=run/'restore103-receipt.json';assert not dest.exists();start=clock();attempts=[];passed=False;reason='completion_timeout';resumed=False;issued=False;reused=False;exception=None
    def sample():
        i=len(attempts);h=run/f'restore103-{i:03d}-header.bin';a=run/f'restore103-{i:03d}-api16.bin';assert not h.exists()and not a.exists()
        qmp('human-monitor-command',{'command-line':f'pmemsave {hex(PHYS)} 0x1000 "{h}"'});qmp('human-monitor-command',{'command-line':f'memsave {hex(API)} 0x10 "{a}"'})
        raw=h.read_bytes();w=struct.unpack_from('<8s8Q',raw);b=a.read_bytes();r={'attempt':i,'elapsed_seconds':clock()-start,'header':str(h),'api16':str(a),'api16_hex':b.hex(),'api16_original':b==ORIGINAL,'header_identity':w[0]==b'F100FILE','shutdown_control':w[6],'restore_status':w[7],'restore_seen':w[8],'header_SHA256':hashlib.sha256(raw).hexdigest()};attempts.append(r);return r
    try:
        before=sample()
        if before['api16_original'] and before['shutdown_control']!=CONTROL:
            # No restoration request is outstanding, and all vCPUs are paused.
            # Do not run a not-yet-initialized backend just to obtain an ack.
            passed=True;reason='already_original_no_request_no_resume'
        elif not before['header_identity']:reason='observer_identity_missing'
        else:
            if before['shutdown_control']==CONTROL:reused=True
            else:gate.shutdown_control();issued=True
            resumed=True;qmp('cont')
            while clock()-start<timeout:
                sleep(min(poll,max(0,timeout-(clock()-start))));qmp('stop');resumed=False;row=sample()
                if not row['header_identity']:reason='observer_identity_changed';break
                if row['restore_seen']:
                    if row['restore_status']!=0:reason='guest_shutdown_failed';break
                    if row['api16_original']and row['shutdown_control']==CONTROL:passed=True;reason='guest_acknowledged_and_original_bytes_verified';break
                    reason='guest_acknowledged_but_API_mismatch';break
                if clock()-start>=timeout:break
                resumed=True;qmp('cont')
    except Exception as exc:reason='cleanup_exception';exception=repr(exc)
    finally:
        if resumed:
            try:qmp('stop');resumed=False
            except Exception as exc:passed=False;reason='final_stop_failed';exception=repr(exc)
    if attempts:
        p=run/'pcidma-original16-restored.bin';assert not p.exists();p.write_bytes(Path(attempts[-1]['api16']).read_bytes())
    result={'passed':passed,'reason':reason,'timeout_seconds':timeout,'elapsed_seconds':clock()-start,'request_bytes':8 if issued else 0,'request_issued':issued,'existing_request_reused':reused,'request_physical':hex(PHYS+48),'expected_API16_hex':ORIGINAL.hex(),'requires_ack_and_original_bytes_after_request':True,'already_original_without_pending_request_never_resumed':reason=='already_original_no_request_no_resume','original_guest_code_written_by_host':False,'guest_left_stopped':not resumed,'exception':exception,'attempts':attempts};dest.write_text(json.dumps(result,indent=2)+'\n');return result
