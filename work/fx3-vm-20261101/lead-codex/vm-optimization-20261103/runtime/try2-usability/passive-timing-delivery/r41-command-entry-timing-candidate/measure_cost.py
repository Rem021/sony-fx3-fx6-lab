from pathlib import Path
import json,os,subprocess,hashlib,statistics
O=Path(__file__).resolve().parent;H=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/runtime/helpers');commands=[];values={}
for cand in (False,True):
 label='candidate' if cand else 'original';header=O/'src/fx3-complete104-observe-v1.h' if cand else H/'fx3-complete104-observe-v1.h';exe=O/'build'/('cost-'+label)
 argv=['/usr/bin/clang','-std=gnu11','-O2','-I',str(H),'-DTEST_CANDIDATE='+str(int(cand)),'-DRETURN_HEADER="'+str(header)+'"',str(O/'tests/cost.c'),'-o',str(exe)]
 p=subprocess.run(argv,capture_output=True);(O/'receipts'/('cost-build-'+label+'.stdout')).write_bytes(p.stdout);(O/'receipts'/('cost-build-'+label+'.stderr')).write_bytes(p.stderr);commands.append({'argv':argv,'exit':p.returncode});assert not p.returncode,p.stderr
 p=subprocess.run([str(exe),'20000'],capture_output=True);(O/'receipts'/('cost-'+label+'.csv')).write_bytes(p.stdout);(O/'receipts'/('cost-'+label+'.stderr')).write_bytes(p.stderr);assert not p.returncode,p.stderr
 rows=[[int(x) for x in line.split(',')] for line in p.stdout.decode().splitlines()];assert len(rows)==3
 values[label]={'raw_rows':rows,'ns_per_return_helper_with_sink':[row[3]/row[2] for row in rows],'bytes_per_line':[row[4]/row[2] for row in rows]}
values['delta_median_host_ns']=statistics.median(values['candidate']['ns_per_return_helper_with_sink'])-statistics.median(values['original']['ns_per_return_helper_with_sink']);values['extra_clock_calls_per_command']=1;values['extra_dprintf_calls']=0;values['extra_characters_max_u64']=len(' entry_ns=')+20;assert values['extra_characters_max_u64']==30
values['limits']='host CLOCK_MONOTONIC/format-to-buffer cost only, includes one added clock and appended formatting; original helper includes its own clock. No serial syscall, native raster, guest/QEMU/CPU-time or performance improvement inference.'
(O/'COST.json').write_text(json.dumps({'commands':commands,'measurement':values,'host_source_sha256':hashlib.sha256((O/'tests/cost.c').read_bytes()).hexdigest()},indent=2)+'\n');print('finite host cost',values['delta_median_host_ns'],'ns median difference; max +30 chars, +1 clock')
