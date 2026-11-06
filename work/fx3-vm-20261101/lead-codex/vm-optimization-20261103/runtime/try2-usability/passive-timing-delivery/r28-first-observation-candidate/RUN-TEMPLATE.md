# 未来明确授权任务的运行模板

本文件不授予VM/Start权限。用本r28 prepare_run.py为未来task创建全新run，再执行其preflight与既定启动流程。CLI-TEMPLATES包含原8步及observe/pin/confirm/recovery/reject命令，返回适配必须使用本目录return-tools，不混旧operate。

在Start/arm前用真实Node工具预载并绑定当前run（不执行动作）：

~~~javascript
const r = await tools.mcp__node_repl__js({
 code: "globalThis.fx3R28One=(await import('file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery/r28-first-observation-candidate/return-tools/short_tool.mjs')).bind('本轮已授权run绝对路径');",
 title: "仅预载本r28单动作函数"
});
for (const b of r.content ?? []) if (b.type==='text') text(b.text);
~~~

实际看初始图并单独standby_review后，一次工具调用只给一个当前明确动作：

~~~javascript
// @exec: {"yield_time_ms":10000,"max_output_tokens":1100}
const r=await tools.mcp__node_repl__js({
 code:"await fx3R28One(['click','1','完整Setup > Area/Date，橙色Area/Date/Time Setting'],nodeRepl);",
 timeout_ms:120000,title:"本次明确动作与实际PNG"
});
if(r.isError) text('返回未知：不重发，下一明确调用原cleanup/End。');
else for(const b of r.content??[]){if(b.type==='text')text(b.text);else if(b.type==='image')image(b);}
~~~

若functions返回Script running，只wait该cell取同次结果，不重新执行。10000ms只减少额外工具往返的可能，120000ms仅容纳原进程/失败cleanup等待；原browser20秒始终不变。

click首图不会早于原arm+5000ms，已过该点不再额外等待。图回模型后真实查看：完整才下一调用pin；若合法过渡，可下一明确observe（最多3张含首图，后续不重复5秒）。5秒不算完成证明，不等SHA稳定、不自动动作。pin返回新固定PNG后必须重新实际查看，再下一调用confirm；不符/不确定则reject/原End，不repin。

示例替换：pin为['pin','实际看本次观察完整，明确固定']；confirm为['confirm','实际重新看本次固定PNG后的具体语义判断']。不得把多动作串入同一脚本。返回非零、身份/未知/到期或图片展示失败不读旧图、不补回包；原operate失败自行End，通路故障由操作代理明确调用本r28 runtime-wrapper/cleanup.py，环境FX3_NAV_RUN_DIR=本次run。

预绑定丢失不能猜测重发或静默切旧候选；按未知处理。未入队恢复依旧独立看恢复图→recovery_cancel→看新恢复图→recovery_review→另一次新nonce click，不能当postkey确认。
