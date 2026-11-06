#!/usr/bin/env python3
"""Verify original sources, bounded results and previous immutable checkpoint."""
import ast, hashlib, io, json, re, struct, sys
from pathlib import Path
from elftools.elf.elffile import ELFFile
HERE=Path(__file__).resolve().parent
TASK=HERE.parent
PIN='40181b37d8d89158e2eda8da7cb92c6bcddba29504c2472a17a3fd7aa33abbb4'
def digest(raw):return hashlib.sha256(raw).hexdigest()

def main():
    parent=TASK/'lens-state-20261029';receipt=parent/'final-receipt.json'
    assert digest(receipt.read_bytes())==PIN
    prior=json.loads(receipt.read_text())
    for row in prior['files']:
        raw=(parent/row['path']).read_bytes();assert len(raw)==row['bytes'] and digest(raw)==row['sha256']
    scripts=list(HERE.glob('*.py'))
    for script in scripts:ast.parse(script.read_text(),filename=str(script))
    assert len(scripts)==4
    data=json.loads((HERE/'service-inspection-results.json').read_text());source=data['source']
    raw=(HERE/source['output']).read_bytes();assert len(raw)==source['bytes'] and digest(raw)==source['sha256']
    elf=ELFFile(io.BytesIO(raw));assert elf['e_type']=='ET_REL' and elf['e_machine']=='EM_AARCH64'
    text=elf.get_section_by_name('.text').data();symbols=list(elf.get_section_by_name('.symtab').iter_symbols())
    for row in data['functions']+data['private_windows']:
        lo=int(row.get('offset',row.get('section_offset')),16)
        assert digest(text[lo:lo+row['bytes']])==row['sha256'] and (HERE/row['listing']).is_file()
    tables={(r['section'],r['offset']):r for r in data['table_relocations']}
    assert tables[('.rodata','0x9e8')]['addend']=='0x13cf8'
    assert tables[('.data','0x408')]['addend']=='0x1ba18'
    text_rel={r['r_offset']:r for r in elf.get_section_by_name('.rela.text').iter_relocations()}
    assert text_rel[0x14420]['r_addend']==0x13de8 and text_rel[0x13ee8]['r_addend']==0x9d0
    upm=json.loads((HERE/'upm-peer-results.json').read_text())
    assert upm['source_sha256']==source['sha256'] and len(upm['cases'])==4
    for row in upm['cases']:
        reply=bytes.fromhex(row['reply_hex']);assert len(reply)==156
        assert struct.unpack_from('<i',reply)[0]==row['status']
        if row['case']=='invalid_factor':assert row['status']==-1018 and 'factor7_power_copy' not in row['entries']
        else:assert row['status']==0 and row['entries']['factor7_power_copy']==1
    selected={int(r['address'],16):r for r in upm['selected_guest_relocations']}
    assert selected[0x110009e8]['target']=='0x10013cf8'
    assert selected[0x12000408]['target']=='0x1001ba18'
    enum=json.loads((HERE/'power-enum-results.json').read_text());assert len(enum['cases'])==3
    assert [r['original_printk_requests'][0]['enum_label'] for r in enum['cases']]==['PS_TYPE_ACV','PS_TYPE_BATTERY','PS_TYPE_UNKNOWN']
    assert [r['original_printk_requests'][1]['enum_label'] for r in enum['cases']]==['PS_AC_CONNECT_OK','PS_AC_CONNECT_NG','PS_AC_CONNECT_UNKNOWN']
    bridge=json.loads((HERE/'ap-upm-bridge-results.json').read_text());assert len(bridge['cases'])==4
    for row in bridge['ap_sources']:
        assert digest(Path(row['path']).read_bytes())==row['sha256']
    assert bridge['upm_sha256']==source['sha256']
    rows={r['case']:r for r in bridge['cases']}
    ac=rows['ac_connected'];assert ac['returned'] and ac['return_value']==0 and ac['boundary'] is None and ac['original_ap_power_flag']==1
    assert ac['original_ap_metadata_checks'][0]['result']=='0x1'
    writes=[r for r in ac['original_global_writes'] if r['address']=='0x400151f0']
    assert len(writes)==1 and writes[0]['bytes']==4 and writes[0]['value']==1 and writes[0]['pc']=='0x40002588'
    for name in ['battery','ac_jack_ng']:
        row=rows[name];assert not row['returned'] and row['return_value'] is None and row['boundary']['operation']=='before_native_Backup_read' and row['boundary']['item']=='0x920017'
        assert row['original_ap_power_flag']==0
    mismatch=rows['model_mismatch_before_power'];assert mismatch['returned'] and mismatch['return_value']==7 and mismatch['upm_execution'] is None and not mismatch['power_ram_bus']
    for name in ['ac_connected','battery','ac_jack_ng']:
        row=rows[name];assert row['upm_execution']['entries']['factor7_power_copy']==1
        assert [r['adapter'] for r in row['power_ram_bus']].count('RAM dynamic channel release')==1
        commands=[struct.unpack_from('<I',bytes.fromhex(r['request_hex']))[0] for r in row['cp_ram_bus'] if 'request_hex' in r]
        assert commands==[3,1,0]
    links=[]
    for link in re.findall(r'\]\(([^)]+)\)',(HERE/'README.md').read_text()):
        if link.startswith('https://') or link in ['final-receipt.json','validation-results.json']:continue
        assert (HERE/link).exists(),link;links.append(link)
    result=dict(previous_checkpoint_files_verified=len(prior['files']),previous_receipt_sha256=PIN,python_ast_files=len(scripts),
                original_kernel_sha256=source['sha256'],original_source_fragments=len(data['functions'])+len(data['private_windows']),
                original_module_table_and_thread_relocations_verified=True,original_power_enums_verified=True,
                case_counts=dict(upm_receiver=4,enum_diagnostic=3,three_guest_bridge=4,total=11),
                exact_original_ap_flag_write_verified=True,local_report_links_verified=len(links),
                boundary=dict(physical_power_state=False,real_ipc=False,kernel_init_or_load=False,native_target_execution=False,
                              fabricated_backup_bytes=False,firmware_output=False,device_actions=0,goal_complete=False,termination_condition_met=False),
                conclusion='Synthetic original-code prepare success is supported; real device admission, loader, complete donor colour chain and flashable modified firmware remain unproven.')
    (HERE/'validation-results.json').write_text(json.dumps(result,indent=2)+'\n')
    assert (HERE/'validation-results.json').is_file()
    print(json.dumps(result))

if __name__=='__main__':main()
