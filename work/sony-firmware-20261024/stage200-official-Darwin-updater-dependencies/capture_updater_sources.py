"""Read only saved vendor containers; copy selected bytes, never run them."""
from pathlib import Path
from hashlib import sha256
from io import BytesIO
import json,os,sys
from elftools.elf.elffile import ELFFile
H=Path(__file__).resolve().parent;B=H.parent;R=B.parents[1]
sys.path.insert(0,str(R/'outputs/fx3-recovery-adapter'))
from fx3_recovery.squash import SquashFS
from fx3_recovery.fat import FatP1
PARSERS=[R/'outputs/fx3-recovery-adapter/fx3_recovery'/n for n in ('squash.py','fat.py')]
def digest(p):return sha256(p.read_bytes()).hexdigest()
def put(n,v):
    with (H/n).open('x') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
def save(label,name,raw):
    parts=Path(name.lstrip('/')).parts
    assert parts and all(x not in ('.','..') for x in parts)
    p=H/'originals'/label/Path(*parts);p.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    with os.fdopen(os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'wb') as f:f.write(raw)
    return p
def elfmeta(raw):
    if raw[:4]!=b'\x7fELF':return None
    e=ELFFile(BytesIO(raw));symbols=[];needed=[]
    for n in ('.symtab','.dynsym'):
        sec=e.get_section_by_name(n)
        if sec:
            for s in sec.iter_symbols():
                if s.name:symbols.append({'table':n,'name':s.name,'type':s['st_info']['type'],
                    'bind':s['st_info']['bind'],'section':s['st_shndx'],'VA':hex(s['st_value']),'size':s['st_size']})
    dyn=e.get_section_by_name('.dynamic')
    if dyn:
        for t in dyn.iter_tags():
            if t.entry.d_tag=='DT_NEEDED':needed.append(t.needed)
    return {'machine':e['e_machine'],'ELF_type':e['e_type'],'entry':hex(e['e_entry']),
            'needed':needed,'symbols':symbols,'all_symbols_are_static_metadata_not_execution':True}

sources=[];captures=[];inventories=[]
inputs=[('official7.02-Ubody',B/'stage182-boot-selector-and-recovery-admission/current-updater-evidence/original-members/udtrbody.squashfs',
         '62e86fad175e0326969d5f1cea29d780feb496ce8034acd2c9c3954320d8ccaa'),
        ('historical2.04-p1',R/'work/fx3-color-port-20261027/input-20261028/original-update-engine/2.04/nflasha1',
         'e5b71cc24bf5232c2e182a979b60c5f080dcbabe2775b32214dc0f394cf53c67'),
        ('historical2.05-p1',R/'work/fx3-color-port-20261027/input-20261028/original-update-engine/2.05/nflasha1',
         'ab2cd5372fed3c742b586e28484c6bf0aa6ebfba1f6d8e450a19191abc5b6591')]
for label,p,expected in inputs:
    raw=p.read_bytes();assert sha256(raw).hexdigest()==expected
    is_p1=label.startswith('historical')
    fsraw=FatP1(raw).contents('/boot/initrd.img') if is_p1 else raw
    fs=SquashFS(fsraw);rows=list(fs.walk());inventory=[]
    sources.append({'label':label,'path':str(p),'bytes':len(raw),'sha256':expected,
        'initrd_sha256':sha256(fsraw).hexdigest() if is_p1 else None,
        'current_body_identity_attested':False,'historical_reference_only':is_p1,'entries':len(rows)})
    for row in rows:
        info={'path':row['path'],'type':row['type'],'size':row.get('size')}
        if row['type']=='file':
            value=fs.contents(row);info['sha256']=sha256(value).hexdigest()
            matched=b'darwin' in value.lower() or 'darwin' in row['path'].lower()
            info['Darwin_literal_or_name_match']=matched
            if matched:
                out=save(label,row['path'],value)
                meta=elfmeta(value)
                captures.append({'source_label':label,'path_in_fs':row['path'],'output':str(out),
                    'bytes':len(value),'sha256':info['sha256'],'ELF':meta})
        inventory.append(info)
    inventories.append({'source_label':label,'files':inventory})
    assert digest(p)==expected
put('source-capture.json',{'sources':sources,'captures':captures,
    'parser_sources':[{'path':str(p),'sha256':digest(p)} for p in PARSERS],
    'scope':'saved filesystem bytes and ELF metadata; Darwin matches are locators, not reachability/dependency proofs',
    'current_body_p1_read':False,'original_or_guest_execution':False,'root_or_device_operations':0})
put('filesystem-inventories.json',inventories)
print(json.dumps({'captures':len(captures),'selected':[{'label':e['source_label'],'path':e['path_in_fs'],
 'bytes':e['bytes'],'needed':e['ELF']['needed'] if e['ELF'] else None} for e in captures],
 'original_or_guest_execution':False}))
