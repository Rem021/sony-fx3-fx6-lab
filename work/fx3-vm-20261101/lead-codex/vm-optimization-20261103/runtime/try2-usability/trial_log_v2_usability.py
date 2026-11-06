"""Incremental complete serial-log inspection; the original log is never truncated."""
import re

FAILURES = [
    (r'assert at|Assertion|\bASSERT(?:!|:|\s+fail)|exception monitor|FX3_SIGNAL_OBSERVE[^\n]*signal=6(?:\s|$)',
     '原厂断言、异常或 abort'),
    (r'Kernel panic|Unhandled fault:|symbol lookup error:|\bOops:|\bBUG:', '固件或内核异常'),
    (r'FX3_SYNC100_REJECT|FX3_SYNC100_DISABLED|FX3_TOUCH100_REJECT|FX3_PRESET_CONTEXT_BIND_REJECT|FX3_SYNC100_API_BIND[^\n]*result=-', '设备或观察器合同拒绝'),
    (r'FX3_DATE99_REJECT|FX3_RM_[A-Z_]*REJECT|FX3_RM_UNKNOWN|unknown\s+key|invalid\s+from_type', '日期或按钮合同拒绝'),
    (r'FX3_MEDIA_INIT_TIMEOUT|FX3_MEDIA_NOTIFY [^\n]*status=1 |FX3_MEDIA_MOUNT_ENTER|MOUNT_ERR_EXTMEDIA_SLOT', '媒体初始化异常'),
    (r'FX3_OSD_PAIR_DEADLINE_EVIDENCE_END|FX3_OSD_ALLOC_DEADLINE_EVIDENCE_END|FX3_OSD_HEADLESS_REJECT|FX3_BACKUP_CP_OWNER_FAILED|FX3_AP89_REPLAY_FAILED|FX3_MEDIA_OWNED_RAW_REJECT|FX3_MEDIA_BIND_REJECT|FX3_GPE_RESOURCE_BIND_REJECT|FX3_PRESET_CONTEXT_BIND_REJECT|FX3_GPE_EARLY_BIND_REJECT|FX3_BACKUP_CP_REJECT|FX3_BACKUP_CP_RETRY|FX3_SYS_UUD_REJECT|FX3_DISPLAY_BIND_FAIL|FX3_DISPLAY_SELFTEST_FAIL', '原有兼容性或生命周期保护触发'),
    (r'FX3_FILE103_READY_FAILED|FX3_OSD_ALLOC_DEADLINE_END|unfetched', 'TRY2 guest readiness or frame failure'),
    (r'FX3_GPE_CMD [^\n]* result=[1-9][0-9]* ', '遇到当前绘制模型不支持的命令'),
]
KEEP = re.compile(r'FX3_KEY_INPUT_RECV|FX3_AP89_SCREEN_OPEN_ENTER|FX3_MEDIA_START_BRANCH|FX3_MEDIA_NOTIFY|FX3_RM_NATIVE_FREE|FX3_KEY96_READY|FRONT_FULL_BODY|raw=02000007000000 |FX3_SYNTH_KEY |FX3_AP101_NATIVE_LOAD_READBACK_WINDOW_BEGIN|FX3_FILE100_NATIVE_FILE_READ generation=1 |FX3_AP_NATURAL_BOOTIN_BEGIN|FX3_BACKUP_INSMOD_RC=0|FX3_FILE100_OBSERVER_READY|FX3_KEY95_STEP_DONE|FX3_SYNC100_BACKEND_BOUND|FX3_FILE103_READY_CONFIRMED')


class FullLogMonitor:
    def __init__(self, path, markers=()):
        self.path = path
        self.offset = 0
        self.partial = ''
        self.overlap = ''
        self.selected = []
        self.markers = {m: False for m in markers}
        self.marker_evidence = {m: 'literal' for m in markers}
        self.date99_semantic = {name: False for name in ('worker', 'date98', 'owner', 'clock_commit')}
        self.failure = None

    def poll(self):
        if not self.path.exists():
            return ''
        with self.path.open('rb') as f:
            f.seek(self.offset)
            chunk = f.read()
            self.offset = f.tell()
        text = self.overlap + chunk.decode(errors='replace')
        for marker in self.markers:
            if marker in text:
                self.markers[marker] = True
                self.marker_evidence[marker] = 'literal'
        # Concurrent kernel printk and init-shell writes can splice the literal
        # CONSUMER_BOUND line.  Require independent intact initialization and
        # transaction receipts; never infer a bind from the worker alone.
        if 'FX3_DATE99_CONSUMER_BOUND' in self.markers and not self.markers['FX3_DATE99_CONSUMER_BOUND']:
            evidence = {
                'worker': 'FX3_DATE99_WORKER_READY serialized=1',
                'date98': 'FX3_DATE98_KERNEL_OBSERVE_READY consumer99_replaces_passive_target=',
                'owner': 'FX3_BACKUP_CP_PUBLIC_OWNER exact_reset33=1 F1_then_F4_once=1 result=0',
                'clock_commit': 'FX3_DATE99_CLOCK_COMMIT transaction=',
            }
            for name, value in evidence.items():
                if value in text:
                    self.date99_semantic[name] = True
            if all(self.date99_semantic.values()):
                self.markers['FX3_DATE99_CONSUMER_BOUND'] = True
                self.marker_evidence['FX3_DATE99_CONSUMER_BOUND'] = 'semantic:worker+date98+owner0+clock_commit'
        if self.failure is None:
            for pattern, label in FAILURES:
                match = re.search(pattern, text, re.I)
                if match:
                    self.failure = label + ': ' + match[0][:300]
                    break
        self.overlap = text[-4096:]
        lines = (self.partial + chunk.decode(errors='replace')).split('\n')
        self.partial = lines.pop()
        self.selected.extend(line for line in lines if KEEP.search(line))
        return '\n'.join(self.selected)
