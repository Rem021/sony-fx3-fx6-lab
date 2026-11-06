#!/usr/bin/env python3
"""Fail closed on this CLI attempt; no browser/image-view side effects."""
import argparse, hashlib, json, sys
from pathlib import Path

QUALIFIED='qualified_screenshot_for_operator_review'
def capture_identity(result):
    b=result['before_eval']['before'];a=result['after_eval']
    step=b['step'];gen=b['content_generation'];seq=b['sequence'];sha=b['png_sha256']
    assert type(step) is int and 1<=step<=8
    assert type(gen) is int and gen>0 and type(seq) is int and seq>0
    assert isinstance(sha,str) and len(sha)==64 and a.get('qualified') is True
    assert a['content_generation']==gen and a.get('png_sha256',a.get('shownSHA'))==sha and a['sequence']>=seq
    if 'step' in a:assert a['step']==step
    if 'frame' in a:assert a['frame']['content_generation']==gen and a['frame']['PNG_sha256']==sha
    return {'firmware_png_sha256':sha,'firmware_generation':gen,'firmware_sequence':seq,'firmware_step':step}

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
            **capture_identity(result)}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--returncode',type=int,required=True);p.add_argument('--stdout-file',required=True);p.add_argument('--evidence-dir',required=True)
    a=p.parse_args()
    try:r=validate_capture(a.returncode,Path(a.stdout_file).read_text(),a.evidence_dir)
    except Exception as e:
        print(json.dumps({'status':'capture_failed','reason':str(e)}));raise SystemExit(2)
    print(json.dumps(r))
