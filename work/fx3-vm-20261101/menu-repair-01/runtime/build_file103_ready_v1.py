from pathlib import Path
import subprocess,json,hashlib,os
R=Path(__file__).resolve().parent;H=R/"helpers"
a=['/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/runtime/toolchains/zig-aarch64-macos-0.17.0/zig', 'cc', '-target', 'aarch64-linux-gnu.2.25', '-O2', '/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/runtime/helpers/fx3-file100-observer-v2.c', '-o', '/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/runtime/helpers/fx3-file100-observer-v2']
q=subprocess.run(a,capture_output=True,text=True);(H/"fx3-file100-observer-v2-build.log").write_text(q.stdout+q.stderr);assert q.returncode==0,q.stderr
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(H/"fx3-file100-observer-v2-build.json").write_text(json.dumps({"args":a,"exit":q.returncode,"source_sha256":sha(H/"fx3-file100-observer-v2.c"),"output_sha256":sha(H/"fx3-file100-observer-v2"),"change":"Read-only observer same data/control ABI, ready PID marker after header initialization", "authority":"msg_45f1419f7e5e"},indent=2)+"\n");print("FILE103_READY_OBSERVER_BUILT")
