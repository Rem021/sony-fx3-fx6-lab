#!/usr/bin/env python3
"""Original file-header selection and RAM-reuse state producer, isolated ARM64."""
import hashlib,importlib.util,json,struct,sys
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;TASK=HERE.parent;PREVIOUS=TASK/'config-producer-20261029'
receipt=PREVIOUS/'final-receipt.json'
assert hashlib.sha256(receipt.read_bytes()).hexdigest()=='581d993c194df656a3327c80090320dcaf1408daeee48d7f2037aa1a338bf9b8'
helper=PREVIOUS/'nor_descriptor_guest.py';manifest=json.loads(receipt.read_text())
pin=next(x for x in manifest['files'] if x['path']==helper.name)
assert hashlib.sha256(helper.read_bytes()).hexdigest()==pin['sha256']
spec=importlib.util.spec_from_file_location('prior_NOR_RAM_guest',helper)
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
R=old.R;STATE=0xfe26c300;LOAD=0xfe208000;HEADER2=0x100400000
class Guest(old.Guest):
    def __init__(self,raw,record):
        super().__init__(raw,record)
        self.u.mem_map(STATE&~4095,4096);self.state_known=bytearray(12)
        self.u.mem_map(LOAD,0x3000);self.load_known=bytearray(0x3000)
        self.u.mem_map(HEADER2,4096,old.UC_PROT_READ);self.u.mem_write(HEADER2,record[:256])
        self.stop_points={};self.helper_results=[]
    def read(self,u,access,at,size,value,user):
        if STATE<=at and at+size<=STATE+12:
            if 0 in self.state_known[at-STATE:at-STATE+size]:self.stop('before_unknown_backup_state_read',address=hex(at),bytes=size)
            return
        if LOAD<=at and at+size<=LOAD+0x3000:
            if 0 in self.load_known[at-LOAD:at-LOAD+size]:self.stop('before_unknown_load_buffer_read',address=hex(at),bytes=size)
            return
        if HEADER2<=at and at+size<=HEADER2+256:return
        super().read(u,access,at,size,value,user)
    def write(self,u,access,at,size,value,user):
        if STATE<=at and at+size<=STATE+12:
            self.state_known[at-STATE:at-STATE+size]=b'\1'*size;self.writes+=1;return
        if LOAD<=at and at+size<=LOAD+0x3000:
            self.load_known[at-LOAD:at-LOAD+size]=b'\1'*size;self.writes+=1;return
        if 0xfe0625e0<=at and at+size<=0xfe0625e8:
            self.initialized[at-old.BASE:at-old.BASE+size]=b'\1'*size;self.writes+=1;return
        super().write(u,access,at,size,value,user)
    def code(self,u,pc,size,user):
        if pc in self.stop_points:self.stop(self.stop_points[pc]);return
        if pc in [0xfe058d48,0xfe058d50]:
            self.helper_results.append(dict(PC=hex(pc),X0=hex(u.reg_read(R.UC_ARM64_REG_X0))))
        super().code(u,pc,size,user)
    def words(self,address,n=3):return list(struct.unpack('<'+'I'*n,bytes(self.u.mem_read(address,n*4))))
def inputs():
    raw=(PREVIOUS/'original-files/loader_nor.bin').read_bytes();assert hashlib.sha256(raw).hexdigest()==old.PIN
    source=json.loads((PREVIOUS/'load-descriptor-sources.json').read_text())
    bank=next(t for t in source['templates'] if t['member']==source['canonical_template'])['banks'][1]
    record=(TASK/'dmm-backup-20261029/original-records/canonical-bank1.bin').read_bytes()
    assert hashlib.sha256(record).hexdigest()==bank['record_sha256']
    return raw,record,source,bank
def main():
    out=HERE/'backup-selection-state-results.json';assert not out.exists()
    raw,record,source,bank=inputs()
    g=Guest(raw,record)
    check=g.call(0xfe04c76c,[old.BACKUP])
    strict_file_choice=g.call(0xfe04c7a8,[old.BACKUP,HEADER2])
    relaxed_choice=g.call(0xfe04d584,[old.BACKUP,HEADER2,0])
    no_headers=g.call(0xfe04c7a8,[0,0])
    assert check['registers'][0]=='0xfffffffa'
    assert strict_file_choice['registers'][0]==no_headers['registers'][0]=='0xffffffff'
    assert relaxed_choice['registers'][0]=='0x2'
    fresh=Guest(raw,record)
    strict_configuration=fresh.call(0xfe0545dc,[0x0c000000,old.OUT+0x3000])
    assert strict_configuration['boundary']['reason']=='before_unknown_backup_state_read'
    g=Guest(raw,record)
    initialization_prefix=g.call(0xfe058adc)
    assert initialization_prefix['boundary']['address']=='0xfe040110'
    assert g.words(STATE)==[0,0,0] and all(g.state_known)
    # Explicit independent post-lookup RAM-reuse fragment. Its input pointer
    # and context register match the original instructions before this entry;
    # real boot handoff, FA0006 lookup and logging are not supplied as successful.
    g.u.reg_write(R.UC_ARM64_REG_X19,old.BACKUP);g.u.reg_write(R.UC_ARM64_REG_X22,STATE)
    g.stop_points={0xfe058dfc:'after_original_RAM_reuse_state_write_before_exit'}
    reuse=g.call(0xfe058d40)
    assert reuse['boundary']['PC']=='0xfe058dfc' and g.words(STATE)[0]==3
    assert g.helper_results==[dict(PC='0xfe058d48',X0='0xfffffffa'),dict(PC='0xfe058d50',X0='0x0')]
    ready_state=g.words(STATE)
    g.stop_points={}
    wrapped=g.call(0xfe058b7c,[0xfa0080,old.OUT])
    expected=(PREVIOUS/bank['saved_payload']).read_bytes()
    assert wrapped['boundary']['reason']=='returned' and wrapped['registers'][0]=='0x2400'
    assert bytes(g.u.mem_read(old.OUT,9216))==expected
    after_query_state=g.words(STATE)
    g.stop_points={0xfe0561b4:'before_original_diagnostic_output'}
    configuration=g.call(0xfe0545dc,[0x0c000000,old.OUT+0x3000])
    assert configuration['boundary']['PC']=='0xfe0561b4'
    assert all(g.load_known[:9216]) and not any(g.load_known[9216:])
    copied=bytes(g.u.mem_read(LOAD,9216));assert copied==expected
    result=dict(NOR_sha256=old.PIN,original_record_sha256=bank['record_sha256'],
        original_header=dict(word4=hex(struct.unpack_from('<I',record,4)[0]),byte8=record[8],word2c=struct.unpack_from('<I',record,0x2c)[0]),
        header_checker=check,strict_file_header_choice=strict_file_choice,
        relaxed_helper_choice=relaxed_choice,no_headers=no_headers,
        header_input_scope='Both chooser inputs are explicitly the same original CP template header copied into separate RAM locations, not real primary and backup files.',
        strict_whole_configuration_without_state=strict_configuration,
        original_state_initializer_prefix=initialization_prefix,initializer_prefix_state_words=[0,0,0],
        independent_original_RAM_reuse_fragment=reuse,original_helper_returns=g.helper_results,
        original_RAM_reuse_state_words=ready_state,original_wrapped_parameter_query=wrapped,
        post_query_state_words=after_query_state,
        original_configuration_entry_after_fragment=configuration,original_configuration_load_buffer=hex(LOAD),
        copied_original_table_bytes=9216,copied_original_table_sha256=hashlib.sha256(copied).hexdigest(),
        load_buffer_tail_unknown_bytes_not_claimed=0x3000-9216,
        scope='Only bounded original ARM64 instructions in RAM. The state3 write is original code, not a supplied ready value, but its RAM-reuse fragment starts after unresolved normal lookup/handoff/logging. The original precheck return is observed as -6 and is not consumed before the separate BK4-marker initializer returns0. No complete normal startup, actual storage/file bytes at DMM target, CPU/cache/TLB maintenance, native Sony program, camera or USB operation.')
    out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(header=result['original_header'],checker=check['registers'][0],strict_choice=strict_file_choice['registers'][0],
        relaxed_choice=relaxed_choice['registers'][0],initializer=initialization_prefix['boundary'],reuse=reuse['boundary'],
        ready_state=ready_state,wrapped_query=wrapped['registers'][0],configuration=configuration['boundary'],copied_bytes=9216)))
if __name__=='__main__':main()
