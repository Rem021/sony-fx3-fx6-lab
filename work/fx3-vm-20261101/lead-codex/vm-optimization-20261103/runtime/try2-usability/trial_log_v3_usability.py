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
        self.marker_evidence = {m: {'method': 'not_observed'} for m in markers}
        self.date99_semantic = {name: False for name in ('worker', 'date98', 'owner')}
        self.date99_transactions = {'accept': set(), 'commit': {}, 'retired': {}}
        self.date99_rejected = False
        self.native_shutdown_events = []
        self.native_power_off_events = []
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
                self.marker_evidence[marker] = {'method': 'literal', 'marker': marker}
        # Concurrent kernel printk and init-shell writes can splice the literal
        # CONSUMER_BOUND line.  Require independent intact initialization and
        # transaction receipts; never infer a bind from the worker alone.
        self.date99_rejected |= bool(re.search(r'FX3_DATE99_REJECT', text))
        if self.date99_rejected and self.marker_evidence.get('FX3_DATE99_CONSUMER_BOUND', {}).get('method') == 'semantic_after_interleaved_literal':
            self.markers['FX3_DATE99_CONSUMER_BOUND'] = False
            self.marker_evidence['FX3_DATE99_CONSUMER_BOUND'] = {'method': 'semantic_invalidated_by_reject'}
        if 'FX3_DATE99_CONSUMER_BOUND' in self.markers and not self.markers['FX3_DATE99_CONSUMER_BOUND']:
            evidence = {
                'worker': 'FX3_DATE99_WORKER_READY serialized=1',
                'date98': 'FX3_DATE98_KERNEL_OBSERVE_READY consumer99_replaces_passive_target=',
                'owner': 'FX3_BACKUP_CP_PUBLIC_OWNER exact_reset33=1 F1_then_F4_once=1 result=0',
            }
            for name, value in evidence.items():
                if value in text:
                    self.date99_semantic[name] = True
            for match in re.finditer(r'FX3_DATE99_ACCEPT transaction=(\d+) reason=(\d+) source=0x809005c5', text):
                self.date99_transactions['accept'].add((int(match[1]), int(match[2])))
            for match in re.finditer(r'FX3_DATE99_CLOCK_COMMIT transaction=(\d+) generation=(\d+) reason=(\d+) valid_UTC=1[^\n]*readback_UTC_ms=(-?\d+) software_clock_advances=1', text):
                self.date99_transactions['commit'][(int(match[1]), int(match[3]))] = {'generation': int(match[2]), 'readback_UTC_ms': int(match[4])}
            for match in re.finditer(r'FX3_DATE99_RETIRED transaction=(\d+) reason=(\d+) result=0 native_request_free=0[^\n]*generation=(\d+)', text):
                self.date99_transactions['retired'][(int(match[1]), int(match[2]))] = int(match[3])
            complete = [((tid, reason), commit) for (tid, reason), commit in self.date99_transactions['commit'].items()
                        if (tid, reason) in self.date99_transactions['accept']
                        and self.date99_transactions['retired'].get((tid, reason)) == commit['generation']]
            if all(self.date99_semantic.values()) and complete and not self.date99_rejected:
                transaction, commit = complete[0]
                self.markers['FX3_DATE99_CONSUMER_BOUND'] = True
                self.marker_evidence['FX3_DATE99_CONSUMER_BOUND'] = {
                    'method': 'semantic_after_interleaved_literal', 'worker': evidence['worker'],
                    'registered_branch': evidence['date98'], 'owner_result': evidence['owner'],
                    'transaction': transaction[0], 'reason': transaction[1],
                    'generation': commit['generation'], 'readback_UTC_ms': commit['readback_UTC_ms'],
                    'retired_result': 0, 'native_request_free': 0}
        if self.failure is None:
            for pattern, label in FAILURES:
                match = re.search(pattern, text, re.I)
                if match:
                    self.failure = label + ': ' + match[0][:300]
                    break
        self.overlap = text[-4096:]
        lines = (self.partial + chunk.decode(errors='replace')).split('\n')
        self.partial = lines.pop()
        self.native_shutdown_events.extend(line.strip() for line in lines
                                           if re.search(r'open screen: [^\r\n]* -> scr0039_shutdown', line))
        self.native_power_off_events.extend(line.strip() for line in lines
                                            if re.search(r'FX3_BOOT_QUEUE_SEND[^\r\n]*source=0x830128 raw=2c000300', line))
        self.selected.extend(line for line in lines if KEEP.search(line))
        return '\n'.join(self.selected)

    def date99_raw_receipt(self):
        """Source byte ranges, with a missing literal kept distinct from proof."""
        data = self.path.read_bytes()
        pats = {
            'literal_consumer_bound': rb'FX3_DATE99_CONSUMER_BOUND',
            'worker': rb'FX3_DATE99_WORKER_READY serialized=1[^\r\n]*',
            'registered_branch': rb'FX3_DATE98_KERNEL_OBSERVE_READY consumer99_replaces_passive_target=[^\r\n]*',
            'owner_result_zero': rb'FX3_BACKUP_CP_PUBLIC_OWNER exact_reset33=1 F1_then_F4_once=1 result=0[^\r\n]*',
            'accept': rb'FX3_DATE99_ACCEPT transaction=1 reason=4 source=0x809005c5[^\r\n]*',
            'clock_commit': rb'FX3_DATE99_CLOCK_COMMIT transaction=1 generation=1 reason=4 valid_UTC=1[^\r\n]*',
            'retired': rb'FX3_DATE99_RETIRED transaction=1 reason=4 result=0 native_request_free=0[^\r\n]*',
            'reject': rb'FX3_DATE99_REJECT[^\r\n]*',
        }
        out = {}
        for name, pat in pats.items():
            m = re.search(pat, data)
            out[name] = None if m is None else {'serial_byte_range': [m.start(), m.end()],
                                                  'raw': m[0].decode(errors='replace')}
        out['literal_present'] = out['literal_consumer_bound'] is not None
        out['semantic_evidence'] = self.marker_evidence.get('FX3_DATE99_CONSUMER_BOUND')
        return out
