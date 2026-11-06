#!/usr/bin/env python3
"""Read explicitly named ordinary project JSON files; never query a device.

This compares recorded strings, not physical identity or process truth. Only
ASCII normalization matches the Windows ToUpperInvariant hash contract here.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat

SCHEMA='fx3-saved-argument-audit/1'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def describe(value):
    if not isinstance(value,str):return {'available':False,'normalization_supported':False}
    ascii_only=value.isascii()
    runs=[len(x) for x in re.findall(r'\\+',value)]
    parts=value.split('\\')
    shape=(ascii_only and len(parts)==3 and all(parts) and parts[0].upper()=='USB'
        and all(n==1 for n in runs) and value==value.strip()
        and not any(c in value for c in '\x00\r\n\"\''))
    vp=re.search(r'(?:^|[\\&])VID_([0-9A-Fa-f]{4})&PID_([0-9A-Fa-f]{4})(?:&|\\|$)',value)
    return {'available':True,'character_length':len(value),'utf8_bytes':len(value.encode('utf-8')),
        'raw_utf8_sha256':digest(value.encode('utf-8')),
        'uppercase_utf8_sha256':digest(value.upper().encode('utf-8')) if ascii_only else None,
        'normalization_supported':ascii_only,'normalization_scope':'ASCII ToUpperInvariant-equivalent only',
        'backslash_count':value.count('\\'),'backslash_runs':runs,
        'has_edge_whitespace':value!=value.strip(),'has_edge_quote':bool(value) and (value[0] in '\"\'' or value[-1] in '\"\''),
        'has_control_character':any(ord(c)<32 or ord(c)==127 for c in value),
        'canonical_USB_root_shape_in_this_audit':shape,
        'nonunique_vid_pid':[vp.group(1).upper(),vp.group(2).upper()] if vp else None}


def recorded_target(receipt):
    result={'evidence':'UNKNOWN','syntax':'UNKNOWN','connected_filter':None,'argument':None,
        'scope':'No command is run; capture_kind is a supplied-record claim, not independent process attestation.'}
    if not isinstance(receipt,dict):return result
    program=receipt.get('program');argv=receipt.get('argv')
    if receipt.get('capture_kind')!='native_argv' or not isinstance(program,str):return result
    if program.replace('\\','/').rsplit('/',1)[-1].lower()!='pnputil.exe':return result
    if not isinstance(argv,list) or not argv or not all(isinstance(v,str) for v in argv):return result
    switches=[x.lower() for x in argv]
    result['connected_filter']='/connected' in switches
    if switches[0]=='/enum-devices':
        if '/deviceid' in switches:
            result['syntax']='HARDWARE_OR_COMPATIBLE_ID_FILTER_NOT_INSTANCE_ID';return result
        positions=[i for i,x in enumerate(switches) if x=='/instanceid']
        if len(positions)!=1 or positions[0]+1>=len(argv):
            result['syntax']='MISSING_OR_AMBIGUOUS_INSTANCE_ID';return result
        pos=positions[0]+1
        if argv[pos].startswith('/'):
            result['syntax']='MISSING_INSTANCE_ID_VALUE';return result
        allowed={'/connected','/deviceids','/relations','/services','/stack','/drivers','/interfaces','/properties'}
        if any(x not in allowed for i,x in enumerate(switches[1:],1) if i not in (pos-1,pos)):
            result['syntax']='UNREVIEWED_EXTRA_PARAMETER';return result
        result.update(evidence='PROVIDED_NATIVE_ARGV_RECORD',syntax='ENUM_DEVICES_INSTANCEID',argument=argv[pos])
    elif switches[0]=='/enum-devicetree':
        if '/instanceid' in switches or '/deviceid' in switches:
            result['syntax']='DEVICE_TREE_ROOT_MUST_BE_POSITIONAL';return result
        positional=[x for x in argv[1:] if not x.startswith('/')]
        if len(positional)!=1:
            result['syntax']='MISSING_OR_AMBIGUOUS_DEVICE_TREE_ROOT';return result
        allowed={'/connected','/services','/stack','/drivers','/interfaces'}
        if any(x.startswith('/') and x not in allowed for x in switches[1:]):
            result['syntax']='UNREVIEWED_EXTRA_PARAMETER';return result
        result.update(evidence='PROVIDED_NATIVE_ARGV_RECORD',syntax='ENUM_DEVICETREE_POSITIONAL',argument=positional[0])
    else:result['syntax']='OUTSIDE_INTENDED_CACHED_ENUMERATION_COMMANDS'
    return result


def audit(cim_id,root_id,receipt):
    cim,root=describe(cim_id),describe(root_id);target=recorded_target(receipt)
    arg=describe(target.pop('argument'));status='UNKNOWN_MISSING_NATIVE_ARGV_OR_SOURCE'
    def comparable(*items):return all(x['available'] and x['normalization_supported'] for x in items)
    source_equal=None;argument_equal=None
    if comparable(cim,root):source_equal=cim['uppercase_utf8_sha256']==root['uppercase_utf8_sha256']
    if comparable(cim,root,arg):argument_equal=len({x['uppercase_utf8_sha256'] for x in (cim,root,arg)})==1
    if source_equal is False:status='MISMATCH_CIM_AND_SELECTED_ROOT_RECORDS'
    elif argument_equal is False:status='MISMATCH_RECORDED_NATIVE_ARGUMENT'
    elif argument_equal is True:
        status='MATCH_WITHIN_PROVIDED_RECORDS' if all(x['canonical_USB_root_shape_in_this_audit'] for x in (cim,root,arg)) else 'MATCH_BUT_IDENTIFIER_SHAPE_REQUIRES_REVIEW'
    elif any(x['available'] and not x['normalization_supported'] for x in (cim,root,arg)):
        status='UNKNOWN_NON_ASCII_NORMALIZATION'
    return {'schema':SCHEMA,'status':status,'cim_id':cim,'selected_root_id':root,'recorded_argument':arg,
        'argument_record':target,'source_id_hashes_equal':source_equal,'all_three_record_hashes_equal':argument_equal,
        'normalization_changes_no_whitespace_quotes_or_backslashes':True,
        'actual_native_process_argv_independently_observed_here':False,
        'stdout_stderr_exit_reason_or_current_connection_proven':False,
        'same_body_firmware_protocol_or_recovery_proven':False,
        'device_queries_camera_operations_or_driver_changes':False}


def pointer(document,path):
    if path=='':return document
    if not path.startswith('/'):raise ValueError('INVALID_JSON_POINTER')
    value=document
    for part in path[1:].split('/'):
        if re.search(r'~(?![01])',part):raise ValueError('INVALID_JSON_POINTER_ESCAPE')
        key=part.replace('~1','/').replace('~0','~')
        if isinstance(value,list):
            if not re.fullmatch(r'0|[1-9][0-9]*',key):raise ValueError('INVALID_JSON_ARRAY_INDEX')
            value=value[int(key)]
        elif isinstance(value,dict):value=value[key]
        else:raise ValueError('JSON_POINTER_TARGET_UNAVAILABLE')
    return value


def checked_path(root,path,output=False):
    root=Path(root).absolute();path=Path(path).absolute()
    if '..' in root.parts or '..' in path.parts:raise ValueError('PARENT_TRAVERSAL_NOT_ACCEPTED')
    # Check links/reparse attributes before resolve, and only allow descendants.
    if not path.is_relative_to(root):raise ValueError('PATH_OUTSIDE_EXPLICIT_PROJECT_ROOT')
    for p in (root,*root.parents):
        s=p.lstat()
        if stat.S_ISLNK(s.st_mode) or getattr(s,'st_file_attributes',0)&0x400:raise ValueError('LINK_OR_REPARSE_ROOT')
    for p in reversed((path,*path.parents[:len(path.parts)-len(root.parts)-1])):
        if output and p==path:
            if p.exists() or p.is_symlink():raise FileExistsError('OUTPUT_EXISTS')
            continue
        s=p.lstat()
        if stat.S_ISLNK(s.st_mode) or getattr(s,'st_file_attributes',0)&0x400:raise ValueError('LINK_OR_REPARSE_PATH')
    if not path.resolve(strict=not output).is_relative_to(root.resolve(strict=True)):raise ValueError('RESOLVED_PATH_OUTSIDE_ROOT')
    if not output and not stat.S_ISREG(path.lstat().st_mode):raise ValueError('INPUT_NOT_REGULAR_FILE')
    return path


def read_json(root,path):
    p=checked_path(root,path)
    if p.stat().st_size>8*1024*1024:raise ValueError('INPUT_TOO_LARGE')
    flags=os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)
    fd=os.open(p,flags)
    with os.fdopen(fd,'rb') as handle:
        if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):raise ValueError('INPUT_NOT_REGULAR_FILE')
        raw=handle.read(8*1024*1024+1)
    if len(raw)>8*1024*1024:raise ValueError('INPUT_TOO_LARGE')
    return json.loads(raw),{'bytes':len(raw),'sha256':digest(raw),'JSON_decoding':'stdlib UTF encoding detection, once only'}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project-root',required=True);p.add_argument('--cim',required=True);p.add_argument('--selected-root',required=True)
    p.add_argument('--receipt',required=True);p.add_argument('--cim-pointer',default='/instance_id')
    p.add_argument('--root-pointer',default='/instance_id');p.add_argument('--receipt-pointer',default='');p.add_argument('--output',required=True)
    args=p.parse_args(argv)
    try:
        cim,ch=read_json(args.project_root,args.cim);root,rh=read_json(args.project_root,args.selected_root)
        receipt,ah=read_json(args.project_root,args.receipt)
        result=audit(pointer(cim,args.cim_pointer),pointer(root,args.root_pointer),pointer(receipt,args.receipt_pointer))
        result['input_file_hashes']={'cim':ch,'selected_root':rh,'receipt':ah}
        output=checked_path(args.project_root,args.output,output=True)
        with output.open('x',encoding='utf-8') as handle:json.dump(result,handle,ensure_ascii=False,indent=2);handle.write('\n')
        print(json.dumps({'status':result['status'],'device_queries':False}))
        return 0
    except (OSError,ValueError,KeyError,IndexError,TypeError,UnicodeError) as error:
        # Never echo an exception message containing a private ID/path/value.
        print(json.dumps({'status':'AUDIT_INPUT_OR_OUTPUT_ERROR','error_class':type(error).__name__,'device_queries':False}))
        return 2


if __name__=='__main__':raise SystemExit(main())
