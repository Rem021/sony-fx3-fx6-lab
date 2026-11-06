"""Read saved FX3 p1 references; never run the extracted programs/modules."""
from pathlib import Path
from hashlib import sha256
from io import BytesIO
import sys, json, os
from elftools.elf.elffile import ELFFile
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN

H=Path(__file__).resolve().parent; B=H.parent; R=B.parents[1]
sys.path.insert(0,str(R/'outputs/fx3-recovery-adapter'))
from fx3_recovery.fat import FatP1
from fx3_recovery.squash import SquashFS
captures=[]; sources=[]
for version, expected in [('2.04','e5b71cc24bf5232c2e182a979b60c5f080dcbabe2775b32214dc0f394cf53c67'),('2.05','ab2cd5372fed3c742b586e28484c6bf0aa6ebfba1f6d8e450a19191abc5b6591')]:
    p=R/f'work/fx3-color-port-20261027/input-20261028/original-update-engine/{version}/nflasha1'
    raw=p.read_bytes(); assert sha256(raw).hexdigest()==expected
    sources.append(dict(path=str(p),bytes=len(raw),sha256=expected,label='historical'+version+'-p1'))
    fs=SquashFS(FatP1(raw).contents('/boot/initrd.img')); inv=list(fs.walk())
    for name in ['/usr/kmod/osal_uipc.ko','/usr/lib/libosal_uipc.so','/usr/kmod/pciedma.ko','/usr/kmod/pci_ep_cp.ko','/usr/kmod/pcie-if.ko','/usr/bin/ud_send_lsi.elf']:
        row=[r for r in inv if r['path']==name and r['type']=='file']; assert len(row)==1
        data=fs.contents(row[0]); out=H/'originals'/version/name.lstrip('/'); out.parent.mkdir(parents=True,exist_ok=True)
        with os.fdopen(os.open(out,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'wb') as f: f.write(data)
        e=ELFFile(BytesIO(data)); sy=e.get_section_by_name('.symtab') or e.get_section_by_name('.dynsym')
        captures.append(dict(version=version,path_in_fs=name,output=str(out),bytes=len(data),sha256=sha256(data).hexdigest(),
            symbols=[dict(name=s.name,offset=hex(s['st_value']),bytes=s['st_size'],section=s['st_shndx'],type=s['st_info']['type']) for s in sy.iter_symbols() if s.name]))
with (H/'reference-providers.json').open('x') as f: json.dump(dict(sources=sources,captures=captures,current_body_p1_identity_verified=False,original_or_guest_execution=False,root_or_device_operations=0),f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps([dict(version=c['version'],file=c['path_in_fs'],bytes=c['bytes'],sha256=c['sha256']) for c in captures]))
