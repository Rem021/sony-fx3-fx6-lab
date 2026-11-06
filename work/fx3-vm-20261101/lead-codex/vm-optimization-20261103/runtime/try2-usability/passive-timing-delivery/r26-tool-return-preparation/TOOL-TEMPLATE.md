# 实际可用的单次工具模板

本环境已实际发现并调用mcp__node_repl__js，支持node:child_process、文件读取及nodeRepl.emitImage。已在同次顶层functions工具内实测“fake child执行 → 文件loadResult → emitImage”，另测exec输出上限8 tokens且完全不解析该屏幕，仍从本次完整文件取摘要并显示图。仅历史回放；生产原operate未执行。

## 生产调用：一个动作，一次工具返回

操作代理只填写当前已授权run目录和**此刻明确给出的一个**operation数组。runDir用绝对规范路径，output目录由UUID新建，不复用。以下是functions工具的完整JavaScript代码；本次只做observe例子，必须在刚刚实际看过上一图并明确需要再观察时使用。click、pin、confirm等动作也只各占一次工具调用，不在代码里串联。

~~~javascript
// @exec: {"yield_time_ms": 1000, "max_output_tokens": 1800}
const runDir = "/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery/当前task已授权新目录";
const operation = ["observe", "实际看上一张本次观察图仍为正常过渡，明确另一次观察"];
const moduleURL = "file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery/r26-tool-return-preparation/tool_call.mjs";
const code = "{const {executeAndLoad}=await import(" + JSON.stringify(moduleURL) + ");const v=await executeAndLoad(" + JSON.stringify(runDir) + "," + JSON.stringify(operation) + ");nodeRepl.write(v.summary);if(v.png)await nodeRepl.emitImage({bytes:v.png,mimeType:'image/png'});}";
const shown = await tools.mcp__node_repl__js({code, timeout_ms:120000, title:"单次明确动作：本次摘要与实际PNG"});
if (shown.isError) {
  text("返回通路未知：不展示图、不重发；下一明确调用走原cleanup/End。");
} else {
  for (const item of shown.content ?? []) {
    if (item.type === "text") text(item.text);
    else if (item.type === "image") image(item);
  }
}
~~~

120000只是工具等待原进程和原失败cleanup的上限，**不会改变原20s alarm**。若functions返回Script running cell ID，只能对该同一cell使用functions.wait收取完成；不是再次执行动作。

Node execFile不经shell，stdout不解析；原child的完整stdout/stderr先由Python直接写当前run新目录。只有本次成功完整JSON通过schema/action、PNG路径/新建时间/哈希校验，才产生returned.png和小于4096字节summary。show_result再用filesystem读取本次summary，校验调用绑定及returned.png字节。上面代码不读current-return.json，也不捕获终端截断文本来猜状态。

## 原动作参数

- click：operation=["click", "1", "本步计划中的明确目标"]；按原计划与审阅前提，不允许自行增加键。
- observe：operation=["observe", "实际看上一观察仍正常过渡的判断"]；含click首图最多3次，原20s不变。
- pin：operation=["pin", "实际看本次未固定观察图已完整，明确选择固定"]；返回scope=fixed_postkey_snapshot的新PNG。
- confirm：operation=["confirm", "实际重新看本次固定PNG后的具体语义判断"]；成功无图片，只返回确认结果。
- standby_review / recovery_review / recovery_cancel / reject仍是原动作加一个明确判断字符串，不增加调用。

图显示后必须结束本次工具调用，让模型真正接收、查看。下一次再决定pin或confirm；不得在同一脚本中判断图片语义、用SHA替代语义、自动observe循环或自动pin/confirm。

## 失败责任

非零退出、完整JSON非法/截断、陈旧PNG、摘要/图片校验失败、图片展示工具异常都无图、无旧结果回读、无重发。原operate失败时会自行原End。若只是适配/展示故障、原动作可能已成功，操作代理下一次应明确调用冻结路径runtime-wrapper/cleanup.py，环境FX3_NAV_RUN_DIR=本次runDir；不要再执行原click/observe/pin/confirm以“补回包”。原20s alarm继续兜底。此模板不自动追加cleanup，以保持一次明确动作和原独立审阅语义。

没有授权新VM/Start，不能把这份准备当作启动权限。
