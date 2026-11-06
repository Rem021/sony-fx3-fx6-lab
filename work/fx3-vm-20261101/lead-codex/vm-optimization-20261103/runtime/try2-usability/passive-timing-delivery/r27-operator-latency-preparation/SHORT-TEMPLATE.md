# 可复用的短返回模板（仅便利候选，不证明20秒可行）

原r26返回适配不改。short_tool.mjs只预先绑定明确run目录、调用原executeAndLoad一次、显示精简摘要及原PNG字节；不保存旧结果、不自动动作、不判断语义。globalThis保留而同URL import模块会重建的实际探测见NODE-PROBE-1/2；因此不使用模块内Map作为跨调用顺序或成功状态。

## 只在未来明确授权任务的Start/arm前预载

此准备本身不含任何VM权限。用真实Node工具预载，填未来已授权run绝对路径：

~~~javascript
const r = await tools.mcp__node_repl__js({
  code: "globalThis.fx3R27One=(await import('file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery/r27-operator-latency-preparation/short_tool.mjs')).bind('当前任务已授权run绝对路径');",
  title: "仅预载单动作返回函数，不执行动作"
});
for (const b of r.content ?? []) if (b.type === "text") text(b.text);
~~~

此阶段可以检查typeof globalThis.fx3R27One；预载或原preflight未通过不开始本轮。绑定清空/丢失后不能在已arm流程中靠猜测重发，按未知走原End。完整原动作回执仍写原task下新tool-return-UUID，不在此模块存成功状态。

## 看图后每次只给一个明确动作

以下functions模板适用于正常child约2.7秒的场景，初始等待10000ms，减少1000ms提前yield的可能；并非变更原20秒alarm。若仍返回Script running，唯一后续是functions.wait收取同cell，不重新执行动作。

~~~javascript
// @exec: {"yield_time_ms": 10000, "max_output_tokens": 1000}
const r = await tools.mcp__node_repl__js({
  code: "await fx3R27One(['pin','刚刚实际看本次观察图完整，明确选择固定'],nodeRepl);",
  timeout_ms: 120000,
  title: "当前唯一明确动作与实际PNG"
});
if (r.isError) text("返回未知；不重发，下一明确调用原cleanup/End。");
else for (const b of r.content ?? []) {
  if (b.type === "text") text(b.text);
  else if (b.type === "image") image(b);
}
~~~

pin例子只能在该观察图实际返回模型并看过后使用；随后必须再看新固定PNG，另一独立调用才可confirm。click/observe/confirm等用原参数替换数组，一次一个动作。禁止将observe→pin→confirm串进脚本、用SHA/稳定帧判语义或延长/重置timer。

生产short_tool仅导入和类型检查，未执行原operate。group-b历史演练实际验证了“预载持有函数→短单次Node调用→真实图返回→下一独立动作”，并用文件绑定前一次回执/PNG限制回放顺序；它不是实时固件/20秒验收。预载约1ms、摘要少约900字节，不足以解释或消除6–10秒跨调用间隔。
