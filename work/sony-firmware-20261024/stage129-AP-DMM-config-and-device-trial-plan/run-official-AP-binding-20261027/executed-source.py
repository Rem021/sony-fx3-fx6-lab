#!/usr/bin/env python3
"""Offline-only exact-package AP config gate and original MPR unit bindings."""
from pathlib import Path
import argparse,datetime,hashlib,json,os,stat,sys
STAGE=Path(__file__).resolve().parent;BASE=STAGE.parent;ROOT=BASE.parents[1]
sys.path.insert(0,str(BASE/'stage128-DMM-provider-and-config'));import provider_audit as p
import prepare_inputs as local_prep
AP=STAGE/'inputs/AP-DmmCfg.bin';CP=BASE/'stage128-DMM-provider-and-config/inputs/DmmCfg.bin'
AP_SHA='48c90ca08ae8174d376bf8cbb454a5544e3d024c317e5136fb31d4fb78572bb1'
AP_VERSION='for ilc32g12m-ipsxmp     2025/06/20 15:43:19'
TARGET=(700,701,822,823,922,939,962,963,966,974,975,985,986,987,991,1243,1244,1245,1246,528413)
def sha(b):return hashlib.sha256(b).hexdigest()
def put(path,j):
    with path.open('x') as f:json.dump(j,f,ensure_ascii=False,indent=2);f.write('\n')
def bounded_regular_file(path):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    try:
        info=os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size>0x25800:raise ValueError('only bounded local regular config files')
        raw=b''
        while len(raw)<info.st_size:
            b=os.read(fd,info.st_size-len(raw))
            if not b:raise ValueError('file changed or short read')
            raw+=b
        if os.fstat(fd).st_size!=info.st_size:raise ValueError('file size changed')
        return raw
    finally:os.close(fd)
def inspect(raw):
    r={'sha256':sha(raw),'bytes':len(raw),'offline_fixed_package_configuration_accepted':False,
        'device_compatibility_actual_loading_or_runtime_allocation_proven':False,'camera_operations_authorized':False}
    try:cfg=p.decode_cfg(raw)
    except (ValueError,UnicodeError) as ex:
        r['rejection']=['invalid_or_incomplete_layout'];r['parse_error']=str(ex);return r,None
    units={u['unit_type']:u for u in cfg['units']};missing=sorted(set(TARGET)-set(units));counts={str(u):len(units[u]['extent_types']) for u in TARGET if u in units}
    reasons=[]
    if r['sha256']!=AP_SHA:reasons.append('not_exact_pinned_official_AP_config')
    if cfg['version_ascii']!=AP_VERSION:reasons.append('different_config_version_or_domain')
    if missing:reasons.append('missing_target_unit_types')
    if any(not 1<=n<=8 for n in counts.values()):reasons.append('target_unit_extent_list_outside_MPR_layout')
    r.update({'version':cfg['version_ascii'],'unit_count':len(units),'target_count':len(TARGET),
        'target_matches':len(set(TARGET)&set(units)),'missing_target_units':missing,'target_extent_counts':counts,
        'max_extent_list_in_complete_file':max((len(u['extent_types']) for u in units.values()),default=0),
        'rejection':reasons,'offline_fixed_package_configuration_accepted':not reasons})
    return r,cfg
def run(out):
    local_prep.volume();assert (BASE/'GOAL_STATUS.json').read_bytes()==(STAGE/'goal-status-before.json').read_bytes()
    raw=bounded_regular_file(AP);r,cfg=inspect(raw);assert r['offline_fixed_package_configuration_accepted']
    assert r['unit_count']==603 and r['target_matches']==20 and r['max_extent_list_in_complete_file']==8
    assert set(r['target_extent_counts'].values())=={1} and len(cfg['rules'])==290
    out.mkdir();(out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    checks=[{'label':'official_AP','result':r}]
    for name,b in [('CP_config',bounded_regular_file(CP)),('changed_last_version_byte',raw[:-1]+bytes([raw[-1]^1])),
            ('truncated_last_byte',raw[:-1]),('short_header',raw[:79]),('appended_byte',raw+b'\0')]:
        a,_=inspect(b);assert not a['offline_fixed_package_configuration_accepted'];checks.append({'label':name,'result':a})
    j=json.loads((BASE/'stage126-native-DMM-buffer-to-Open/run-native-buffer-Open-20261027/buffer-Open-results.json').read_text())
    units={u['unit_type']:u for u in cfg['units']};modes=[];bindings=[]
    for mode in (21,25,31,32):
        c=next(x for x in j['cases'] if x['declared_mode']==mode);rows=c['original_unit_rows']
        assert len(rows)=={21:7,25:10,31:13,32:19}[mode]
        assert all(x['original_unit_rows']==rows for x in j['cases'] if x['declared_mode']==mode)
        mapped=[]
        for row in rows:
            u=units[row['unit_type']];assert len(u['extent_types'])==1
            mapped.append({'original_MPR_row':row,'AP_config_unit_offset':u['header_offset'],'AP_extent_types':u['extent_types']})
        modes.append({'declared_mode':mode,'rows':mapped,'every_referenced_unit_exists':True,
            'every_referenced_unit_has_one_extent_in_official_AP_file':True,'actual_runtime_mode_and_allocation_unproven':True})
    assert sorted({row['original_MPR_row']['unit_type'] for m in modes for row in m['rows']})==list(TARGET)
    for unit in TARGET:
        u=units[unit];defs=[]
        for kind in ('roots','rules'):
            for g in cfg[kind]:
                for row in g['rows']:
                    if row['words'][2] in u['extent_types']:
                        defs.append({'config_group_kind':kind,'header_offset':g['header_offset'],'group_type':g['type'],
                            'selector_word12':g['selector'],'record_offset':row['offset'],'raw_words':row['words']})
        assert defs,unit
        bindings.append({'unit_type':unit,'unit_offset':u['header_offset'],'extent_types':u['extent_types'],
            'candidate_definition_rows':defs,'actual_active_rule_address_size_and_owner_unproven':True})
    # Preserve the decoded original, not a repacked or installable config.
    put(STAGE/'AP-DmmCfg-decoded.json',cfg)
    boot=(STAGE/'inputs/insmod_drv2').read_text();fstab=(STAGE/'inputs/fstab').read_text();init2=(STAGE/'inputs/init2').read_text()
    required=['DMMCFG_FILE=/setting/DmmCfg.bin','if [ ! -e $DMMCFG_FILE ] ; then',
        '    DMMCFG_FILE=/setting/DmmConfig.bin','insmod /usr/kmod/dmm.ko DmmConfig=$DMMCFG_FILE']
    assert all(s in boot for s in required)
    assert '/dev/nflasha2\t/setting' in fstab and '/dev/nflasha8\t/cp' in fstab
    assert '[ -r $INITRC_DIR/insmod_drv2     ] && . $INITRC_DIR/insmod_drv2' in init2
    excerpts={'driver_config_selection':[{'line':i,'text':s} for i,s in enumerate(boot.splitlines(),1) if s in required],
        'mounts':[{'line':i,'text':s} for i,s in enumerate(fstab.splitlines(),1) if s.startswith(('/dev/nflasha2\t','/dev/nflasha8\t'))],
        'init2_driver_source':[{'line':i,'text':s} for i,s in enumerate(init2.splitlines(),1) if 'insmod_drv2' in s]}
    output={'status':'PASS_OFFICIAL_AP_CONFIG_BOOT_SOURCE_AND_20_UNIT_BINDINGS_NOT_DEVICE_ACCEPTANCE',
        'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_sha256':sha(Path(__file__).read_bytes()),
        'official_AP':r,'config_checks':checks,'mode_unit_bindings':modes,'unit_extent_candidate_definitions':bindings,
        'startup_source_excerpts':excerpts,'actual_fallback_file_exists_or_loaded_hash_unproven':True,
        'AP_file_is_separate_from_CP_config_in_partition8':True,'new_native_execution_cases':0,
        'scripts_camera_Windows_UU_or_host_services_executed':False,'goal_complete':False,'persistent_write_release':False}
    put(out/'AP-config-results.json',output)
    print(json.dumps({'status':output['status'],'checks':len(checks),'AP_units':603,'target_matches':20,
        'target_max_extents':1,'whole_AP_max_extents':8,'mode_rows':sum(len(m['rows']) for m in modes)}))
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--out',type=Path);a.add_argument('--inspect-config',type=Path);v=a.parse_args()
    if v.inspect_config:
        result,_=inspect(bounded_regular_file(v.inspect_config));print(json.dumps(result,ensure_ascii=False,indent=2))
        raise SystemExit(0 if result['offline_fixed_package_configuration_accepted'] else 2)
    if not v.out:a.error('--out or --inspect-config is required')
    run(v.out)
