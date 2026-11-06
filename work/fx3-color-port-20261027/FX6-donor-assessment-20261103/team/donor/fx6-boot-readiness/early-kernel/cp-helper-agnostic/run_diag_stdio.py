#!/usr/bin/env python3
"""One diagnostic VM with -serial stdio: read guest serial and query the exception monitor."""
import argparse, json, os, plistlib, socket, subprocess, sys, threading, time, uuid, hashlib, fcntl, signal
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import fixed_runner as fr

MANIFEST = HERE / 'vm-candidate-diag.json'
SHA_FILE = HERE / 'VM-CANDIDATE-DIAG-SHA256.txt'


def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(4*1024*1024), b''):
            h.update(b)
    return h.hexdigest()


def check():
    vol = plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
    if vol.get('VolumeUUID') != fr.UUID: raise RuntimeError('wrong volume')
    if sha(MANIFEST) != SHA_FILE.read_text().strip(): raise RuntimeError('manifest changed')
    s = json.loads(MANIFEST.read_text())
    if s.get('status') != 'APPROVED_TENTH_DIAG_PENDING_RUN': raise RuntimeError('status')
    for key in ('kernel','initrd','dtb','backup'):
        if sha(s[key]['path']) != s[key]['sha256']: raise RuntimeError(key + ' hash')
    if s['candidate_argv_before_observer_serial_retarget'][s['candidate_argv_before_observer_serial_retarget'].index('-kernel')+1] != s['kernel']['path']:
        raise RuntimeError('kernel argv')
    return s


def run(s, seconds):
    held = fr.acquire(); run_dir = HERE / 'runs' / ('diagstd-' + uuid.uuid4().hex[:8]); run_dir.mkdir(parents=True, mode=0o700)
    args = s['candidate_argv_before_observer_serial_retarget'].copy(); idx = args.index('-serial'); args[idx+1] = 'stdio'
    qemu = None; qmp = None; reader = None; stop = threading.Event(); exception = threading.Event()
    serial_commands = []; serial_bytes = bytearray(); reason = 'not_started'; error = None
    try:
        (run_dir/'command.json').write_text(json.dumps({'argv':args,'manifest_sha256':sha(MANIFEST),'scope':s['scope'],'serial':'stdio'},indent=2)+'\n')
        with (run_dir/'host-stderr.log').open('wb') as err:
            qemu = subprocess.Popen(args, cwd=run_dir, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=err, start_new_session=True, preexec_fn=fr.limits)
            deadline = time.monotonic() + seconds
            while not (run_dir/'q').exists() and qemu.poll() is None and time.monotonic() < deadline:
                time.sleep(0.05)
            if qemu.poll() is not None: raise RuntimeError('QEMU exited before QMP')
            qmp = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM); qmp.settimeout(3)
            fr.connect_relative(qmp, run_dir)
            qreader = qmp.makefile('rb'); json.loads(qreader.readline())
            fr.qmp_send(qmp, qreader, 'qmp_capabilities', 1)
            log = (run_dir/'serial.log').open('wb')
            def read_serial():
                buf = b''
                try:
                    while not stop.is_set() and qemu.stdout is not None:
                        chunk = qemu.stdout.read(65536)
                        if not chunk: break
                        buf += chunk; serial_bytes.extend(chunk); log.write(chunk); log.flush()
                        if b'Exception>' in buf or b'Entering exception monitor' in buf: exception.set()
                        if len(buf) > 65536: buf = buf[-65536:]
                finally: log.close()
            reader = threading.Thread(target=read_serial, daemon=True); reader.start()
            fr.qmp_send(qmp, qreader, 'cont', 2)
            if exception.wait(max(1, seconds - 1)):
                reason = 'exception_monitor_seen'; time.sleep(1.0)
                for cmd in (b'help\r\n', b'bt\r\n', b'regs\r\n', b'info\r\n', b'stack\r\n', b'task\r\n'):
                    serial_commands.append(cmd.decode(errors='replace').strip())
                    try:
                        qemu.stdin.write(cmd); qemu.stdin.flush()
                    except Exception:
                        break
                    time.sleep(1.0)
                time.sleep(2.0)
            else: reason = 'no_exception_timeout'
    except BaseException as exc:
        error = repr(exc); reason = 'error'
    finally:
        stop.set()
        if qmp is not None:
            try: fr.qmp_send(qmp, qreader, 'quit', 9)
            except Exception: pass
            qmp.close()
        if qemu is not None:
            try: qemu.wait(timeout=5)
            except subprocess.TimeoutExpired:
                if qemu.poll() is None: os.killpg(qemu.pid, signal.SIGTERM)
                try: qemu.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    if qemu.poll() is None: os.killpg(qemu.pid, signal.SIGKILL)
                    qemu.wait(timeout=3)
        if reader is not None: reader.join(timeout=2)
        for stream in reversed(held):
            fcntl.flock(stream, fcntl.LOCK_UN); stream.close()
    receipt = {'schema':'fx6-hybrid-fx3kernel-diag-stdio-run-v1','utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'reason':reason,'error':error,
               'exception_monitor_seen':exception.is_set(),'serial_commands':serial_commands,'serial_bytes':len(serial_bytes),
               'serial_sha256':hashlib.sha256(serial_bytes).hexdigest(),'qemu_pid':None if qemu is None else qemu.pid,
               'qemu_exit':None if qemu is None else qemu.returncode,'process_reaped':qemu is None or qemu.poll() is not None,
               'locks_released':True,'manifest_sha256':sha(MANIFEST),'one_VM_one_Start':True,'deployment':False}
    (run_dir/'diag-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    return receipt


def main():
    ap = argparse.ArgumentParser(); g = ap.add_mutually_exclusive_group(required=True); g.add_argument('--check',action='store_true'); g.add_argument('--run',action='store_true')
    ap.add_argument('--seconds',type=int,default=60); ns = ap.parse_args()
    if not 1 <= ns.seconds <= 180: ap.error('seconds')
    s = check()
    if ns.check: print(json.dumps({'status':'PASS_DIAG_STDIO_CANDIDATE','manifest_sha256':sha(MANIFEST),'runtime_started':False},indent=2))
    else: print(json.dumps(run(s,ns.seconds),ensure_ascii=False,indent=2))

if __name__ == '__main__': main()
