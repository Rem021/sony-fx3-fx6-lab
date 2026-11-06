#!/usr/bin/env python3
"""Fail closed on this CLI attempt; no browser/image-view side effects."""
import argparse, hashlib, json, sys
from pathlib import Path

QUALIFIED='qualified_screenshot_for_operator_review'
def validate_capture(returncode,stdout,evidence_dir):
    if returncode!=0:raise ValueError('bounded_CLI_nonzero_exit:'+str(returncode))
    result=json.loads(stdout)
    if not isinstance(result,dict) or result.get('status')!=QUALIFIED:
        raise ValueError('bounded_CLI_not_qualified:'+str(result.get('reason',result.get('status')) if isinstance(result,dict) else 'invalid_shape'))
    expected=Path(evidence_dir)
    if expected.is_symlink() or not expected.is_dir():raise ValueError('new_evidence_directory_missing_or_symlink')
    raw=result.get('screenshot_path')
    if not isinstance(raw,str) or not Path(raw).is_absolute():raise ValueError('screenshot_path_not_absolute')
    shot=Path(raw)
    if shot.name!='menu-reference-page.png' or shot.parent!=expected:
        raise ValueError('screenshot_not_in_this_new_exclusive_evidence_directory')
    if shot.is_symlink() or not shot.is_file() or shot.resolve(strict=True).parent!=expected.resolve(strict=True):
        raise ValueError('screenshot_missing_nonregular_or_symlink')
    data=shot.read_bytes()
    if not data.startswith(b'\x89PNG\r\n\x1a\n'):raise ValueError('screenshot_not_PNG')
    if hashlib.sha256(data).hexdigest()!=result.get('screenshot_file_sha256'):
        raise ValueError('screenshot_hash_mismatch')
    return {'status':QUALIFIED,'validated_new_screenshot':True,'screenshot_path':str(shot),
            'screenshot_file_sha256':result['screenshot_file_sha256'],
            'firmware_png_sha256':result.get('before_eval',{}).get('before',{}).get('png_sha256')}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--returncode',type=int,required=True);p.add_argument('--stdout-file',required=True);p.add_argument('--evidence-dir',required=True)
    a=p.parse_args()
    try:r=validate_capture(a.returncode,Path(a.stdout_file).read_text(),a.evidence_dir)
    except Exception as e:
        print(json.dumps({'status':'capture_failed','reason':str(e)}));raise SystemExit(2)
    print(json.dumps(r))
