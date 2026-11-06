"""Bounded acknowledged cleanup of the existing software-owned control page.
No original code writes from the host. The frozen guest unbind helper restores
its own API patch. Caller enters and returns with QEMU stopped.
"""
from pathlib import Path
import json,struct,time,hashlib
PHYS=0x41d400000
API=0xffffff80083220c8
ORIGINAL=bytes.fromhex('000b00b4fd7bbba9fd030091f35301a9')
CONTROL=0x100c1ea9

def restore_native_api(qmp,gate,run,timeout=20,poll=.25,clock=time.monotonic,sleep=time.sleep):
    if not 0<timeout<=30 or not 0<poll<=1:raise ValueError('bounded cleanup requires timeout<=30s and poll<=1s')
    run=Path(run);dest=run/'restore103-receipt.json';assert not dest.exists()
    start=clock();attempts=[];passed=False;reason='completion_timeout';resumed=False
    def sample():
        i=len(attempts);header=run/f'restore103-{i:03d}-header.bin';api=run/f'restore103-{i:03d}-api16.bin'
        assert not header.exists() and not api.exists()
        qmp('human-monitor-command',{'command-line':f'pmemsave {hex(PHYS)} 0x1000 "{header}"'})
        qmp('human-monitor-command',{'command-line':f'memsave {hex(API)} 0x10 "{api}"'})
        raw=header.read_bytes();words=struct.unpack_from('<8s8Q',raw);b=api.read_bytes()
        row={'attempt':i,'elapsed_seconds':clock()-start,'header':str(header),'api16':str(api),'api16_hex':b.hex(),'api16_original':b==ORIGINAL,'header_identity':words[0]==b'F100FILE','shutdown_control':words[6],'restore_status':words[7],'restore_seen':words[8],'header_SHA256':hashlib.sha256(raw).hexdigest()}
        attempts.append(row);return row
    try:
        before=sample()
        if not before['header_identity']:reason='observer_identity_missing'
        else:
            gate.shutdown_control() # One existing 8-byte software-owned request.
            qmp('cont');resumed=True
            while clock()-start<timeout:
                sleep(min(poll,max(0,timeout-(clock()-start))))
                qmp('stop');resumed=False;row=sample()
                if not row['header_identity']:reason='observer_identity_changed';break
                if row['restore_seen']:
                    if row['restore_status']!=0:reason='guest_shutdown_failed';break
                    if row['api16_original'] and row['shutdown_control']==CONTROL:
                        passed=True;reason='guest_acknowledged_and_original_bytes_verified';break
                    reason='guest_acknowledged_but_API_mismatch';break
                if clock()-start>=timeout:break
                qmp('cont');resumed=True
    except Exception as exc:
        reason='cleanup_exception';exception=repr(exc)
    else:exception=None
    finally:
        if resumed:
            try:qmp('stop');resumed=False
            except Exception as exc:passed=False;reason='final_stop_failed';exception=repr(exc)
    if attempts:
        final=run/'pcidma-original16-restored.bin';assert not final.exists();final.write_bytes(Path(attempts[-1]['api16']).read_bytes())
    result={'passed':passed,'reason':reason,'timeout_seconds':timeout,'elapsed_seconds':clock()-start,'request_bytes':8,'request_physical':hex(PHYS+48),'expected_API16_hex':ORIGINAL.hex(),'requires_both_guest_ack_and_actual_API_bytes':True,'original_guest_code_written_by_host':False,'guest_left_stopped':not resumed,'exception':exception,'attempts':attempts}
    dest.write_text(json.dumps(result,indent=2)+'\n');return result
