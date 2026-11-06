from pathlib import Path
import subprocess,os,json
r=Path(__file__).resolve().parent
fdt=next((r/'deps/dtc').rglob('libfdt.1.dylib')).resolve()
subprocess.run(['install_name_tool','-id',str(fdt),str(fdt)],check=True,capture_output=True)
subprocess.run(['codesign','--force','--sign','-',str(fdt)],check=True,capture_output=True)
env=os.environ.copy();env['PATH']=str(r/'build-venv/bin')+':'+env['PATH'];env['PKG_CONFIG_PATH']=str(r/'pkgconfig');env['PKG_CONFIG']=str(r/'deps/pkgconf/3.0.10/bin/pkgconf')
args=[str(r/'sources/qemu-11.1.2/configure'),'--target-list=aarch64-softmmu','--without-default-features','--enable-tcg','--enable-fdt','--disable-docs','--disable-tools','--disable-guest-agent','--disable-werror','--python='+str(r/'build-venv/bin/python')]
(r/'configure-02-command.json').write_text(json.dumps({'args':args,'PKG_CONFIG_PATH':env['PKG_CONFIG_PATH'],'PKG_CONFIG':env['PKG_CONFIG']},indent=2)+'\n')
with (r/'configure-02.log').open('w') as f:p=subprocess.run(args,cwd=r/'build',env=env,stdout=f,stderr=subprocess.STDOUT)
print('configure_rc',p.returncode)
print((r/'configure-02.log').read_text()[-4500:])
