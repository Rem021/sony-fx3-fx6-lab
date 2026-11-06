#!/usr/bin/env python3
"""Readback validation; does not repeat completed guest experiments."""
import ast,hashlib,json,re
from pathlib import Path
from inspect_body_policy import HERE,PATH,PIN,View

def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def main():
    prior=HERE.parent/'body-load-20261029';receipt=prior/'final-receipt.json'
    assert digest(receipt)=='6b67b82dab412adef6b928ccd3eb21242e712ed1de3478a5cfb83651f630b430'
    checked=[]
    for row in json.loads(receipt.read_text())['files']:
        p=prior/row['path'];assert p.stat().st_size==row['bytes'] and digest(p)==row['sha256'];checked.append(row['path'])
    assert len(checked)==22
    syntax=[]
    for p in sorted(HERE.glob('*.py')):ast.parse(p.read_text(),filename=str(p));syntax.append(p.name)
    parsed=[]
    for p in sorted(HERE.rglob('*.json')):
        if p.name in ['validation-results.json','final-receipt.json']:continue
        json.loads(p.read_text());parsed.append(str(p.relative_to(HERE)))
    body=View(PATH,PIN);span_checks=[]
    for file,key in [('body-policy-static-results.json','functions'),('extract-contract-static-results.json','fragments')]:
        for row in json.loads((HERE/file).read_text())[key]:
            raw=body.read(int(row['va'],16),row['bytes']);assert hashlib.sha256(raw).hexdigest()==row['sha256']
            assert (HERE/row['disassembly']).is_file();span_checks.append(dict(source=file,va=row['va'],bytes=len(raw)))
    assert len(span_checks)==25
    shell=json.loads((HERE/'shell-request-guest-results.json').read_text())['cases']
    factory=json.loads((HERE/'keytag-factory-guest-results.json').read_text())['cases']
    headers=json.loads((HERE/'tar-header-guest-results.json').read_text())['cases']
    text=json.loads((HERE/'extract-text-guest-results.json').read_text())['cases']
    assert list(map(len,[shell,factory,headers,text]))==[5,8,4,4]
    assert headers[-1]['parse_result']==2
    assert [r['extract_return'] for r in text]==[1,1,0,0]
    assert [r['sink_bytes'] for r in text]==[29,29,0,0]
    snap=json.loads((HERE/'marker-snapshot-results.json').read_text())
    assert snap['code_page_summary']==dict(total=361,readable=0,matching=0,unreadable=361,contradicting=0)
    assert next(r for r in snap['selected_checks'] if r['label']=='cached_stat_result')['signed_value']==-1
    contract=json.loads((HERE/'extract-contract-static-results.json').read_text())
    assert len(contract['string_handler_symbol_comparisons'])==20 and all(r['identical'] for r in contract['string_handler_symbol_comparisons'])
    for row in contract['original_files']:
        p=Path(row['path']);assert p.stat().st_size==row['bytes'] and digest(p)==row['sha256']
    links=[]
    for target in re.findall(r'\]\(([^)]+)\)',(HERE/'README.md').read_text()):
        if target.startswith('https://'):continue
        p=HERE/target
        if target not in ['validation-results.json','final-receipt.json']:assert p.exists(),target
        links.append(target)
    result=dict(status='PASS_BOUNDED_COMPONENT_READBACK',previous_receipt_sha256=digest(receipt),previous_sealed_files_verified=len(checked),
                syntax_files=syntax,json_files=parsed,original_span_checks=span_checks,guest_case_counts=dict(shell_request=5,keytag_factory=8,tar_header=4,benign_text_extract=4),guest_cases_total=21,
                code_identity_for_snapshot_proven=False,live_marker_state_proven=False,full_xml_dispatch_proven=False,
                local_readme_links=links,host_target_file_writes=0,native_target_execution=0,camera_actions=0,
                goal_completion_claimed=False,termination_condition_met=False)
    (HERE/'validation-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(previous_sealed_files=22,spans=25,guest_cases=21,status=result['status'],camera_actions=0)))

if __name__=='__main__':main()
