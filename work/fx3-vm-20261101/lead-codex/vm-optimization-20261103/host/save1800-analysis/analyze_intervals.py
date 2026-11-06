"""Read-only extraction of same-clock GPE intervals and approximate host anchors."""
import hashlib
import json
import re
from pathlib import Path

HERE=Path(__file__).resolve().parent
RUN=HERE.parents[1]/'runtime/runs/vmopt-20261103-save1800-836febd8'
SERIAL=RUN/'serial.log'
SHA='54dd1237d678dfd5aa2cd03d0b087a5a45a438d69ab63c7365c587a6272270ec'


def value(line,name):
    match=re.search(r'(?<![A-Za-z])'+re.escape(name)+r'=([^ ]+)',line)
    return match.group(1) if match else None


def main():
    raw=SERIAL.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==SHA
    text=raw.decode(errors='replace')
    allocations={};events={6329:{},7545:{}};keys={}
    for line in text.splitlines():
        if 'FX3_GPE104_DYNAMIC_RETURN' in line and 'flags=0x2a' in line and 'module=0x82' in line and 'result=0' in line:
            allocations[value(line,'QID')]={'ns':int(value(line,'ns')),'event':value(line,'event')}
        if 'FX3_SYNTH_KEY step=' in line and 'status=1 ' in line:
            step=value(line,'step');stamp=value(line,'monotonic_ns')
            if step and stamp:keys[int(step)]=int(stamp)/1e9
        seq=value(line,'seq') if 'FX3_GPE104_' in line else None
        if seq and int(seq) in events:
            event=events[int(seq)]
            if 'FX3_GPE104_COMPLETE_ENTER' in line:
                event['qid']=value(line,'completion_source');event['enter_ns']=int(value(line,'ns'))
                event['allocation']=dict(allocations[event['qid']])
            elif 'FX3_GPE104_COMPLETE_RETURN' in line:
                event['complete_ns']=int(value(line,'ns'));event['complete_result']=value(line,'result')
            elif 'FX3_GPE104_CMD_RETURN' in line and value(line,'op')=='4':
                event['cmd_return_ns']=int(value(line,'ns'))
    gates={x['step']:x['host_monotonic'] for x in json.loads((RUN/'ap101-host-input-gate.json').read_text())}
    qmp=[x for x in json.loads((RUN/'qmp.json').read_text()) if 'request' in x]
    # Step 1 and 19 write gates match the immediately preceding QMP stop.
    run_start=gates[19]-1247.2627000419889
    def estimate(guest_s,low,high):
        def pair(step):return (keys[step],gates[step]-run_start)
        x0,y0=pair(low);x1,y1=pair(high)
        return y0+(guest_s-x0)*(y1-y0)/(x1-x0)
    out=[]
    for seq,low,high in [(6329,16,17),(7545,18,19)]:
        row=events[seq];a=row.pop('allocation');row['allocate_ns']=a['ns'];row['alloc_event']=a['event']
        row['alloc_to_enter_ms']=(row['enter_ns']-a['ns'])/1e6
        row['enter_to_complete_ms']=(row['complete_ns']-row['enter_ns'])/1e6
        row['alloc_to_complete_ms']=(row['complete_ns']-a['ns'])/1e6
        row['complete_to_cmd_return_ms']=(row['cmd_return_ns']-row['complete_ns'])/1e6
        lo=estimate(a['ns']/1e9,low,high);hi=estimate(row['complete_ns']/1e9,low,high)
        row['estimated_host_elapsed_s']=[round(lo,3),round(hi,3)]
        row['host_mapping']='linear interpolation between host InputGate and guest key-down observations; approximate, no common clock proof'
        nearby=[]
        for event in qmp:
            t=event['elapsed_seconds']
            if lo-1<=t<=hi+1:
                req=event['request'];command=req['execute'];arg=req.get('arguments',{}).get('command-line','')
                nearby.append({'elapsed_s':round(t,6),'command':command,'hmp_file':arg.split('/')[-1].rstrip('"') if 'pmemsave ' in arg else None})
        row['nearby_qmp_requests']=nearby
        out.append({'seq':seq,**row})
    result={'serial_sha256':SHA,'serial_bytes':len(raw),'host_start_monotonic_from_step19':run_start,
            'intervals':out,'kernel_error_separate_clock':'[38320.919593] is printk kernel time; not subtracted from user ns or QMP elapsed'}
    (HERE/'intervals.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
