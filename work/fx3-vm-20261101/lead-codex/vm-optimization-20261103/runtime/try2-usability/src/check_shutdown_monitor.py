#!/usr/bin/env python3
import sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from trial_log_v3_usability import FullLogMonitor
with tempfile.TemporaryDirectory() as d:
 p=Path(d)/'serial.log';p.touch();m=FullLogMonitor(p)
 with p.open('a') as f:f.write('open screen: scr0039_boot -> scr0039_shutdown\n')
 m.poll(); at_ready=len(m.native_shutdown_events)
 assert at_ready==1
 assert not m.native_power_off_events
 with p.open('a') as f:f.write('FX3_BOOT_QUEUE_SEND tid=379 bytes=28 source=0x830128 raw=2c000300000000000000000000000000000000000000000000000000 caller_relative=0x2eacd4c\n')
 m.poll(); assert len(m.native_power_off_events)==1
 with p.open('a') as f:f.write('open screen: scr7001_1003 -> scr0039_shut')
 m.poll(); assert len(m.native_shutdown_events)==at_ready
 with p.open('a') as f:f.write('down\n')
 m.poll(); assert len(m.native_shutdown_events)==at_ready+1
 assert m.native_shutdown_events[-1]=='open screen: scr7001_1003 -> scr0039_shutdown'
 print('shutdown exact original line, pre-ready baseline, cross-poll fragment PASS')
