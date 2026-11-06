"""Bind helper startup/main pointers and saved script dependencies without running them."""
from pathlib import Path
from hashlib import sha256
from io import BytesIO
import json,struct
from elftools.elf.elffile import ELFFile
H=Path(__file__).resolve().parent
j=json.loads((H/'helper-disassembly.json').read_text());rows=[]
def sign(v,b):return v-(1<<b) if v&(1<<(b-1)) else v
for label,load_pc,expected in [('historical2.05-init',0x401118,0x400be0),('official7.02-firmup',0x401140,0x400c30)]:
    meta=next(r for r in j['helpers'] if r['label']==label);p=Path(meta['path']);d=p.read_bytes();e=ELFFile(BytesIO(d))
    assert sha256(d).hexdigest()==meta['sha256']
    def read(a,n):
        for s in e.iter_segments():
            if s['p_type']=='PT_LOAD' and s['p_vaddr']<=a and a+n<=s['p_vaddr']+s['p_filesz']:
                off=s['p_offset']+a-s['p_vaddr'];return d[off:off+n]
        raise AssertionError(hex(a))
    w=int.from_bytes(read(load_pc,4),'little');assert w&0xff00001f==0x58000000
    pool=load_pc+sign((w>>5)&0x7ffff,19)*4;main=int.from_bytes(read(pool,8),'little');assert main==expected
    call=next(r for r in meta['calls'] if r.get('import')=='__libc_start_main')
    pc=int(call['site'],16);word=int.from_bytes(read(pc,4),'little');assert word&0xfc000000==0x94000000
    target=pc+sign(word&0x3ffffff,26)*4
    assert meta['PLT'][hex(target)]['name']=='__libc_start_main'
    interp=next(s.get_interp_name() for s in e.iter_segments() if s['p_type']=='PT_INTERP')
    rows.append({'label':label,'source_sha256':meta['sha256'],'ELF_entry':meta['entry'],
      'raw_main_load':hex(load_pc),'raw_main_pointer_pool':hex(pool),'main':hex(main),
      'libc_start_main_PLT':hex(target),'interpreter':interp,
      'scope':'entry/main source linkage if Linux dynamic runtime starts process; not camera boot or call reachability from USB'})
init=H/'originals/historical2.05-p1/sbin/init';text=init.read_text()
assert text.index('insmod.sh')<text.index('us_darwin_init.sh')<text.index('UdtrMain.sh &')
assert 'PWR_IC_DARWIN=7' in text and 'if [ $PWR_IC -eq $PWR_IC_DARWIN ]' in text
drivers=H/'originals/historical2.05-p1/usr/bin/insmod.sh';ds=drivers.read_text()
assert 'insmod $MODPATH/sio.ko' in ds
config=H/'originals/official7.02-Ubody/config/config.xml';cx=config.read_text()
assert '<shell module="us_darwin_firm.sh" param="darwin" thread="yes"/>' in cx
wrapper=H/'originals/historical2.05-p1/usr/bin/us_darwin_firm.sh';wt=wrapper.read_text()
assert 'ud_darwin_firmup.elf $TARGET_DIR/darwin_boo.bin $TARGET_DIR/darwin_core.bin' in wt
result={'helper_startup_bindings':rows,'historical_AP_updater_boot_dependency':{
 'init_path':str(init),'init_sha256':sha256(init.read_bytes()).hexdigest(),
 'observed_order':['Linux mounts','insmod.sh','power-IC type check','conditional us_darwin_init.sh','UdtrMain.sh background'],
 'driver_loader_path':str(drivers),'driver_loader_sha256':sha256(drivers.read_bytes()).hexdigest(),
 'sio_module_load_present':True,'actual_current_p1_identity_verified':False},
 'official7_02_Darwin_stage':{'config_sha256':sha256(config.read_bytes()).hexdigest(),'wrapper':'us_darwin_firm.sh','thread':'yes',
 'historical_wrapper_sha256':sha256(wrapper.read_bytes()).hexdigest(),'current_body_wrapper_identity_verified':False},
 'no_bootstrap_from_dead_AP_proven':True,'original_or_guest_execution':False,'root_or_device_operations':0}
with (H/'entry-and-dependency-audit.json').open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({'startup_main_bindings':len(rows),'historical_SIO_load_before_updater_main':True,
 'no_camera_bootstrap_or_execution':True}))
