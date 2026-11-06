"""Bounded host-only startup evidence; never returns an admission decision.

No guest, QMP, serial-file read, sleeps, environment dump or per-poll disk write.
All observation exceptions are contained. Token offsets use raw new bytes only.
"""
import collections
import json
import struct
import time
from pathlib import Path

MARKERS = (
 b'FX3_BACKUP_INSMOD_RC=0', b'FX3_AP101_NATIVE_LOAD_READBACK_WINDOW_BEGIN',
 b'FX3_AP_NATURAL_BOOTIN_BEGIN', b'FX3_SYNC100_BACKEND_BOUND',
 b'FX3_FILE103_READY_CONFIRMED', b'FX3_KEY96_READY',
 b'FX3_AP89_SCREEN_OPEN_ENTER ', b'FX3_AP89_SCREEN_CREATE ',
 b'FX3_UI_CONFIG_DONE ', b'FX3_TIMER_ENTRY ', b'FX3_UI_FILL_EXEC ',
 b'FX3_OSD_HEADLESS_COPY ', b'FX3_OSD_FRAME_TARGET_VALID ', b'FX3_OSD102_COMMIT ',
)
PREDICATES = ('phaseA_unobserved','replay_input_verified','screen_open_observed',
 'validated_ring_present','screen_quiet_10s','media_branches_exact',
 'media_notifications_exact','native_free_sizes_present','key96_ready',
 'front_full_body','expected_raw_message','last_screen_allowed','nonuniform_pixels')
TAIL = max(map(len, MARKERS))-1
MAX_BYTES = 256*1024

class Changes:
    """Fixed initial/first-kind/last plus a bounded recent transition deque."""
    def __init__(self, limit):
        self.initial = self.last = None
        self.recent = collections.deque(maxlen=limit)
        self.first_kind = {}
        self.count = self.transitions = self.evicted = self.first_kind_omitted = 0
        self.key = None
    def add(self, key, row):
        self.count += 1
        if self.initial is None: self.initial = row
        if key != self.key:
            self.transitions += 1
            if len(self.recent)==self.recent.maxlen: self.evicted += 1
            self.recent.append(row)
            if key not in self.first_kind:
                if len(self.first_kind)<32: self.first_kind[key]=row
                else: self.first_kind_omitted += 1
        self.key, self.last = key, row
    def data(self):
        return {'observations':self.count,'transitions':self.transitions,
          'recent_limit':self.recent.maxlen,'evicted_transitions':self.evicted,
          'first_kind_omitted':self.first_kind_omitted,'initial':self.initial,
          'first_kinds':list(self.first_kind.values()),'recent':list(self.recent),'last':self.last}

class StartupObservation:
    def __init__(self, run, *, clock=time.monotonic_ns):
        self.path = Path(run)/'startup-observation.json'
        self.clock = clock
        self.stage = 'startup'
        self.serial_offset = self.serial_chunks = self.serial_bytes = 0
        self.carry = b''
        self.markers = {}
        self.header = Changes(48)
        self.ready = Changes(32)
        self.phases = Changes(8)
        self.errors = collections.Counter()
        self.header_counts = collections.Counter()
        self.active_ready = None
        self.flush_attempted = self.saved = False
        self.phase('startup')
    def _error(self, area):
        self.errors[area] += 1 # fixed caller labels, no exception text or environment
    def stamp(self):
        try: return self.clock()
        except Exception: self._error('clock'); return None
    def phase(self, stage):
        try:
            self.stage=stage
            self.phases.add(stage,{'stage':stage,'host_received_ns':self.clock(),'serial_offset':self.serial_offset})
        except Exception: self._error('phase')
    def serial_chunk(self, start, chunk, end):
        try:
            received=self.clock(); self.serial_chunks+=1; self.serial_bytes+=len(chunk)
            # A gap cannot join two unrelated byte spans into a fictitious token.
            if start!=self.serial_offset: self._error('serial_gap');self.carry=b''
            prefix=self.carry+chunk[:TAIL] # <=2*TAIL transient; no full chunk copy
            origin=start-len(self.carry)
            for token in MARKERS:
                name=token.decode('ascii')
                if name not in self.markers:
                    a=prefix.find(token)
                    b=chunk.find(token)
                    offsets=([origin+a] if a>=0 else [])+([start+b] if b>=0 else [])
                    if offsets:
                        off=min(offsets)
                        self.markers[name]={'byte_offset':off,'token_bytes':len(token),
                          'host_first_complete_token_received_ns':received,
                          'serial_chunk_start':start,'serial_chunk_end':end,'stage':self.stage,
                          'line_complete_received_ns':None,
                          'semantics':'first complete literal token; no guest occurrence time or full record/semantic acceptance claim'}
                row=self.markers.get(name)
                if row is not None and row['line_complete_received_ns'] is None:
                    at=max(0,row['byte_offset']+row['token_bytes']-start)
                    if chunk.find(b'\n',at)>=0:row['line_complete_received_ns']=received
            self.carry=chunk[-TAIL:] if len(chunk)>=TAIL else (self.carry+chunk)[-TAIL:]
            self.serial_offset=end
        except Exception: self._error('serial')
    def header_read(self, *, before_ns, after_ns, request_id_before, request_id_after,
                    returned, file_length, prefix, source, outcome, exception_type=None):
        try:
            words=list(struct.unpack_from('<16Q',prefix)) if prefix is not None and len(prefix)>=128 else None
            if outcome!='returned': kind=outcome
            elif len(returned)!=256: kind='short' if file_length is None or file_length<256 else 'wrong_length'
            elif words[0]!=0x32474e495244534f: kind='bad_magic'
            elif words[1]!=2: kind='bad_version'
            elif words[4]==0: kind='valid_seq0'
            else: kind='valid_positive'
            self.header_counts[kind]+=1
            row={'kind':kind,'stage':self.stage,'serial_offset':self.serial_offset,
              'host_read_before_ns':before_ns,'host_read_after_ns':after_ns,
              'request_id_before':request_id_before,'request_id_after':request_id_after,
              'request_id':request_id_after if isinstance(request_id_after,int) and isinstance(request_id_before,int) and request_id_after>request_id_before else None,
              'returned_length':len(returned),'file_length_at_original_gate':file_length,
              'raw_16Q':words,'words_source':source,'exception_type':exception_type,
              'semantics':'host read observation only; no guest/server/browser atomic claim'}
            self.header.add(self.stage+':'+kind,row)
        except Exception: self._error('header')
    def begin_ready(self):
        try:
            self.active_ready={'predicates':{k:'not_evaluated' for k in PREDICATES},'evaluation_complete':False}
        except Exception: self._error('ready_begin')
    def predicate(self, name, value):
        # Return the very same value object: the original BoolOp owns truth testing.
        try:
            t=type(value)
            observed=value if t is bool else bool(len(value)) if t in (dict,list,tuple,str,bytes) else value is not None if value is None else 'unknown_type'
            if self.active_ready is not None and name in PREDICATES:self.active_ready['predicates'][name]=observed
        except Exception: self._error('predicate')
        return value
    def end_ready(self, *, qualified, last_screen_observed_at, frame):
        try:
            row=self.active_ready
            row.update(evaluation_complete=True,stage=self.stage,host_received_ns=self.clock(),
                serial_offset=self.serial_offset,last_screen_observed_host_monotonic=last_screen_observed_at,
                qualified=qualified,validated_ring_identity=self._frame(frame))
            key=self.stage+':'+str(tuple(row['predicates'].values()))+':'+str(qualified)
            self.ready.add(key,row);self.active_ready=None
        except Exception: self._error('ready_end')
    @staticmethod
    def _frame(frame):
        if type(frame) is not dict:return None
        return {k:frame.get(k) for k in ('sequence','epoch','PNG_sha256','pixel_source_sequence','host_monotonic')}
    def status(self):
        return {'schema':'fx3-startup-observation-r30-v1','path':str(self.path),
          'flush_attempted':self.flush_attempted,'saved':self.saved,'errors':dict(self.errors)}
    def data(self):
        return {**self.status(),'stage':self.stage,'limits':{'header_recent':48,'ready_recent':32,'phase_recent':8,
          'first_kind_per_stream':32,'marker_whitelist':len(MARKERS),'serial_carry_bytes':TAIL,'file_bytes':MAX_BYTES},
          'header_counts':dict(self.header_counts),'headers':self.header.data(),'ready':self.ready.data(),
          'phases':self.phases.data(),'markers':self.markers,'ready_incomplete':self.active_ready,
          'serial':{'chunks':self.serial_chunks,'bytes':self.serial_bytes,'consumed_offset':self.serial_offset,'carry_bytes':len(self.carry)},
          'write_policy':'one bounded replace after original cleanup; no fsync/poll writes; abrupt host death may lose all observation evidence'}
    def flush(self):
        if self.flush_attempted:return
        self.flush_attempted=True
        try:
            self.phase('after_cleanup')
            value=self.data();value['saved']=True
            raw=(json.dumps(value,separators=(',',':'))+'\n').encode()
            if len(raw)>MAX_BYTES:
                self._error('serialization_limit')
                # Explicitly retain first/last/boundaries and drop recent transition arrays.
                value=self.data();value['saved']=True;value['serialization_truncated']=True
                for name in ('headers','ready','phases'):
                    stream=value[name];stream['serialization_omitted_recent']=len(stream['recent']);stream['recent']=[]
                raw=(json.dumps(value,separators=(',',':'))+'\n').encode()
            if len(raw)>MAX_BYTES:raise ValueError('bounded_observation_limit')
            temp=self.path.with_suffix('.json.tmp');temp.write_bytes(raw);temp.replace(self.path)
            self.saved=True
        except Exception:self._error('write')
