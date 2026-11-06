#!/usr/bin/env python3
"""Offline checks of four inspected, pinned upstream host functions only.

AST-loads selected definitions, never imports upstream packages or creates a
camera object. Byte buffers/journals/boot IDs and read-only fake camera replies
are explicit fixtures. No native worker, compiler, USB, auth, or firmware write.
The source directory must contain the pinned reference files from download
receipts; fetch them separately if the temporary reference copy was retired.
"""
from pathlib import Path
import argparse
import ast
import builtins
import datetime
import json
import re
import sys
import traceback
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'work/sony-firmware-20261024'
STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE/'stage25-mc-image-map'))
import mc_image_map as im


def pinned_inventory():
    rows={}
    for file in sorted(STAGE.glob('source-downloads*.json')):
        for row in json.loads(file.read_text())['records']:
            if row.get('error') is None:
                assert row['path'] not in rows
                rows[row['path']]=row
    return rows


def selected(source_root,relative,name,namespace,receipts):
    row=pinned_inventory()[relative];path=source_root/relative;raw=path.read_bytes()
    assert im.sha(raw)==row['sha256'];text=raw.decode('utf-8');tree=ast.parse(text)
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name]
    assert len(nodes)==1;node=nodes[0]
    assert not node.decorator_list and not any(isinstance(n,(ast.Import,ast.ImportFrom)) for n in ast.walk(node))
    allowed=('ValueError','AssertionError','any','len','int','list','set','bytes','str','map','min','max','range','sorted','dict','tuple','next','hex')
    namespace=dict(namespace,__builtins__={key:getattr(builtins,key) for key in allowed})
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec'),namespace)
    receipts.append({'file':relative,'function':name,'line_start':node.lineno,'line_end':node.end_lineno,
      'file_sha256':im.sha(raw),'function_source_sha256':im.sha(ast.get_source_segment(text,node).encode()),
      'whole_module_imported':False})
    return namespace[name]


def run(out,source_root):
    prior=BASE/'stage45-stop-notification-routing/final-receipt.json'
    assert im.sha(prior.read_bytes())=='2823c9b165fec0d2170d4d005598f91001d8b46ca464f6b8a06a8c7a0b050cf5'
    for row in json.loads(prior.read_text())['files']:assert im.sha((ROOT/row['path']).read_bytes())==row['sha256']
    inventory=pinned_inventory();relative='src/looks/looktool/worker.py'
    raw=(source_root/relative).read_bytes();assert im.sha(raw)==inventory[relative]['sha256']
    tree=ast.parse(raw)
    assignment=[n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='NAMES' for t in n.targets)]
    assert len(assignment)==1;names=ast.literal_eval(assignment[0].value);assert names==('appFw.so','cpapp-b.bin')
    receipts=[]
    same_body=selected(source_root,'src/looks/looktool/checkpoint.py','same_body',{},receipts)
    difference=selected(source_root,'src/looks/looktool/checkpointjob.py','program_difference',{},receipts)
    known=selected(source_root,'src/looks/looktool/factoryrecover.py','known_programs',
      {'Path':Path,'re':re,'worker':SimpleNamespace(NAMES=names)},receipts)
    def forbidden_branch(*args,**kwargs):
        raise AssertionError('Unexercised outcome parser branch must never be substituted')
    completion=selected(source_root,'src/looks/looktool/factoryrecover.py','completion_evidence',
      {'re':re,'outcome':forbidden_branch},receipts)
    cases=[]
    def check(label,call,reject=False,expected=None):
        try:result=call()
        except ValueError as error:
            assert reject,(label,str(error));cases.append({'case':label,'outcome':'expected_rejection','detail':str(error)});return
        assert not reject,label
        assert result==expected,(label,result,expected)
        cases.append({'case':label,'outcome':'expected_acceptance_within_host_fixture_scope','result':result})
    identity={'model':'ILCE-7CM2','serial_sha256':'a'*64,'usb_serial_sha256':'b'*64}
    check('same body serial and USB digests',lambda:same_body(identity,dict(identity)))
    check('conflicting normal serial even if USB matches',lambda:same_body(identity,dict(identity,serial_sha256='c'*64)),True)
    check('missing common body identifier',lambda:same_body({'model':'ILCE-7CM2'},{'model':'ILCE-7CM2'}),True)
    check('FX3 rejected by original A7C II identity function',lambda:same_body(identity,dict(identity,model='ILME-FX3')),True)
    check('legacy normal serial only',lambda:same_body(identity,{'model':'ILCE-7CM2','serial_sha256':'a'*64}))

    root=out/'fixture-transaction';worker=root/'worker';worker.mkdir(parents=True);(root/'evidence').mkdir()
    ap,cp=bytes(range(32)),bytes(range(16));target_ap=bytearray(ap);target_cp=bytearray(cp)
    windows=[(0,4,ap[4:8],bytes.fromhex('aabbccdd')),(0,12,ap[12:16],bytes.fromhex('10203040')),
      (1,8,cp[8:12],bytes.fromhex('fedcba98'))]
    lines=[];rows=[]
    for i,(chip,at,old,new) in enumerate(windows):
        for kind,data in (('old',old),('new',new)):
            lines.append('static const u8 '+kind+'_'+str(i)+'[]={'+','.join(map(str,data))+'};')
        rows.append('{'+f'{at}UL,{len(old)},{chip},old_{i},new_{i}'+'}')
        (target_cp if chip else target_ap)[at:at+len(new)]=new
    lines.append('static const struct Window windows[]={'+','.join(rows)+'};')
    header=worker/'batch.private.h';header.write_text('\n'.join(lines)+'\n',encoding='ascii')
    # No executable exists at this path: the upstream check only reads the
    # accompanying header. It is a synthetic transaction-evidence fixture.
    build={'path':str(worker/'batch.fixture'),'windows':3,'sizes':[32,16]}
    state={'program_builds':[build]};history=[(root,state)]
    images=lambda a,b:{'appFw.so':bytes(a),'cpapp-b.bin':bytes(b)}
    check('all complete windows old',lambda:known(images(ap,cp),history))
    check('all complete windows target',lambda:known(images(target_ap,target_cp),history))
    partial=bytearray(ap);partial[4:8]=target_ap[4:8]
    check('different completed windows may be old or target',lambda:known(images(partial,cp),history))
    torn=bytearray(ap);torn[4:6]=target_ap[4:6]
    check('mixed bytes inside one window rejected',lambda:known(images(torn,cp),history),True)
    check('program length mismatch rejected',lambda:known(images(ap[:-1],cp),history),True)
    external={'program_builds':[dict(build,path=str(out/'elsewhere/batch.fixture'))]}
    check('header outside recorded worker directory rejected',lambda:known(images(ap,cp),[(root,external)]),True)
    outside=bytearray(target_ap);outside[0]=0xee
    def outside_scope():
        known(images(outside,target_cp),history)
        result=difference(bytes(target_ap),bytes(outside))
        assert result=={'expected_bytes':32,'actual_bytes':32,'first_difference':'0x0'}
        return 'window check passes; original full-program comparison still detects byte0'
    check('window check does not replace complete-byte readback',outside_scope,
      expected='window check passes; original full-program comparison still detects byte0')

    boot0='11111111-1111-1111-1111-111111111111';boot1='22222222-2222-2222-2222-222222222222'
    class CameraFixture:
        def __init__(self,boot):self.boot=boot;self.reads=[]
        def read(self,path,missing=False):
            assert path=='/proc/sys/kernel/random/boot_id'
            self.reads.append(path);return (self.boot+'\n').encode()
    intent={'result':'checkpoint.program.result','mode':1}
    def finish(boot,old=boot0,later=()):
        camera=CameraFixture(boot)
        return completion(camera,[],root,{'source_boot_id':old},intent,list(later))
    check('recorded later native completion is accepted as journal evidence',
      lambda:finish(boot0,later=[{'event':'native_result_verified'}]),expected='recorded-native-completion')
    check('empty temporary state and same boot are insufficient',lambda:finish(boot0),True)
    check('changed valid boot accepted only as new-boot evidence',lambda:finish(boot1),expected='new-camera-boot')
    check('invalid boot text rejected',lambda:finish('not-a-boot-uuid'),True)
    check('no recorded prior boot rejected',lambda:finish(boot1,old=''),True)
    (root/'evidence/old-program-report.bin').write_bytes(b'fixture: not a native report')
    check('archived program-report file does not unblock same-boot latest program intent',lambda:finish(boot0),True)
    assert len(cases)==18
    proof={'status':'PASS_18_PINNED_UPSTREAM_HOST_FUNCTION_CHECKS_WITH_SYNTHETIC_EVIDENCE_ONLY',
      'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_functions':receipts,
      'cases':cases,'worker_names_read_as_AST_literal':list(names),
      'whole_upstream_module_imported':False,'AST_extracted_original_host_functions_executed':True,
      'native_worker_or_syscall_or_camera_session_executed':False,
      'camera_boot_or_media_or_restore_or_rescue_verified':False,
      'scope':'Four inspected original host functions, synthetic bytes/headers/journals and a read-only fake boot-id reply. No claim of device protocol, kernel, write rollback, cold boot or recovery behavior.',
      'goal_complete':False,'persistent_write_release':False}
    im.write_json(out/'restore-check-results.json',proof)
    (out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    im.write_json(out/'source-receipt.json',{'script_sha256':im.sha(Path(__file__).read_bytes()),
      'previous_manifest_sha256':im.sha(prior.read_bytes()),'volume_uuid':im.VOLUME,
      'proof_sha256':im.sha((out/'restore-check-results.json').read_bytes()),'source_functions':receipts,
      'no_camera_or_remote_operation':True})
    print(json.dumps({'status':proof['status'],'checks':len(cases),'original_host_functions':len(receipts),
      'real_device_or_recovery_verified':False,'goal_complete':False,'persistent_write_release':False}))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True)
    parser.add_argument('--source-root',required=True);args=parser.parse_args();im.volume()
    out=Path(args.output).resolve();assert STAGE in out.parents and not out.exists();out.mkdir()
    try:run(out,Path(args.source_root).resolve())
    except Exception:
        (out/'attempt-source.py').write_bytes(Path(__file__).read_bytes())
        im.write_json(out/'attempt-failure.json',{'traceback':traceback.format_exc(),'passing_result':False});raise


if __name__=='__main__':main()
