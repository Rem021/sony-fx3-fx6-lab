# 显式确认辅助：候选操作说明

本目录只有离线候选，未部署。它只压缩**操作员已亲看完整目标画面之后**的宿主调用间隙；不会识别目标、发固件键、武装/延长闹钟、直接 POST 或自动重试。原页面、原 20,000ms 闹钟及所有 guest/健康/收尾门限保持原样。

先按既有 `../interaction-deadline-helper/OPERATION.md` 在**自有且唯一** `fx3-deadline-*` 浏览器会话安装原 helper，武装本次 nonce。操作员须在画面 PNG 中亲自确认语义目标，并记录所见图的 64 位小写 SHA256、实际 review step 和非空说明。

`--png-sha` **只能填页面已加载固件图像的 `shownSHA`，并须等于当时 `lastStatus.frame.PNG_sha256`**；它不是 1280×1200 整张网页截图文件的 SHA256。两类证据分列保存：网页截图供人看页面语义，其文件 SHA 只标识整页截图；`shownSHA` 标识页面中固件 PNG 内容。实际操作时先在专属 tab 只读取得 `shownSHA`、`displayedGeneration`、`displayed`、`lastStatus.frame`，截取并亲看同一页面，再只读取一次这些字段。前后 `shownSHA`、generation、sequence 与当前 frame 身份必须一致且 `render_valid`；若任何字段变动，即使 A→B→A 后 SHA 回到 A，也要重新看最新画面或 End，不能在截图后取任意最新 SHA 填入已审图身份。命令示意：

```sh
agent-browser --session "$DEADLINE_SESSION" eval '({shownSHA,displayedGeneration,displayed,frame:lastStatus.frame,render_valid:lastStatus.render_valid})' > "$DEADLINE_RUN_DIR/confirm-before.json"
agent-browser --session "$DEADLINE_SESSION" screenshot "$DEADLINE_RUN_DIR/confirm-page.png"
agent-browser --session "$DEADLINE_SESSION" eval '({shownSHA,displayedGeneration,displayed,frame:lastStatus.frame,render_valid:lastStatus.render_valid})' > "$DEADLINE_RUN_DIR/confirm-after.json"
shasum -a 256 "$DEADLINE_RUN_DIR/confirm-page.png" > "$DEADLINE_RUN_DIR/confirm-page-file-SHA256.txt"
```

核对前后身份且亲看截图中的**固件画面**之后，才显式调用一次：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 explicit_confirm_cli.py \
  --session 'fx3-deadline-<本轮唯一名>' \
  --url 'http://127.0.0.1:<本轮端口>/' \
  --launch-id '<本轮launch_request_id UUID>' \
  --nonce '<当前已armed闹钟UUID>' \
  --step '<当前review_step>' \
  --png-sha '<本人刚看清的完整PNG SHA256>' \
  --target '本人确认的具体原生页面或合法无变化效果' \
  --receipt '<本轮新文件绝对路径>.json'
```

必须事先知道精确 URL（含尾斜线）、launch ID、alarm nonce、step、图 SHA；文件名不可复用。CLI 先核唯一专属 tab，再在同一页面 eval 中核 r17 PAGE 脚本及原确认 handler 指纹、document/launch/alarm 的 nonce 与未过期 due、当前完整图身份及可点击的原确认按钮。随后只调用一次 `confirmButton.click()`，同步记录原 handler 创建的 `pendingConfirm` 身份，并在原 due 内最多等待 10s 观察原 `confirmationMatches`、当前最新图加载、server ready 与七键放行；最后才调用原 helper 的 `cancel(nonce)`，核 nonce、原 due、state cancelled 与 elapsed <20,000ms。历史确认图无需等于后来新图；新图仍须通过原 PAGE 的 SHA+generation+render_valid 门。

输出 `confirmed_and_cancelled` 才表示本次宿主确认及闹钟解除；不代表固件菜单正确或 VM 生命周期通过。`refused` 表示点击前门不符，`unknown` 表示点击可能已经发生但 ACK/放行/取消未证实；两者都不会重试或解除闹钟。CLI/browser eval 超时、异常或回执写入中断时，`eval_may_have_started=true` 的留存文件必须按“可能已点击”处理，禁止再次调用来猜测结果。原闹钟继续兜底；遇原生错误或送达未知仍按既有 End/收尾规约处理。

独占回执保存调用前、点击、匹配 server receipt、最新帧放行、cancel 或拒绝/超时的 UTC 与页面 `performance.now()`。报告中的 `target` 是操作员输入的说明，不是机器识图证明。试用时仍须逐张截图、手动决定键和页面确认；此工具本身不给 VM 运行权限。
