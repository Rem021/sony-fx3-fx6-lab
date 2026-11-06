# r26 实现前设计

仅改宿主操作流程：原PAGE/server/runner/native observer、snapshot生命周期、正常按键gate、deadline与计划全保持字节。真实r25 8accepted/7confirm仍失败，不补确认。首个ACK后新帧可只是待机闪烁，不能自动视作效果完成。

postkey观察和r25未入队恢复观察严格分开。新观察schema fx3-postkey-observation-r26-v1只导出当前已加载Blob PNG的真实字节：同步捕获其源URL和显示元数据，异步读该不可变Blob后按实际字节核SHA；之后重新读fresh status并同步检查document/脚本/launch/run/step/attempt/nonce/alarm及PAGE生命周期，允许live画面前进。旧显示帧信息只标历史来源，firmware_generation=null，不主张因果或输入许可。server review_required/input_received/review_step对应冻结runner匹配native down/up后进入的已知接收阶段；不新增server准入或native效果证明。

每次click前将当前document UUID/timeOrigin和run incarnation只读绑定到attempt。accepted后，宿主持久flow先fsync observation reservation再导出首图，最多3次（含首图），每次再次observe必须另一次实际看上一图后的明确判断。身份/未知/耗尽/到期使flow terminal，再读帧不能复活；无自动重复观察、重试或延迟点击。

pin是另一独立wrapper调用：查看最新观察图后显式选择，先核图/receipt链接和实时身份，再持久保留pin-reserved-unknown，然后只调用原r25 capture一次。返回固定PNG必须重新实际查看后独立confirm；观察图不能冒充capture，固定后不可observe/repin。任何unknown、语义不符/拒绝、确认失败按原End；不延长原20s，不增加键预算。

验证用真实候选PAGE/server与实际operate __main__：mock native后3.5秒待机动画再菜单；先观察未pin，再独立observe/pin/confirm，包含真实非零工具/审阅间隔和deadline实测。覆盖身份、生命周期、次数/到期、冒充固定图、pin后复活/回包丢失；r25全恢复链接新observe/pin/confirm，并保留必要server/browser回归。只在新r26目录创建fixture；所有历史输入全哈希且只读。
\n## 实现修正：保留原CSP\n\n首两轮原始错误证明fetch(blob:)失败；原CSP connect-src只允许self，故改实际agent-browser screenshot，不改PAGE/server。截图SHA只绑定实际PNG字节；前后分别fresh status与同步完整身份，保留两端显示帧但不把其SHA/gen等同截图。每端点前后核唯一tab/URL，异步负例改截图阶段注入。原导出方案未作为最终合同。\n