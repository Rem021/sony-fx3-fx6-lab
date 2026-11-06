#!/usr/bin/env python3
"""R27 historical transport replay only. No operate, VM, native, browser or timer."""
import argparse,importlib.util,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent/'r26-tool-return-preparation'
spec=importlib.util.spec_from_file_location('r26_return_adapter_replay',BASE/'return_adapter.py');adapter=importlib.util.module_from_spec(spec);spec.loader.exec_module(adapter)
p=argparse.ArgumentParser();p.add_argument('group',choices=['group-a','group-b']);p.add_argument('action',choices=['click','pin','confirm']);a=p.parse_args()
run=ROOT/'evidence'/a.group;out=run/a.action
case={'click':'observation','pin':'fixed','confirm':'confirmation'}[a.action]
code=adapter._execute_once([sys.executable,'-B',str(BASE/'fake_child.py'),case,str(run)],a.action,run,out,{**os.environ,'FX3_RETURN_FIXTURE_ONLY':'1','PYTHONDONTWRITEBYTECODE':'1'})
raise SystemExit(code)
