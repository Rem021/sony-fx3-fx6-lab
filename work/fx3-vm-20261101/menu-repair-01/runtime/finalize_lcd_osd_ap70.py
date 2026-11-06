from pathlib import Path
import json,re,hashlib,fcntl,os,datetime
R=Path(__file__).resolve().parent;root=R.parents[3];run=R/'runs/ap70lcd-f61554d9';v=json.loads((run/'receipt.json').read_text());lines=(run/'serial.log').read_text(errors='replace').split('\n');start=next(i for i,l in enumerate(lines) if 'FX3_LCD_BRIGHTNESS_COMMIT' in l);prev='未捕获';caller='';stack=[];tid=None;rows=[]
for i,l in enumerate(lines):
 m=re.search(r'\[\s*(\d+\.\d+)\]',l)
 if m:prev=m[1]
 if 'FX3_PROFILE_STACK_BEGIN' in l:stack=[];tid=int(re.search(r'tid=(\d+)',l)[1])
 if 'FX3_PROFILE_FRAME' in l:stack.append(l.strip())
 if 'FX3_PROVIDER_CALLER' in l:caller=l.strip()
 if 'FX3_PROVIDER_REQUEST' not in l or i<start:continue
 d=dict(re.findall(r'(destination|bytes|source|caller|raw)=(\S+)',l));d.update(line=i+1,guest_time_previous_log=prev,caller_module=caller,stack=list(stack),tid=tid)
 d['wait_type']='同步: send_and_wait_cmp_i +0x2de70a8' if 'relative=0x2de7264' in caller else '无需回复: send_no_wait_i +0x2de83b4' if 'relative=0x2de8550' in caller else '无需回复: +0x2de66f4, snd+0x2de6880后直接返回' if 'relative=0x2de6884' in caller else '未审计'
 raw=bytes.fromhex(d['raw']);d['command']=hex(int.from_bytes(raw[2:4],'little'));rows.append(d)
base=(R/'runs/ap69audio-1cbbef9f/serial.log').read_text(errors='replace').split('\n')
def key(l):
 m=re.search(r'target=(\S+).*tag1=(\S+)',l);return m.groups() if m else None
old={key(l) for l in base if 'FX3_UIPC_SEND_UNIQUE' in l};seen=set();other=[]
for i,l in enumerate(lines):
 if i<start or 'FX3_UIPC_SEND_UNIQUE' not in l:continue
 k=key(l)
 if k not in old and k not in seen:other.append(dict(line=i+1,text=l.strip(),classification='仅被动差集，含回复/动态queue；不可当新服务请求'));seen.add(k)
locks=[]
for p in [R/'.run.lock',root/'outputs/fx3-vm/.run.lock']:
 with p.open('rb') as f:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(f,fcntl.LOCK_UN)
 locks.append(dict(path=str(p),reacquire_and_release=True))
try:os.kill(v['qemu_pid'],0);pid_absent=False
except ProcessLookupError:pid_absent=True
missing=[k for k,x in v['markers'].items() if not x];assert not missing and v['qemu_exit']==0 and v['process_reaped'] and v['inputs_unchanged'] and pid_absent
proof=json.loads((root/'work/fx3-vm-20261101/lead-claude/audits/vdf011a-0159/vdf011a-0159-proof.json').read_text());originals=[]
for p,x in proof['sources'].items():
 p=root/p
 if p.name not in ('appFw.so','cpapp-b.bin'):continue
 sha=hashlib.sha256(p.read_bytes()).hexdigest();assert sha==x['sha256'];originals.append(dict(path=str(p),sha256=sha,unchanged=True))
summary={k:v[k] for k in ['candidate','candidate_sha256','run','requested_seconds','duration_seconds','qemu_exit','process_reaped','inputs_unchanged','host_observer_error','guest_exception_markers']};summary.update(missing_markers=missing,qemu_pid_absent=pid_absent,locks=locks,originals=originals,requests_after_11a=rows,new_uipc_keys_vs_ap69=other,hardware_complete=False,menu_verified=False)
(R/'lcd-osd-ap70-run-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
report=root/'reports/2026-11-01-fx3-vm-resumed-repair/ap70-lcd-osd.md'
text='''# AP70：LCD 亮度软件接受与 OSD 静默接受

AP70 通过 80 秒运行及收尾核验，解除 TID334 的 0x11a 等待点；原 0x111a 被消费并释放 result=0，随后发送 0x429、0x500。0x159 接受 mask7 且不发送回复。仍无菜单或硬件完成验收。

动态栈修正：本次实际为 `sequence_display_setup::set_lcd_brightness()`（函数名字符串 VA 0x3922a98），经 appFw+0x2b8b488 → +0x2dcfd94 → +0x2dea398 → send_and_wait_cmp_i(+0x2de70a8)，不是已证明执行独立的 `sequence_set_lcd_brightness::run()`。原 +0x2b8b650..+0x2b8b69c 引用 BACK_LIGHT_MODE 字符串 VA 0x39226c6 并调用 +0x2de0094；运行在 0x111a 释放之后，TID334 向 0x5503e0 发 tag1=0x300f6，再发送 0x429/0x500，证明同一亮度设置路径已越过 BACK_LIGHT_MODE 后续点。不能将特定 sequence 名称的先前静态猜测冒充动态证据。

实现 v25 从 v24 插入生成：0x11a 仅接受完整14B `0d201a010e000180010e000e0600`，保留payload、selector1/brightness6、pending_hardware=1，向来源回12B `0d201a110c00018000000000`，成功释放请求；分配失败不改状态、发送失败回滚状态并释放新回复，未知值拒绝不回复。0x159 仅接受固定10B头、padding0、mask3或7，保存4B legacy payload、pending_f030=1，释放请求且不分配/发送回复。标记均明确 physical_complete=0。

ASan/UBSan 宿主检查通过（含已有模型回归、24000次锁检查）：LCD正例、原回复字节/租约释放、发送失败回滚、分配失败、14个字段逐字节变异和长度拒绝；OSD3/7、4B状态、全部其余mask、header/padding/长度拒绝及无回复断言。交叉编译、CPIO重建和DTB initrd-end更新通过。工具选项参照 [Clang ASan](https://clang.llvm.org/docs/AddressSanitizer.html) 与 [UBSan](https://clang.llvm.org/docs/UndefinedBehaviorSanitizer.html)，协议依据本机原件审计。

运行 `ap70lcd-f61554d9`：qemu_exit=0、process_reaped=true、inputs_unchanged=true、missing_markers=[]、host_observer_error=null、guest_exception_markers=[]；进程PID独立确认不存在、两把锁独立重取后释放；AP/CP原件SHA与审计proof一致。80秒已覆盖guest约458秒的0x11a，无需加长；guest时间和宿主墙钟不同。历史候选/helpers/runs保留。

## 0x11a 后的服务请求时间线

时间列为串口中最近前一条内核时间戳（秒），仅近似定位，不能当精确发送时刻。完整payload、动态栈、行号和全部UIPC差集见运行摘要；这里长包只展示前24B。所有VA为appFw相对地址；运行基址为0x7f31c73000。

|guest时间≈|目标|命令|字节/头部|等待类型|调用者 VA|
|---|---|---|---|---|---|
'''
for d in rows:
 raw=d['raw'];display=raw if len(raw)<=48 else raw[:48]+'…';rel=d['caller_module'].split('relative=')[-1]
 text+=f"|{d['guest_time_previous_log']}|{d['destination']}|{d['command']}|{d['bytes']}B `{display}`|{d['wait_type']}|+{rel}|\n"
text+='''
新增的 VDF0x429（10B `0d2029040a0001800000`）经 +0x2df2d94 调 send_no_wait_i，0x500（10B `0d2000050a0001800100`）经 +0x2df2df4 调 +0x2de66f4，该入口 +0x2de6880 只发送，正常分支 +0x2de6914..+0x2de6928 直接返回，无接收；两者虽然被未注册VDF服务丢弃，但均不是新的同步等待。未审计其功能或实现回复。其余表项在AP69已有，包含服务软件回复后续布局/plane/LUT与释放限制调用，不代表全是新阻塞。

## 仍等待的线程与观测边界

- TID319 SeqThreadPool1 最后发送 ADF0x32e/10B、source0x81cf61c2 后进入同queue接收；TID320 SeqThreadPool2 最后发送 ADF0x33d/8B、source0x81cf61c3 后进入同queue接收，caller均+0x2de7264（send_and_wait_cmp_i）。本轮仅被动保留栈，没有深挖或修改两条ADF。
- TID334 已无未回复的同步VDF请求。snapshot1记录其 S/futex_wait；这是内核睡眠快照，不能据此判定新的协议阻塞。TID322也记录 S/futex_wait，但之后继续发送布局/plane/LUT与释放限制，不能将早期快照说成最终卡死。
- snapshot2/3未再捕获匹配im.elf maps的进程，退出原因未证实；因此上述ADF为最后观测等待点，而不是通过末尾进程存活验收的线程状态。运行器的qemu_exit=0是宿主有界收尾，不是guest正常关机。
- 除0x429/0x500外的新UIPC差集含TID334到0x5503e0/tag0x300f6、TID230到0x808261c0/tag0，以及TID322到0x9059000e/tag0x81cf61c0；完整记录在摘要。后两条及其等待语义未审计，不能声明新同步阻塞，交Lead决定。

## 复核入口

- [80秒运行原回执](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap70lcd-f61554d9/receipt.json)、[serial](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap70lcd-f61554d9/serial.log)。
- [运行摘要与完整时间线](../../work/fx3-vm-20261101/menu-repair-01/runtime/lcd-osd-ap70-run-summary.json)。
- [宿主ASan/UBSan](../../work/fx3-vm-20261101/menu-repair-01/runtime/helpers/lcd-osd-transport-host-check.json)、[v25构建](../../work/fx3-vm-20261101/menu-repair-01/runtime/helpers/fx3-capid-v25-build.json)。
- [原调用者指令证据](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap70-passive-callers-proof.json)、[候选](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap70-lcd-osd/candidate70.json)。
'''
report.write_text(text)
state=json.loads((R/'STATE.json').read_text());state.update(updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),phase='AP70_REVIEW_COMPLETE_LCD_OSD_SOFTWARE_ONLY',current_candidate=v['candidate'],current_candidate_sha256=v['candidate_sha256'],last_run=v['run'],ap70_summary=str(R/'lcd-osd-ap70-run-summary.json'),ap70_report=str(report),missing_markers=missing,next_minimal_command={'status':'Lead决定ADF审计与后续GPE集成；0429/0500无需同步回复，snapshot2/3缺少im需单独观察，未擅自扩展'})
(R/'STATE.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
idx=report.parent/'README.md';s=idx.read_text();s=s.replace('最新：[清屏与后续启动协议解析]', '此前：[清屏与后续启动协议解析]',1);s=s.replace('# FX3 虚拟机续接修复回执\n','# FX3 虚拟机续接修复回执\n\n最新：[AP70亮度与OSD软件接受](ap70-lcd-osd.md)：0x111a消费释放0，0x159静默接受，TID334继续到BACK_LIGHT_MODE及无等待0429/0500；ADF032e/033d仍为最后观测等待点，无菜单/硬件验收。\n',1);idx.write_text(s)
print(report)
