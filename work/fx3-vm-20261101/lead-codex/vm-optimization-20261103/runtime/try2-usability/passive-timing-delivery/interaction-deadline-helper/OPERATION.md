# 后续有界测试的一次性截止规约

这是测试worker手动调用的辅助，未部署到产品入口。生产辅助固定20,000ms；不改变原30秒停止要求、guest时限、原始输入门或收尾合同。浏览器挂起、事件循环阻塞、后台节流或页面失效时不能保证硬实时30秒。

## 绑定与视口

1. 新运行须另获授权并照原规约核卷UUID/运行占用/固定输入；本工具不授予VM运行权限。
2. 只用worker自有、已经打开当前运行的单标签会话，名称须为 `fx3-deadline-*`。不得用default、用户Chrome/CDP会话或多标签会话。包装器不导航、不切换/关闭标签；逐次核对唯一标签URL。
3. 把专属浏览器视口固定为 **1280×1200**（本次真实PAGE已验证）。亲看当前完整目标区域与“结束试用”按钮同时完整在视口中。若布局不满足，可在武装前扩大专属视口；不能忽略可见性校验。
4. 武装到取消/到期期间不得滚动、缩放、改viewport、刷新、导航、换标签或关闭浏览器。不得为腾出时间重装辅助或重新武装延长同一目标。
5. 精确URL必须与当前 `location.href` 原文相同：`http://127.0.0.1:PORT/`，含末尾斜线，无query/hash/凭据；不接受localhost或其他主机。还核对本次 `lastStatus.launch_request_id`、当前document/timeOrigin、固定r12 PAGE脚本SHA、预定DOM及原End处理器身份。

## 显式调用

在本目录执行以下命令；先将所有占位符替换为**已核对的当前运行**，证据路径只能指向该运行的新目录。不是可直接照抄启动VM的脚本。

```sh
DEADLINE_SESSION='fx3-deadline-<新run-id>'
DEADLINE_URL='http://127.0.0.1:<当前端口>/'
DEADLINE_LAUNCH='<当前页面launch_request_id>'
DEADLINE_RUN_DIR='<已核卷的新run绝对路径>'
agent-browser --session "$DEADLINE_SESSION" set viewport 1280 1200
agent-browser --session "$DEADLINE_SESSION" eval '({url:location.href,launch_id:lastStatus.launch_request_id,phase:lastStatus.phase})'
PYTHONDONTWRITEBYTECODE=1 python3 deadline_cli.py install --session "$DEADLINE_SESSION" --url "$DEADLINE_URL" --launch-id "$DEADLINE_LAUNCH" > "$DEADLINE_RUN_DIR/deadline-install.json"
```

只有已Start并处于ready的本次页面可武装。脚本只接受当前r12页面指纹；未来候选若PAGE脚本不同会拒绝，须先另行离线审查，不得删除指纹条件临场绕过。

每个新语义目标人工生成一个从未用过的UUID（可运行 `python3 -c 'import uuid; print(uuid.uuid4())'`），复制进任务变量；**在目标固件键点击前**执行：

```sh
DEADLINE_NONCE='<本目标全新UUID>'
PYTHONDONTWRITEBYTECODE=1 python3 deadline_cli.py arm --session "$DEADLINE_SESSION" --url "$DEADLINE_URL" --launch-id "$DEADLINE_LAUNCH" --nonce "$DEADLINE_NONCE" > "$DEADLINE_RUN_DIR/deadline-arm-step-01.json"
```

必须确认返回 `current.nonce` 等于本nonce、`current.state=armed`、`deadline_ms=20000`；保存原 `due_ms`。然后worker通过真实页面按钮只点击本次已授权目标键，不用脚本POST。工具本身没有发送键的接口。CLI耗时计入闹钟，不会因此重新给20秒。

## 观察、确认与解除

- 保持闹钟有效，使用短轮询和当前完整截图判断**语义目标**；NO CARD闪烁/任意framechanged不是完成证据。
- 看清目标后，若页面要求宿主看图确认，由worker亲自点一次，并核对匹配的HTTP200/nonce/step/gen/SHA、当前有效新帧和输入ready；辅助不会确认。可让同一闹钟覆盖这段放行观察，避免旧r11确认后卡住时失去截止保护。
- 上述目标和必要放行完成后，worker才显式解除**当前同一个nonce**：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 deadline_cli.py cancel --session "$DEADLINE_SESSION" --url "$DEADLINE_URL" --launch-id "$DEADLINE_LAUNCH" --nonce "$DEADLINE_NONCE" > "$DEADLINE_RUN_DIR/deadline-cancel-step-01.json"
```

**成功取消证据**必须同时有：返回current.nonce等于arm文件；state=`cancelled`；events有本nonce的`cancelled`及elapsed_ms<20000；原due_ms不变。再按原规约核页面没有停止/错误，不能把“计时器已取消”当成“End被撤回”。保存已亲看目标截图SHA和正常确认回执。重复/旧nonce返回ignored不算成功取消。下一目标用新UUID。

- 未达到目标不得提前cancel换新nonce延长。若明确409后允许人工再按/再确认，须遵守该轮已有授权、重新亲看图、统计机会；原闹钟继续，绝不自动重试或重置截止。
- 送达未知/错误/目标未成立/前端未放行时先End；不为补证等待到20秒。计时器是后备，不替代即时停止规则。

## 到期与清理

- 到期只调用捕获的、仍在本document完整可见的原End按钮 `.click()`，一次之后永久sealed，不补点或重试。若原PAGE已经ending/stopping/finished或End已disabled，只记录，不再click。
- `end_click`仅证明调用处理器；仍须核真正HTTP End ACK、恢复原字+ACK、QMPquit/exit/reap/PID/双锁/finalACK。它不是VM清理通过的证明。
- URL/页面/DOM/End可见性不符会记录`expire_refused`，不会转去其他标签、自动滚动、修改handler或直接POST。此时截止未能操作，须按现有人工收尾流程处理并记失败；不要把拒绝当作已End。
- 本辅助不改/清除原PAGE的错误提示；辅助错误和拒绝留在CLI错误或status.events中，须保存为回执，不自动隐藏。
- 主动End无需先cancel：已进入停止则后备到期只记录。正常收尾验证完成后关闭专属浏览器，销毁当前document；不可在尚未End时关闭/导航规避闹钟。
- 已取消或到期后可显式 `deadline_cli.py dispose ...`（同URL/launch参数）封存辅助；活动alarm不允许dispose。没有setInterval、守护进程或launchd任务。

## 离线复核

```sh
PYTHONDONTWRITEBYTECODE=1 python3 offline_browser_test.py
```

这只启轻量loopback真实r12 PAGE/TrialState和专属Chrome，绝不启VM。测试短版仅替换deadline.js中唯一20,000常量为1,200ms；生产20秒包装器另做arm/cancel/dispose验证。离线脚本的fixture MENU点击仅为pending场景布置，不能复制成真实运行的自动按键/自动确认流程。
