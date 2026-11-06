#!/usr/bin/env python3
"""Read FX3 original bytes and emit bounded boot/load binding evidence."""
import hashlib
import json
from pathlib import Path
import re

BASE = Path('/Volumes/KAFU2T/AI/Projects/Mac/work')
FX = BASE/'fx3-vm-20261101/fx3-audit/original-members'
SRC = BASE/'sony-firmware-20261024'

def digest(data): return hashlib.sha256(data).hexdigest()
def source(path, expected):
    data=path.read_bytes(); actual=digest(data)
    if actual!=expected: raise RuntimeError(f'original hash mismatch: {path}: {actual}')
    return data

init2_path=FX/'nflasha7/sbin/init2'
fstab_path=FX/'nflasha7/sbin/initrc/fstab'
bootin_path=FX/'nflasha15/bin/bootin.elf'
im_path=FX/'nflasha15/bin/im.elf'
ap_path=FX/'nflasha15/lib/appFw.so'
cp_path=SRC/'stage2/extraction/files/nflasha8/cpapp-b.bin'
spi_path=SRC/'stage198-AP-CP-loaders-and-partition-selection/originals/loader_spi.bin'
config_path=BASE/'fx3-color-port-20261027/config-producer-20261029/original-files/pformat_config.txt'
hashes={'init2':'45d3b907e6ef96c9a930cd3e6f919db700bffb5f18c386abfdb655f4d9954aeb',
        'fstab':'3936e6508ba89a025fc998c824434562c2d16234db96e179ec3f3a90a5a1d6f0',
        'bootin':'dab3ce4b6c28a6c9ffd9f0b893dce1d08f3ee7302a09df87e518409e728be2f2',
        'im':'5171f576d8b76cfbf15581389183b390c445bd6ff9dd97fd6668c5f64e77dc91',
        'ap':'545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f',
        'cp':'c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba',
        'spi':'314d372d0d2b9883c3b9dc04b40389edb3100e6d5ef529633cc427c3d0cab72e'}
paths={'init2':init2_path,'fstab':fstab_path,'bootin':bootin_path,'im':im_path,
       'ap':ap_path,'cp':cp_path,'spi':spi_path}
blobs={k:source(p,hashes[k]) for k,p in paths.items()}
init_lines=blobs['init2'].decode('ascii').splitlines()
boot_script=[{'line':i+1,'text':v} for i,v in enumerate(init_lines)
             if 'mount -a -T $FSTAB' in v or '/usr/bin/bootin.elf &' in v or 'if [ "$MODE" != "0" ]' in v]
assert len(boot_script)==4
fstab=blobs['fstab'].decode('ascii')
assert '/dev/nflasha15\t/usr\text2\tro,' in fstab and '/dev/nflasha8\t/cp\tvfat\trw,' in fstab
bootin_im=[i for i in range(len(blobs['bootin'])) if blobs['bootin'].startswith(b'/usr/bin/im.elf',i)]
assert len(bootin_im)==2
config=source(config_path,'21cd5b29dd165c322f5b00bb057802c377ff94af15f95881e150a32130302ece').decode('ascii')
match=re.search(r'file_param\s*\{[^}]*path\s*=\s*"cpapp-b.bin"[^}]*load\s*=\s*(0x[0-9A-Fa-f]+)',config,re.S)
assert match and int(match.group(1),16)==0x108000
spi=blobs['spi']
words={hex(i):spi[i:i+4].hex() for i in (0x5aac,0x5ab0,0x5ab4,0x41bc,0x3ca8,0x3cd8)}
assert words['0x5aac']=='00009052' and words['0x5ab0']=='0002a072' and words['0x3cd8']=='e0039fd6'
proof=json.loads((SRC/'stage198-AP-CP-loaders-and-partition-selection/fixed-handoff-proof.json').read_text())
assert proof['source_sha256']==hashes['spi'] and proof['fixed_handoff_target']=='0x108000'
asset=json.loads((BASE/'fx3-vm-20261101/fx3-audit/asset-audit.json').read_text())
members={x['path']:x for x in asset['files']}
assert members['/lib/appFw.so']['sha256']==hashes['ap'] and members['/lib/appFw.so']['partition']==15
result={'schema':'fx3-original-loader-binding-v1','level':'static original bytes plus prior bounded proof',
        'sources':{k:{'path':str(paths[k]),'bytes':len(blobs[k]),'sha256':hashes[k]} for k in paths},
        'ap_boot_chain':{'init2_calls':boot_script,'bootin_im_path_offsets':[hex(x) for x in bootin_im],
                         'mounted_usr':'nflasha15 ext2 ro','ap_projection':{'partition':15,
                         'path':'/lib/appFw.so','inode':members['/lib/appFw.so']['original_inode'],
                         'sha256':hashes['ap']},'im_elf_sha256':hashes['im'],
                         'appFw_reader':'not bound by these original init/bootin/im bytes'},
        'cp_chain':{'partition':8,'filesystem':'vfat','path':'/cpapp-b.bin',
                    'config_path':str(config_path),'config_sha256':'21cd5b29dd165c322f5b00bb057802c377ff94af15f95881e150a32130302ece',
                    'config_load':match.group(1),
                    'spi_words_at_file_offsets':words,'prior_static_handoff_target':proof['fixed_handoff_target'],
                    'reader':'loader_spi handoff target consistent with cpapp config; exact file reader not bound'},
        'unknown':['current camera boot path/version selection','appFw.so actual dlopen/loader caller and in-memory identity',
                   'cpapp-b.bin exact reader and active slot','WBI image selection and cold-start behavior',
                   'any installed bytes or executable patch window'], 'install_ready':False}
print(json.dumps(result,ensure_ascii=False,indent=2))
