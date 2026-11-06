#!/usr/bin/env python3
"""Bounded local FX3 kernel/userland research VM. No camera/device access."""
from pathlib import Path
import argparse,datetime,fcntl,hashlib,json,os,plistlib,resource,signal,socket,subprocess,sys,time,uuid
ROOT=Path(__file__).resolve().parent

def digest(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    ap=argparse.ArgumentParser(description='FX3 原内核最小研究虚拟机（未实现相机菜单/成像）')
    ap.add_argument('--profile',choices=['minimal-linux','app-loader'],default='minimal-linux')
    ap.add_argument('--seconds',type=int,default=12)
    ap.add_argument('--self-check',action='store_true')
    ns=ap.parse_args()
    if not 1<=ns.seconds<=30:ap.error('--seconds 必须为 1..30')
    manifest=json.loads((ROOT/'manifest.json').read_text())
    vol=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
    if vol.get('VolumeUUID')!=manifest['volume_uuid']:raise RuntimeError('外盘身份不符或未挂载')
    kernel=Path(manifest['kernel']['path'])
    checks=[(ROOT/n,h) for n,h in manifest['runtime_sha256'].items()]+[(kernel,manifest['kernel']['sha256'])]
    for path,expected in checks:
        if not path.is_file() or path.is_symlink() or digest(path)!=expected:raise RuntimeError('源身份校验失败: '+str(path))
    if ns.self_check:
        print('PASS: 卷UUID、QEMU/dylib、实验DTB/CPIO与原FX3内核SHA全部一致。');return 0
    lock=(ROOT/'.run.lock').open('a+b')
    try:fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:raise RuntimeError('此入口已有运行，请等该次结束')
    run=Path(manifest['run_root'])/('a-'+uuid.uuid4().hex[:8]);run.mkdir()
    sock=run/'qmp.sock'
    if len(os.fsencode(sock))>=100:raise RuntimeError('任务Unix socket路径过长')
    profile=manifest['profiles'][ns.profile];qemu=ROOT/manifest['binary']
    dtb=ROOT/profile['dtb'];initrd=ROOT/profile['initrd']
    args=[str(qemu),'-machine','virt,gic-version=2,secure=off','-accel','tcg','-cpu','cortex-a35','-smp','1','-m',str(manifest['memory_mib']),'-display','none','-nodefaults','-nic','none','-no-reboot','-monitor','none','-serial','file:'+str(run/'serial.log'),'-qmp','unix:'+str(sock)+',server=on,wait=off','-d','in_asm','-D',str(run/'instruction.log'),'-S','-kernel',str(kernel),'-initrd',str(initrd),'-device','loader,file='+str(dtb)+',addr=0x400002000,force-raw=on']
    (run/'command.json').write_text(json.dumps({'args':args,'model_env':manifest['model_env'],'profile':ns.profile},indent=2)+'\n')
    env=os.environ.copy();env.update(manifest['model_env'])
    journal=[];samples=[];seq=0;error=None;p=None
    def limits():
        resource.setrlimit(resource.RLIMIT_FSIZE,(16*1024*1024,16*1024*1024))
        resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    start=time.monotonic();started=datetime.datetime.now(datetime.timezone.utc).isoformat()
    with (run/'host-stdout.log').open('wb') as stdout,(run/'host-stderr.log').open('wb') as stderr:
        try:
            p=subprocess.Popen(args,env=env,stdout=stdout,stderr=stderr,start_new_session=True,preexec_fn=limits)
            for _ in range(100):
                if sock.exists() or p.poll() is not None:break
                time.sleep(.05)
            if p.poll() is not None:raise RuntimeError('QEMU启动失败，见host-stderr.log')
            s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);s.settimeout(3);s.connect(str(sock));f=s.makefile('rb')
            journal.append({'greeting':json.loads(f.readline())})
            def qmp(cmd,arguments=None):
                nonlocal seq
                seq+=1;request={'execute':cmd,'id':seq}
                if arguments is not None:request['arguments']=arguments
                journal.append({'request':request});s.sendall((json.dumps(request)+'\n').encode())
                while True:
                    raw=f.readline()
                    if not raw:raise RuntimeError('QMP已结束')
                    response=json.loads(raw);journal.append({'response':response})
                    if response.get('id')==seq:return response
            qmp('qmp_capabilities');qmp('human-monitor-command',{'command-line':'info registers'});qmp('cont')
            deadline=time.monotonic()+ns.seconds
            while time.monotonic()<deadline and p.poll() is None:
                st=subprocess.run(['ps','-o','rss=,vsz=','-p',str(p.pid)],capture_output=True,text=True)
                samples.append({'elapsed_seconds':time.monotonic()-start,'rss_vsz_kib':st.stdout.strip()});time.sleep(.25)
            if p.poll() is None:
                qmp('stop')
                for command in ['gva2gpa 0xffffff80086e7538','gva2gpa 0xfffffffff13a1c38','x /2gx 0xffffff80086994d8','x /4gx 0xffffff80086e47a0','memsave 0xffffff80086994d8 0x10 "'+str(run/'printk-pointers.bin')+'"','memsave 0xffffff80086e47a0 0x20 "'+str(run/'printk-indices.bin')+'"','memsave 0xffffff80086e7538 0x20000 "'+str(run/'printk-ring.bin')+'"','info registers']:
                    qmp('human-monitor-command',{'command-line':command})
                qmp('query-status');qmp('query-cpus-fast');qmp('quit')
            p.wait(timeout=5)
        except (Exception,KeyboardInterrupt) as e:error=repr(e)
        finally:
            if p is not None and p.poll() is None:
                os.killpg(p.pid,signal.SIGTERM)
                try:p.wait(timeout=3)
                except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=3)
    (run/'qmp.json').write_text(json.dumps(journal,indent=2)+'\n')
    serial=(run/'serial.log').read_text(errors='replace') if (run/'serial.log').exists() else ''
    found={m:m in serial for m in profile['required_markers']}
    exceptions=[m for m in ['Kernel panic','Entering exception monitor.','Unhandled fault:'] if m in serial]
    unchanged=all(digest(path)==h for path,h in checks)
    passed=all(found.values()) and not exceptions and error is None and unchanged and p is not None and p.returncode==0
    status=('ORIGINAL_USERLAND_REACHED' if ns.profile=='minimal-linux' else 'ORIGINAL_APP_LOADER_VERIFY_LIST_PASSED') if passed else 'INCOMPLETE_OR_BLOCKED'
    receipt={'created_utc':started,'duration_seconds':time.monotonic()-start,'status':status,'scope':profile['scope'],'profile':ns.profile,'manifest_sha256':digest(ROOT/'manifest.json'),'inputs_unchanged':unchanged,'required_markers':found,'guest_exception_markers':exceptions,'qemu_exit':None if p is None else p.returncode,'host_observer_error':error,'memory_samples':samples,'run':str(run),'source_kernel_sha256':manifest['kernel']['sha256'],'qemu_runtime_sha256':digest(qemu),'physical_devices_disks_network_or_firmware_writes':0,'menu_or_capture_verified':False,'process_reaped':p is not None and p.poll() is not None}
    (run/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    print('状态:',status);print('日志:',run)
    print('\n'.join(serial.splitlines()[-18:]))
    return 0 if passed else 2

if __name__=='__main__':
    try:sys.exit(main())
    except Exception as exc:print('停止:',exc,file=sys.stderr);sys.exit(2)
