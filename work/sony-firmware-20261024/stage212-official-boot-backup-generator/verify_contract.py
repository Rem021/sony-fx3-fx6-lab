"""Rebind saved evidence to original files, no target code execution."""
from pathlib import Path
from hashlib import sha256
import importlib.util,io,json,sys,types,struct
from elftools.elf.elffile import ELFFile

H=Path(__file__).resolve().parent; B=H.parent; R=H.parents[2]
prev=B/'stage211-NOR-runtime-map-and-SIO-initialization'
assert sha256((prev/'final-receipt.json').read_bytes()).hexdigest()=='62070d9c8d226a08bc467e463d4faefdcd1aa858f7f3b9867077342e20e6eac8'
manifest=json.loads((prev/'final-receipt.json').read_text())
for r in manifest['files']:
    raw=(R/r['path']).read_bytes()
    assert len(raw)==r['bytes'] and sha256(raw).hexdigest()==r['sha256']
assert (H/'goal-status-before.json').read_bytes()==(prev/'goal-status-after.json').read_bytes()
tool=R/'outputs/fx3-recovery-adapter'
assert sha256((tool/'releases/fx3-recovery-adapter-0.4.0.zip').read_bytes()).hexdigest()=='43343ddd7f516886f9d4ad354937f900710288dfd854c4d20b47ec7f915c636f'
sys.path.insert(0,str(tool))
from fx3_recovery.squash import SquashFS
capture=json.loads((H/'source-capture.json').read_text())
raw=(R/capture['source_image']).read_bytes()
assert sha256(raw).hexdigest()==capture['source_image_sha256']
sq=SquashFS(raw); entries={e['path']:e for e in sq.walk() if e['type']=='file'}
for r in capture['files']:
    data=sq.contents(entries[r['path_in_image']])
    assert data==(R/r['output']).read_bytes() and len(data)==r['bytes'] and sha256(data).hexdigest()==r['sha256']
proof=json.loads((H/'official-boot-writer-proof.json').read_text())
for r in proof['ranges']:
    src=R/r['source']; data=src.read_bytes()
    assert sha256(data).hexdigest()==r['source_sha256']
    off=r['file_offset']; piece=data[off:off+r['bytes']]
    assert piece==(R/r['raw']).read_bytes() and sha256(piece).hexdigest()==r['sha256']
    with src.open('rb') as f:
        e=ELFFile(f);lo=int(r['VA_start'],16);hi=int(r['VA_end_exclusive'],16)
        seg=next(p for p in e.iter_segments() if p['p_type']=='PT_LOAD' and p['p_vaddr']<=lo and hi<=p['p_vaddr']+p['p_filesz'])
        assert off==seg['p_offset']+lo-seg['p_vaddr']
for r in proof['script_lines']:
    assert (R/r['source']).read_text().splitlines()[r['line']-1]==r['text']

# Independent raw instruction-word checks for the critical lost-return claim.
with (H/'originals/bin/pformat.elf').open('rb') as f:
    e=ELFFile(f); segments=list(e.iter_segments())
    def word(va):
        p=next(p for p in segments if p['p_type']=='PT_LOAD' and p['p_vaddr']<=va and va+4<=p['p_vaddr']+p['p_filesz'])
        f.seek(p['p_offset']+va-p['p_vaddr']);return int.from_bytes(f.read(4),'little')
    def branch_target(pc):
        w=word(pc);n=w&0x3ffffff;n=n-(1<<26) if n&(1<<25) else n
        return w>>26,pc+4*n
    assert word(0x4093d0)==0x52800013  # mov w19,#0
    assert branch_target(0x4093d4)==(0b100101,0x409d2c)  # BL writer
    assert branch_target(0x4093d8)==(0b000101,0x4090dc)  # B return tail
    assert word(0x4090dc)==0x2a1303e0  # mov w0,w19
    assert word(0x4090f8)==0xd65f03c0  # ret

layout=json.loads((H/'default-BKSB-layout-comparison.json').read_text())
assert layout['record_count']==22 and layout['property_checks']==1386
ap=[r for r in layout['layouts'] if r['record_index']==0]
cp=[r for r in layout['layouts'] if r['record_index']==1]
missing=['0x5d000b','0x5d000c','0x5d0011','0x5d0012']
assert all(r['missing_ids']==missing and r['predicted_BKSB_bytes'] is None for r in ap)
assert all(r['all65_present'] and r['predicted_BKSB_bytes']==1088 and r['fits_CP_config_2048_bytes'] for r in cp)

# The independent PMCA parser must also reject all44 absent AP properties.
ref=B/'stage207-Backup-template-and-GPIO-config'
cap=json.loads((ref/'format-source-capture.json').read_text())
for r in cap['files']:assert sha256((R/r['output']).read_bytes()).hexdigest()==r['sha256']
pkgname='fx3_bksb_absence212';root=ref/'reference/pmca/pmca'
pkg=types.ModuleType(pkgname);pkg.__path__=[str(root)];sys.modules[pkgname]=pkg
sp=importlib.util.spec_from_file_location(pkgname+'.backup',root/'backup/__init__.py',submodule_search_locations=[str(root/'backup')])
mod=importlib.util.module_from_spec(sp);sys.modules[pkgname+'.backup']=mod;sp.loader.exec_module(mod)
negative=[]
for row in ap:
    src=R/'work/sony-firmware-20261024/stage207-Backup-template-and-GPIO-config/originals/ALCIN'/Path(row['template']).name
    raw=src.read_bytes();assert sha256(raw).hexdigest()==row['source_sha256']
    start,size=struct.unpack_from('<II',raw,0x18)
    view=io.BufferedReader(io.BytesIO(raw[:start+size]));assert not view.writable()
    bk=mod.BackupFile(view)
    for ident in missing:
        try:bk.getProperty(int(ident,16))
        except Exception as ex:
            assert str(ex) in ['Invalid property','Invalid property id']
            negative.append(dict(template=Path(row['template']).name,id=ident,independent_rejection=str(ex)))
        else:raise AssertionError('Independent parser unexpectedly accepted missing AP property')
    view.close()
assert len(negative)==44

audit_path=B/'stage182-boot-selector-and-recovery-admission/current-updater-evidence/current-updater-asset-audit.json'
audit=json.loads(audit_path.read_text()); names=[x['name'] if 'name' in x else x['path'] for x in audit['tar']['members']]
assert len(names)==155 and not any('loader_emmc.tar' in n for n in names)
assert len(audit['nor_loader_members'])==4
assert (H/'goal-status-before.json').read_bytes()==(B/'GOAL_STATUS.json').read_bytes()
assert len(json.loads((B/'GOAL_STATUS.json').read_text())['requirements'])==16
out=dict(status='PASS_STATIC_REBIND_AND_HOST_ONLY_PARSER_COMPARISONS',
    previous_seal_sha256='62070d9c8d226a08bc467e463d4faefdcd1aa858f7f3b9867077342e20e6eac8',
    previous_members_reverified=len(manifest['files']),source_image_sha256=capture['source_image_sha256'],
    reextracted_files=len(capture['files']),original_ranges=len(proof['ranges']),script_line_pins=len(proof['script_lines']),
    independent_raw_instruction_checks=5,default_records=22,independent_present_property_matches=1386,
    independent_absent_property_rejections=44,absence_results=negative,
    current_package_top_tar_members=155,loader_emmc_archive_in_reviewed_top_level_archive=False,
    current_package_inventory_sha256=sha256(audit_path.read_bytes()).hexdigest(),
    release04_unchanged=True,canonical_requirements=16,
    actual_camera_backup_restore_or_MAIN_recording_acceptance=False,
    Sony_code_or_guest_execution=False,root_or_device_operations=0,persistent_write_release=False)
(H/'verification-receipt.json').open('x').write(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k!='absence_results'}))
