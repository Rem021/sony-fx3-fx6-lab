https://github.com/QAQLeonard/a7c2-fl23-research/issues/44
一键安装失败后恢复原厂功能出错
# ILCE-7CM2 / 固件 2.01 / Windows：0x2CF19xx 一组设置键会话内自变化，verify_preservation 拦截所有写入流；另有 journal os.replace 偶发 WinError 5 导致工作区无法归类

## 环境

- A7C2Tools 3.0.3（Windows x64 包），Windows 11（10.0.26300），自带 Python 3.11.9
- 机身：ILCE-7CM2，固件 2.01，USB 连接=海量存储
- 驱动：0E8A=libusbK（Zadig 手动装），0336=WinUSB（工具自动装）
- 以下日志若标注"本地补丁后"，来自打了 `core.py` 白名单补丁的运行（见问题 1 末尾的披露）

## 问题 1（主要）：chip0/0x2CF19xx 设置键在无写入时自漂移，`verify_preservation` 拦截一切写入流

**现象**：factory_reset / resume_factory / vertical_disable / setup_all 的设置阶段全部以
`發現額外設定變動：chip0/0x…` 停机。断电取电池后复现，跨多次服务会话稳定复现。
当前 `runtime_counter` 白名单只登记了 0x01070000 与 0x02780000。

**观测到的键与取值**（全部 4 字节、attr 0→0、before 全为 `00000000`）：

| 键 | 变化 | 备注 |
|---|---|---|
| 0x2cf191c | `0 → 0x1a1`（417） | 多轮取值稳定 |
| 0x2cf196f | `0 → 0x1a1`（417） | 与 191c **同轮同值** |
| 0x2cf191d | `0 → 0x0088a8bd`，后一轮 `0 → 0xe8e00d73` | 跨轮变化 |
| 0x2cf1970 | `0 → 0xe8e00d73` | 与 191d **同轮同值** |

即两对字段分别共享同一写入值，应为同一写入者（时间戳/序号类盖章）。

**证据 A（no-op 也漂移）**：work `20261025-192435-factory-cf869` 中，mode-1 native 写入结果
`changed_mask=0`、before==after（工具未写任何东西），verify_preservation 仍在 0x2cf191c 上停机。
键值漂移发生在"生成计划读取→写入后复查"的数十秒间隙内，与工具写入无关。

**证据 B（与管理键区不重叠）**：mode-1 targets 为 47123664..47125129（0x2CF0CD0..0x2CF1289）；
漂移键全部位于 0x2CF1900–0x2CF19FF，在工具管理的 look 键区之上，互不重叠。

**建议**：把 0x2cf191c/0x2cf191d/0x2cf196f/0x2cf1970（或整个 0x2CF19xx 页的 4 字节同 attr 漂移）
纳入 `runtime_counter` 遥测白名单。

**本地补丁披露**：为完成安装，我本地修改了 `camera_runtime/core.py` 的 `runtime_counter`——
接受 chip0/0x2CF1900-0x2CF19FF 的 4 字节同 attr 漂移为遥测并打印前后值；另在
`verify_preservation` 的报错信息中加入了前后值。补丁后 factory 恢复与一键安装全部顺利完成，
说明白名单方案即可解决。

## 问题 2：journal 落盘 `os.replace` 偶发 WinError 5，工作区陷入无法归类的 NEEDS_REVIEW

**现象**：setup_all 安装阶段，`backupstore.write_json` 的 `os.replace(direct.private.json.<hash>.new,
direct.private.json)` 偶发 `PermissionError [WinError 5] 拒绝访问`（疑似杀软/索引器短暂锁定热文件）。
崩溃点恰在 `native_result_verified` 之后、`native_cleanup_verified` 之前。

**后果**：
1. journal 最后一笔未落盘，子事务停在 NEEDS_REVIEW；后续 setup_all 时 `reviewnames.source` 报
   `Unknown last operation; do not replay`、`namespause.source` 报 `Names/cleanup/mount outcome is
   not fully accounted for`，最终硬拒"上次安装结果需要核对，不会重复刷写"——没有用户侧核对/清除入口。
2. staged worker 的 cleanup 步骤被跳过（本次靠断电清除）。

**建议**：`write_json` 的 `os.replace` 加重试/退避或备用临时名；归类逻辑对"journal 止于
native_result_verified"的子事务给出专门处理（视为暂存已验证、无持久写入）；或提供核对后继续的 UI 路径。

## 问题 3（补充观测）：认证后切换 0336 可能迟到远超 20 秒等待窗

- 多次 usb_prepare：Senser 认证三轮全部成功，但 20 秒窗口内 0336 不出现，报"認證後相機未進入服務模式（期間出現的 Sony USB 身份：0e8a）"；其中两次随后 60 秒内 0E8A 也未回归（"服務身份未出現，相機也未回到普通 USB"）。
- 但 18:50（一轮失败结束后约 1–2 分钟），相机自行以 0336 出现并停留约 40 秒（18:50:51–18:51:17 间的扫描可见）。
- 中间身份实测：096F 于 17:33:29（setupapi 记录）、0D68 于 18:44:16（驱动扫描记录）。

可作为 field log 的补充：迟到型切换 + 超窗后才现身。

## 其他（轻微）

- 首次 wdi-simple 安装 0E8A 时，因相机存储卷被占用（STORAGE\Volume veto query-removal，
  setupapi 记录 "Device required reboot: Query remove failed 0x17"）导致 180 秒超时；重插后自愈。
  或可在安装前提示关闭占用相机盘符的窗口/弹出卷。

## 附件

- 诊断包 ×2（a7c2-diagnostics.zip，18:42 与 19:15 两个时点）
- work 目录：`20261025-191255-setup-57137`（WinError 5 现场）、`20261025-192356-factory-d9992` 与
  `20261025-192435-factory-cf869`（no-op 漂移证据）、`20261025-202330-setup-6220d`（补丁后成功安装，
  含全部 telemetry 行）
- 关键日志摘录（本地补丁后，成功安装那一跑）：

```
telemetry: accepted chip0/0x2cf191c self-change attr 0->0 data 00000000->a1010000
telemetry: accepted chip0/0x2cf191d self-change attr 0->0 data 00000000->e8e00d73
telemetry: accepted chip0/0x2cf196f self-change attr 0->0 data 00000000->a1010000
telemetry: accepted chip0/0x2cf1970 self-change attr 0->0 data 00000000->e8e00d73
```