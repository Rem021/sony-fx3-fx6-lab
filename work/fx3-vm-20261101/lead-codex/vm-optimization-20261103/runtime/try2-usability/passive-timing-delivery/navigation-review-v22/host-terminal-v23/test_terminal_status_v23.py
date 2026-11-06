import ast
import json
from pathlib import Path
from terminal_status_v23 import terminal_summary

HERE=Path(__file__).resolve().parent
RUN=HERE.parents[2]/'runs/try2navreview-web-v22-c3aed1dd'
actual=json.loads((RUN/'receipt.json').read_text())
answer=terminal_summary(actual)
assert '原生关机' in answer['status'] and '运行中' not in answer['status']
assert answer['last_stop_cause']=='health_failure'
assert answer['last_health_pass'] is False and answer['last_lifecycle_pass'] is True
assert answer['restart_requires_new_authorization'] is True

cases={'native_shutdown':dict(actual,native_model_power_off_after_ready=False,native_shutdown_after_ready=True),
       'healthy':dict(actual,native_model_power_off_after_ready=False,native_shutdown_after_ready=False,health_pass=True,stop_cause='end_trial_button'),
       'host_failure':dict(actual,native_model_power_off_after_ready=False,native_shutdown_after_ready=False,health_pass=False,stop_cause='host_error'),
       'cleanup_failure':dict(actual,lifecycle_pass=False),
       'startup_failure':dict(actual,qemu_pid=None,lifecycle_pass=False)}
expected={'native_shutdown':'原生关机','healthy':'健康检查通过','host_failure':'健康检查未通过',
          'cleanup_failure':'收尾检查未全部通过','startup_failure':'模拟器未启动'}
for name,case in cases.items():
    result=terminal_summary(case)
    assert expected[name] in result['status'] and '运行中' not in result['status']

source=(HERE/'run_trial_v22_navigation_review.py').read_text()
tree=ast.parse(source)
main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
assert "terminal = terminal_summary(receipt)" in source
assert "'next_minimal_command': {**terminal" in source
assert "final_message = terminal['status']" in source
print(json.dumps({'status':'PASS','actual_run_status':answer,'cases':list(cases),
                  'production_runner_uses_terminal_summary':True,'guest_started':False},ensure_ascii=False,indent=2))
