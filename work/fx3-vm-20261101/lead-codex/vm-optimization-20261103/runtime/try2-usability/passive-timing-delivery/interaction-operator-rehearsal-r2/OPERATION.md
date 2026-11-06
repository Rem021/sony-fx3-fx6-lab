# r2 单次操作员模拟演练

准备阶段只运行五项本地假CLI输出校验。未取得协调端明确放行及固定hash之前，不创建COORDINATOR-RELEASE.json，不运行fixture_server.py/capture_once.py，不arm或点击模拟MENU。dependency_gate.py在进程启动和arm前重新核冻结交付/源码/依赖。目录存在不代表验收。

得到放行后记录原消息ID与SOURCE-FREEZE.json/SHA256SUMS/REPORT.md固定SHA，核验后仅启动本目录fixture_server.py及prepare.py。原r17 PAGE/TrialState不变，唯一自有fx3-deadline-*标签，1280×1200；真实Start只启动模拟后端，未创建任何VM/guest。参考完整PNG来自历史c33f8c46，7秒是显式指定的模拟延迟。参数和独占nonce、确认命令均在arm前准备。

单个工具调用运行capture_once.py，它只执行原20秒arm→一次真实页面模拟MENU→r2只读取图。必须以实际进程exit0、JSON合格status、validated_new_screenshot=true、绝对截图路径在本轮新menu-capture-01独占目录内、实际PNG文件存在及hash相符作为展示前提。任何失败非零退出且没有screenshot_path；禁止取旧图或不存在图。调用端还须解析stdout并检查状态后才view_image，在同一工具结果内返回图像。

亲看返回画面中完整Setup > Area/Date和橙色Area/Date/Time Setting焦点后，下一工具调用只显式运行confirm_once.py一次。该包装器调用原冻结explicit_confirm_cli一次；不会自动判断语义、预先确认、重发键或重新arm。原工具完成真实confirm HTTP匹配、原PAGE放行和同nonce/cancel。只有confirmed_and_cancelled、原due不变及elapsed<20000ms才算本步骤通过。模型图像收到/审完的时钟无仪器时记unknown。

失败先原页面End，再补证、保存原时钟/HTTP/nonce，禁止重复演练；成功也只证明一次模拟工具链。结束后dispose辅助、关闭自有browser和本fixture端口/进程，独立核PID不存在、端口关闭、浏览器inactive。生产20秒timer不是系统挂起/阻塞条件下的硬实时保证。所有旧失败件、候选、helper、入口、ledger保持不变。
