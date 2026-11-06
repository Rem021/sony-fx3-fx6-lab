from pathlib import Path
import subprocess,json,os,hashlib
R=Path(__file__).resolve().parent;H=R/'helpers';args=json.loads((R/'display86-v2-build-args.json').read_text());p=subprocess.run(args,env=dict(os.environ,ZIG_GLOBAL_CACHE_DIR=str(R/'toolchains/zig-cache'),ZIG_LOCAL_CACHE_DIR=str(R/'toolchains/zig-local-cache')),text=True,capture_output=True);assert not p.returncode,p.stderr
(H/'fx3-display-observe-v2-build.json').write_text(json.dumps({'args':args,'exit':0,'source_sha256':hashlib.sha256((H/'fx3-display-observe-v2.c').read_bytes()).hexdigest(),'asm_sha256':hashlib.sha256((H/'fx3-display-probes-v1.S').read_bytes()).hexdigest(),'output_sha256':hashlib.sha256((H/'fx3-display-observe-v2.so').read_bytes()).hexdigest()},indent=2)+'\n');print('DISPLAY_V1_BUILD_PASS')
