"""Capture saved reference driver/provider bytes and inspect source archive names."""
from pathlib import Path
from hashlib import sha256
from io import BytesIO
import importlib.util,json,os,sys,tarfile
from elftools.elf.elffile import ELFFile
H=Path(__file__).resolve().parent;B=H.parent;R=B.parents[1]
sys.path.insert(0,str(R/'outputs/fx3-recovery-adapter'))
from fx3_recovery.fat import FatP1
from fx3_recovery.squash import SquashFS
def save(label,name,raw):
    p=H/'originals'/label/name.lstrip('/');p.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    with os.fdopen(os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'wb') as f:f.write(raw)
    meta=None
    if raw[:4]==b'\x7fELF':
        e=ELFFile(BytesIO(raw));symbols=[]
        for n in ('.symtab','.dynsym'):
            sec=e.get_section_by_name(n)
            if sec:
                for s in sec.iter_symbols():
                    if s.name:symbols.append({'name':s.name,'type':s['st_info']['type'],'section':s['st_shndx'],'VA_or_section_offset':hex(s['st_value']),'bytes':s['st_size']})
        meta={'type':e['e_type'],'machine':e['e_machine'],'symbols':symbols,
              'sections':[{'name':s.name,'index':i,'address':hex(s['sh_addr']),'file_offset':s['sh_offset'],'bytes':s['sh_size']} for i,s in enumerate(e.iter_sections())]}
    return {'label':label,'path_in_fs':name,'output':str(p),'bytes':len(raw),'sha256':sha256(raw).hexdigest(),'ELF':meta}
rows=[]
for version,expected in [('2.04','e5b71cc24bf5232c2e182a979b60c5f080dcbabe2775b32214dc0f394cf53c67'),('2.05','ab2cd5372fed3c742b586e28484c6bf0aa6ebfba1f6d8e450a19191abc5b6591')]:
    p=R/f'work/fx3-color-port-20261027/input-20261028/original-update-engine/{version}/nflasha1'
    raw=p.read_bytes();assert sha256(raw).hexdigest()==expected
    fs=SquashFS(FatP1(raw).contents('/boot/initrd.img'));inventory=list(fs.walk())
    for name in ('/usr/kmod/sio.ko','/usr/lib/libul_GpioCtrl.so','/usr/bin/insmod.sh'):
        matches=[r for r in inventory if r['path']==name and r['type']=='file'];assert len(matches)==1
        rows.append(save('historical'+version+'-p1',name,fs.contents(matches[0])))

# Current main-AP library is separate evidence, not a substitute p1 driver.
helper=B/'stage2/extraction/read_filesystems.py'
assert sha256(helper.read_bytes()).hexdigest()=='eecbe9b099f9fbc8f8e06759c5e8a2ce9910e0f365ae9891fe0887353edc31ad'
sp=importlib.util.spec_from_file_location('saved_ext2_reader',helper);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
image=B/'stage2/extraction/nflasha15.img';assert sha256(image.read_bytes()).hexdigest()=='df0a2cf2ebb0d884605d041a6dcb701092bd36848956855b8d3d7a7164a3a1c5'
fs=m.Ext2(image);inv=list(fs.walk());selected=[r for r in inv if r['path']=='/lib/libul_GpioCtrl.so'];assert len(selected)==1
rows.append(save('official7.02-main-AP',selected[0]['path'],fs.data(selected[0]['inode'])))
fs.b.close();fs.f.close()

archive=B/'stage65-windows-cache-and-runtime-readiness/work/vendor-source-reference/range-resume-20261026/linux-kernel.complete.tar.gz'
expected='bb2d9cc676fef6aaf2f8f6703c4e041c133da0e7101b5afd33800eaf7c156d0f'
assert sha256(archive.read_bytes()).hexdigest()==expected
with tarfile.open(archive,'r:gz') as tf:
    names=[t.name for t in tf.getmembers() if ('sio' in t.name.lower() and ('/udif/' in t.name or '/mach-cxd' in t.name))]
result={'providers':rows,'current_main_AP_image':str(image),'current_main_AP_image_sha256':'df0a2cf2ebb0d884605d041a6dcb701092bd36848956855b8d3d7a7164a3a1c5',
 'current_main_AP_named_sio_ko':[r['path'] for r in inv if r['path'].endswith('/sio.ko')],
 'GPL_reference':{'path':str(archive),'sha256':expected,'label':'official FX3 7.00 source reference, not exact7.02 source/build proof',
   'selected_sio_filename_candidates':names,'scope':'filename filter only, no absence proof for equivalent/renamed driver code'},
 'current_body_p1_identity_verified':False,'source_or_guest_execution':False,'root_or_device_operations':0}
with (H/'provider-capture.json').open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({'captured':[{'label':r['label'],'path':r['path_in_fs'],'bytes':r['bytes'],'sha256':r['sha256']} for r in rows],
 'GPL_SIO_filename_candidates':names,'source_or_guest_execution':False}))
