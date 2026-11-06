from pathlib import Path
R=Path(__file__).resolve().parent
s=(R/'prepare_candidate89.py').read_text().replace("D=R/'ap89-backup-ram-replay'","D=R/'ap89-r2-backup-helper-replay'")
a=s.index("  replay=f'''");b=s.index("''';s=s.replace(needle,replay+needle)",a)
replay='''  replay='\'\' echo FX3_AP89_BACKUP_REPLAY_BEGIN physical=0x404000000 bytes=0x221000 original_seed_load_finished=1 AP_not_started=1 raw_RAM_input=1 not_storage_file=1
 /simulation/fx3-backup-replay-v1
 replay_rc=$?
 echo FX3_AP89_BACKUP_REPLAY_HELPER_RC=$replay_rc
 if [ "$replay_rc" != 0 ]; then echo FX3_AP89_REPLAY_FAILED; while true; do /bin/busybox sleep 1; done; fi
 echo FX3_AP89_HOST_READBACK_WINDOW_BEGIN bounded_seconds=5 AP_not_started=1
 /bin/busybox sleep 5
 echo FX3_AP89_HOST_READBACK_WINDOW_END
'''
s=s[:a]+replay+s[b:];s=s.replace("assert template;entries.append(('simulation/ap89-backup-ram.bin'", "assert template;entries.append(('simulation/fx3-backup-replay-v1',template,(H/'fx3-backup-replay-v1').read_bytes()));entries.append(('simulation/ap89-backup-ram.bin'")
s=s.replace('ddexactfrozenAP88liveRAM','helperSHAvalidatesfrozenAP88liveRAMandremapsreadbackbeforehostQMPsnapshot').replace("'mechanism':'guest/dev/mem boundedddwriteafteroriginalbackupmoduleload,beforeAPstarts;fullSHAreadback'", "'mechanism':'boundedguesthelperfixedSHA/twooriginalbankheaders/wholecopy/remapSHA/rollback;5sboundedpreAPhostQMPreadbackwindow'")
s=s.replace("'CPIO_added':['simulation/ap89-backup-ram.bin'", "'CPIO_added':['simulation/fx3-backup-replay-v1','simulation/ap89-backup-ram.bin'")
s=s[:s.index("s=(R/'run_candidate88_model_r4.py')")]+'''print(D/'candidate.json')
'''
path=R/'_prepare_candidate89_r2_impl.py';path.write_text(s);exec(compile(s,str(path),'exec'))
source=(R/'run_candidate89.py').read_text().replace('            early_stop_reason = None\n','            early_stop_reason = None\n            replay_input_verified = False\n')
needle="                serial_now=(run/'serial.log').read_text(errors='replace')\n"
extra='''                if 'FX3_AP89_BACKUP_REPLAY_VERIFIED' in serial_now and not replay_input_verified:
                    qmp('stop')
                    before_AP='FX3_AP_NATURAL_BOOTIN_BEGIN' not in serial_now
                    input_path=run/'ap89-input-before-AP.bin'
                    qmp('human-monitor-command',{'command-line':'pmemsave 0x404000000 0x221000 "'+str(input_path)+'"'})
                    got=digest(input_path);wanted=candidate['backup_replay']['sha256']
                    verified=got==wanted and before_AP
                    (run/'ap89-host-input-readback.json').write_text(json.dumps({'sha256':got,'expected':wanted,'before_AP_bootin_marker':before_AP,'verified':verified,'bytes':input_path.stat().st_size,'physical':'0x404000000','method':'QMPstop/pmemsave afterguesthelperremapSHA beforeAPlaunch;existingreservedRAMonly'},indent=2)+'\\n')
                    if not verified:
                        early_stop_reason='AP89 independenthostRAMSHA or preAPtiming mismatch; stopbeforevalidation'
                        break
                    replay_input_verified=True
                    qmp('cont')
'''
assert needle in source;source=source.replace(needle,needle+extra);(R/'run_candidate89_r2.py').write_text(source)
