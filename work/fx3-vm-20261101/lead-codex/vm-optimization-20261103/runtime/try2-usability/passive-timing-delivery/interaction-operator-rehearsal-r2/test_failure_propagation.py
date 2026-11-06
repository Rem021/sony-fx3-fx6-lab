#!/usr/bin/env python3
"""Small local fake-CLI checks only. NO browser, timer, fixture or guest."""
import base64,datetime,hashlib,json,subprocess,sys
from pathlib import Path
H=Path(__file__).resolve().parent
T=H/'wrapper-local-checks';T.mkdir()
png=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScLbtAAAAABJRU5ErkJggg==')
results=[]
for case in ['nonzero_despite_qualified','status_failure','missing_file','outside_directory','valid_current_file']:
    root=T/case;root.mkdir();evidence=root/'new-capture';evidence.mkdir()
    shot=evidence/'menu-reference-page.png'
    if case not in ['missing_file','outside_directory']:shot.write_bytes(png)
    if case=='outside_directory':shot=root/'old-image.png';shot.write_bytes(png)
    body={'status':'no_qualified_screenshot' if case=='status_failure' else 'qualified_screenshot_for_operator_review',
          'screenshot_path':str(shot),'screenshot_file_sha256':hashlib.sha256(png).hexdigest(),'reason':'fake_cli_error_for_local_validation'}
    fake=root/'fake_cli.py';fake.write_text('import json,sys\nprint('+repr(json.dumps(body))+')\nsys.exit('+str(2 if case=='nonzero_despite_qualified' else 0)+')\n')
    child=subprocess.run([sys.executable,'-B',str(fake)],capture_output=True,text=True)
    out=root/'fake-stdout.json';out.write_text(child.stdout)
    wrapper=subprocess.run([sys.executable,'-B',str(H/'capture_validation.py'),'--returncode',str(child.returncode),'--stdout-file',str(out),'--evidence-dir',str(evidence)],capture_output=True,text=True)
    parsed=json.loads(wrapper.stdout)
    expected=0 if case=='valid_current_file' else 2
    assert wrapper.returncode==expected,(case,wrapper.stdout,wrapper.stderr)
    assert (parsed.get('validated_new_screenshot') is True)==(expected==0)
    if expected:assert 'screenshot_path' not in parsed
    results.append({'case':case,'fake_CLI_exit':child.returncode,'wrapper_exit':wrapper.returncode,'result':parsed,'passed':True})
(H/'WRAPPER-LOCAL-RESULT.json').write_text(json.dumps({'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'five local fake subprocess output checks; zero browser/arm/key','passed':True,'cases':results},indent=2)+'\n')
print(json.dumps({'passed':True,'cases':len(results),'browser_or_timer_started':False}))
