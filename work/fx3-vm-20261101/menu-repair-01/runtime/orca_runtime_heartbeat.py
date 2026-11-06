from pathlib import Path
import time,subprocess,json,os,datetime
R=Path(__file__).resolve().parent;stop=R/'.heartbeat-stop-ctx_ee4f6943c8d7';deadline=time.monotonic()+7200
while time.monotonic()<deadline:
 for _ in range(240):
  if stop.exists():raise SystemExit(0)
  time.sleep(1)
 try:
  s=json.loads((R/'STATE.json').read_text());phase='reviewing' if s.get('current_run') else 'implementing'
 except Exception:phase='implementing'
 p=subprocess.run(['orca','orchestration','send','--from','orca_session_id:6cbe29fd-fb24-4199-bba8-b8ad99383477','--type','heartbeat','--subject','alive','--task-id','task_bf4f4211be76','--dispatch-id','ctx_ee4f6943c8d7','--phase',phase],text=True,capture_output=True)
 print(datetime.datetime.now(datetime.timezone.utc).isoformat(),p.returncode,p.stdout.strip(),p.stderr.strip(),flush=True)
