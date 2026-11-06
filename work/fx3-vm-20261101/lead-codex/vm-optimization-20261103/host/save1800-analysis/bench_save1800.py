"""Offline fixed-SHA full-corpus host reading/regex comparison."""
import hashlib
import json
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOST = HERE.parent
sys.path.insert(0, str(HOST / 'incremental-log'))
sys.path.insert(0, str(HOST))
sys.path.insert(0, str(HERE.parents[3] / 'menu-repair-01/runtime'))
from serial_snapshot import SerialSnapshot
from nonuniform_candidate import nonuniform_rgba
from guarded_reject import guarded_rejects, ASSERT, RM
from osd_ring93_v4 import rgba

RUN = HERE.parents[1] / 'runtime/runs/vmopt-20261103-save1800-836febd8'
SERIAL = RUN / 'serial.log'
SHA = '54dd1237d678dfd5aa2cd03d0b087a5a45a438d69ab63c7365c587a6272270ec'


def actual_regex(text):
    """The actual runner's serial predicates; outputs retain match order/count."""
    return {
        'unfetched': 'unfetched' in text,
        'alloc_minus1018': bool(re.search(r'FX3_LIGHT104_ALLOC_RETURN[^\n]*result=-1018(?: |$)', text)),
        'uipc_base': re.search(r'FX3_UIPC104_TEXT_BASE=(0x[0-9a-fA-F]+)', text).group(1) if re.search(r'FX3_UIPC104_TEXT_BASE=(0x[0-9a-fA-F]+)', text) else None,
        'gpe_base': re.search(r'FX3_GPE104_LIB_BIND base=(0x[0-9a-fA-F]+)', text).group(1) if re.search(r'FX3_GPE104_LIB_BIND base=(0x[0-9a-fA-F]+)', text) else None,
        'backup_base': re.search(r'FX3_BACKUP102_TEXT_BASE=(0x[0-9a-fA-F]+)', text).group(1) if re.search(r'FX3_BACKUP102_TEXT_BASE=(0x[0-9a-fA-F]+)', text) else None,
        'sync_reject': bool(re.search(r'FX3_SYNC100_REJECT|FX3_SYNC100_DISABLED|FX3_TOUCH100_REJECT|FX3_PRESET_CONTEXT_BIND_REJECT|FX3_SYNC100_API_BIND[^\n]*result=-', text)),
        'date_reject': 'FX3_DATE99_REJECT' in text,
        'ldec_failure': any(t in text for t in ['FX3_LDEC103_INIT_FAILED','FX3_LDEC103_SELFTEST_FAILED']),
        'ldec_ioctl_failure': bool(re.search(r'FX3_LDEC103_IOCTL[^\n]*result=-[0-9]+', text.split('FX3_LDEC103_GUEST_IOCTL_SELFTEST_PASS',1)[1])) if 'FX3_LDEC103_GUEST_IOCTL_SELFTEST_PASS' in text else False,
        'assert': bool(re.search(r'assert at|Assertion|exception monitor|FX3_SIGNAL_OBSERVE[^\n]*signal=6(?: |$)',text,re.I)),
        'rm_reject': bool(re.search(r'FX3_RM_[A-Z_]*REJECT|FX3_RM_UNKNOWN|unknown\s+key|invalid\s+from_type',text,re.I)),
        'media_failure': 'FX3_MEDIA_INIT_TIMEOUT' in text or bool(re.search(r'FX3_MEDIA_NOTIFY [^\n]*status=1 ',text)),
        'media_mount': 'FX3_MEDIA_MOUNT_ENTER' in text or 'MOUNT_ERR_EXTMEDIA_SLOT' in text,
        'opens': [m.group(1) for m in re.finditer(r'FX3_AP89_SCREEN_OPEN_ENTER [^\n]*id2=(0x[0-9a-f]+)',text)],
        'keys_up': [m.groups() for m in re.finditer(r'FX3_SYNTH_KEY step=(\d+) key=(0x[0-9a-f]+) status=0 [^\n]*result=0 ',text)],
        'branches': re.findall(r'FX3_MEDIA_START_BRANCH [^\n]*state=(\d+)',text),
        'notify': re.findall(r'FX3_MEDIA_NOTIFY [^\n]*mediaID=(0x[0-9a-f]+) [^\n]*status=(\d+)',text),
        'freed': re.findall(r'FX3_RM_NATIVE_FREE [^\n]*bytes=(\d+) [^\n]*result=0 ',text),
        'file_window': 'FX3_AP101_NATIVE_LOAD_READBACK_WINDOW_BEGIN' in text,
        'file_generation': 'FX3_FILE100_NATIVE_FILE_READ generation=1 ' in text,
        'before_ap': 'FX3_AP_NATURAL_BOOTIN_BEGIN' not in text,
        'backup_load': 'FX3_BACKUP_INSMOD_RC=0' in text,
        'uptime': [m.groups() for m in re.finditer(r'FX3_GUEST_UPTIME_SNAPSHOT\s*\n([0-9]+\.[0-9]+) ([0-9]+\.[0-9]+)',text)],
        'diagnostic': any(x in text for x in ['FX3_OSD_PAIR_DEADLINE_EVIDENCE_END','FX3_OSD_ALLOC_DEADLINE_EVIDENCE_END','FX3_OSD_HEADLESS_REJECT','FX3_BACKUP_CP_OWNER_FAILED','FX3_AP89_REPLAY_FAILED','FX3_MEDIA_OWNED_RAW_REJECT','FX3_MEDIA_BIND_REJECT','FX3_GPE_RESOURCE_BIND_REJECT','FX3_PRESET_CONTEXT_BIND_REJECT','FX3_GPE_EARLY_BIND_REJECT','FX3_BACKUP_CP_REJECT','FX3_BACKUP_CP_RETRY','FX3_SYS_UUD_REJECT','FX3_DISPLAY_BIND_FAIL','FX3_DISPLAY_SELFTEST_FAIL']),
        'gpe_reject': bool(re.search(r'FX3_GPE_CMD [^\n]* result=[1-9][0-9]* ',text)),
        'fatal': any(x in text for x in ['Unhandled fault:','Entering exception monitor.','Kernel panic','symbol lookup error:']),
    }


def measured(fn):
    start=time.process_time_ns();value=fn();return value,(time.process_time_ns()-start)/1e6


def main():
    assert hashlib.file_digest(SERIAL.open('rb'),'sha256').hexdigest()==SHA
    old,old_read=measured(lambda:SERIAL.read_text(errors='replace'))
    reader=SerialSnapshot(SERIAL)
    new,new_first=measured(reader.poll)
    assert old==new
    _,old_repeat=measured(lambda:SERIAL.read_text(errors='replace'))
    new_repeat_text,new_repeat=measured(reader.poll)
    assert new_repeat_text==old
    old_events,old_regex=measured(lambda:actual_regex(old))
    new_events,new_regex=measured(lambda:actual_regex(new))
    assert old_events==new_events
    old_reject,old_reject_ms=measured(lambda:(bool(ASSERT.search(old)),bool(RM.search(old))))
    new_reject,new_reject_ms=measured(lambda:guarded_rejects(new))
    assert old_reject==new_reject
    frame_rows=[]
    for stem in ['osd-frame-000001','osd-frame-000023','osd-frame-004680']:
        meta=json.loads((RUN/(stem+'.json')).read_text())
        raw=(RUN/(stem+'.raw')).read_bytes()
        pixels=rgba(raw,meta['width'],meta['height'],meta['stride_pixels'],meta['native_format'])
        def old_scan():return any(pixels[i:i+4]!=pixels[:4] for i in range(4,len(pixels),4))
        a,a_ms=measured(lambda:[old_scan() for _ in range(200)])
        b,b_ms=measured(lambda:[nonuniform_rgba(pixels) for _ in range(200)])
        assert a==b
        frame_rows.append({'stem':stem,'raw_sha256':hashlib.sha256(raw).hexdigest(),'raw_bytes':len(raw),'rgba_bytes':len(pixels),'old_200_cpu_ms':round(a_ms,3),'candidate_200_cpu_ms':round(b_ms,3)})
    output={'serial_sha256':SHA,'serial_bytes':SERIAL.stat().st_size,'decoded_chars':len(old),
            'old_first_read_cpu_ms':round(old_read,3),'candidate_first_read_cpu_ms':round(new_first,3),
            'old_repeat_read_cpu_ms':round(old_repeat,3),'candidate_repeat_poll_cpu_ms':round(new_repeat,3),
            'old_actual_regex_cpu_ms':round(old_regex,3),'candidate_actual_regex_cpu_ms':round(new_regex,3),
            'old_two_reject_regex_cpu_ms':round(old_reject_ms,3),
            'guarded_two_reject_cpu_ms':round(new_reject_ms,3),
            'two_rejects_equal':True,
            'actual_regex_equal':True,'actual_regex_event_counts':{k:len(v) for k,v in old_events.items() if isinstance(v,list)},
            'old_repeat_file_bytes':SERIAL.stat().st_size,'candidate_repeat_anchor_bytes':64,
            'retained_decoded_chars':len(reader.text),'frames':frame_rows,
            'scope':'full 81.3MB corpus single pass and one unchanged repeat; not a recorded 607-poll run, no guest timing proof'}
    (HERE/'bench.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps(output,indent=2))


if __name__=='__main__':main()
