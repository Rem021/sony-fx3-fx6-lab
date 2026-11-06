"""Original-word-gated byte transcription, NOT execution of ELF functions.
No stub supplies a branch result: changed-counter is an explicit fixture precondition.
The finite scalar cases do not claim that these values were observed at runtime.
"""
import sys
sys.dont_write_bytecode = True
import struct, json
from trace import E, H, sha
from record_subset import convert_record_timer, project_fx6_record_message, UnsupportedRecord

def word(k, pc):
    return int.from_bytes(bytes.fromhex(E[k].mapping(pc)['bytes_le']), 'little')

def movz(k, pc, rd):
    w = word(k, pc)
    assert w & 0x7f800000 == 0x52800000 and w & 31 == rd and (w >> 21) & 3 == 0
    return (w >> 5) & 0xffff

def store_offset(k, pc, rt, rn, byte=False):
    w = word(k, pc)
    assert w & 0xffc00000 == (0x39000000 if byte else 0xb9000000)
    assert w & 31 == rt and (w >> 5) & 31 == rn
    return ((w >> 10) & 0xfff) * (1 if byte else 4)

def producer_record(k, previous, counter, rec_fps, imaging_fps):
    # Transcribe only the established changed-counter path, not Codec execution.
    assert counter != previous and all(0 <= x <= 0xffffffff for x in (previous,counter,rec_fps,imaging_fps))
    a = {'fx3_mpr': (0xb5364,0xb5028,0xb3e20,0xb3e24,0xb3e28,0xb3e38,0xb3e48),
         'fx6_mpr': (0x129c2c,0x1286c4,0x128434,0x128438,0x12843c,0x12844c,0x12845c)}[k]
    size,header,one,fc,flag,fps,imaging = a
    p = bytearray(movz(k,size,0))
    struct.pack_into('<I',p,0,movz(k,header,1))
    p[store_offset(k,flag,1,19,True)] = movz(k,one,1)
    for pc,rt,value in ((fc,0,counter),(fps,1,rec_fps),(imaging,1,imaging_fps)):
        struct.pack_into('<I',p,store_offset(k,pc,rt,19),value)
    return bytes(p)

def run():
    # Original consumer words tie the projection to loads/stores, not symbol names.
    expected = {0x212b73c:0xd2800200,0x212b744:0x52801d82,
                0x212b74c:0xb9400a62,0x212b750:0xb9000402,
                0x212b754:0xb9400e62,0x212b758:0xb9000802,
                0x212b75c:0xb9401262,0x212b760:0xb9000c02}
    for pc,w in expected.items(): assert word('fx6_ap',pc)==w
    positives=[]
    for previous,counter,fps,imaging in ((0,1,300000,300000),(99,100,239760,599400),
                                        (0xffffffff,0,0,0),(0,0xffffffff,0xffffffff,0xffffffff)):
        raw=producer_record('fx3_mpr',previous,counter,fps,imaging)
        native=producer_record('fx6_mpr',previous,counter,fps,imaging)
        before=sha(raw); converted=convert_record_timer(raw)
        assert converted==native and sha(raw)==before
        assert project_fx6_record_message(converted)==struct.pack('<4I',0xec,fps,imaging,counter)
        assert [i for i in range(60) if converted[i]!=raw[i]]==[0]
        positives.append({'condition':'counter differs; only record-time writer modifies zeroed timer record',
                          'previous':previous,'counter':counter,'record_fps_x10000':fps,'imaging_fps_x10000':imaging,
                          'fx3_hex':raw.hex(),'fx6_native_hex':native.hex(),'fx3_sha256':before,
                          'fx6_sha256':sha(native),'ap_message_hex':project_fx6_record_message(converted).hex()})
    base=bytes.fromhex(positives[0]['fx3_hex']);bad=[('short',base[:-1]),('long',base+b'\0'),('mutable',bytearray(base))]
    for name,offset,value in [('wrong_event',0,0x26),('unchanged_counter_flag',4,0),('noncanonical_flag',4,2),
                               ('padding',5,1),('playback',0x14,1),('audio_record',0x24,1),('audio_playback',0x30,1),
                               ('hidden_playback_scalar',0x18,1),('tail_unknown',59,1)]:
        p=bytearray(base);p[offset]=value;bad.append((name,bytes(p)))
    rejected=[]
    for name,p in bad:
        try:convert_record_timer(p)
        except UnsupportedRecord as e:rejected.append({'case':name,'error':str(e)})
        else:raise AssertionError(name+' must reject')
    result={'kind':'word-gated byte semantics; synthetic fixtures, not observed events',
            'original_elf_execution':False,'stubs':[], 'positive_cases':positives,'rejected_cases':rejected,
            'not_proven':['event occurs during Init','runtime callback binding','valid live memory size/provenance',
                          'playback/audio semantics','AP downstream message release']}
    (H/'fixture-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'positive':len(positives),'rejected':len(rejected),'stubs':0}))
    return result
if __name__=='__main__':run()
