# FX3 删除／C4 键静态审计

2026-11-02。**删除／垃圾桶键使用 `UIBIZ_KEY_TACT_DELETE`：UI 枚举 `0x23` → InfraInput 物理码 `0x1f8`。** 名称行在 appFw `0x4164fe8`，配对行在 `0x2f8f9f0`；不能将 UI 值 `0x23` 当成物理键码。原厂 FX3 说明将机身同一个按钮标为拍摄用 Custom button 4／回放用 Delete，故这里的 C4 指该物理按钮，不另造 CUSTOM4 码。[Sony Rear side](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000886869.html)

六个目标键、十二个精确 20B body 均已从原名称表、原映射表和默认模板重建。**首次设置页的垃圾桶提示已由既有 PNG 确认，`DELETE_ON=0x90000` 也已闭合；但 `DELETE_ON → Set on the camera` 的具体动作 ID 分派仍未完整证实。** 不以截图、事件／页面配对或候选处理函数代替完整键→动作证明，详见第四节。没有启动 QEMU、发送按键、访问设备、修改 runtime／STATE／原件或获取运行锁；只写本目录三个文件。

## 复现

在项目根 `/Volumes/KAFU2T/AI/Projects/Mac` 执行：

```sh
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python -B \
  work/fx3-vm-20261101/lead-claude/audits/key-delete-c4/audit_key_delete.py

work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python -B \
  work/fx3-vm-20261101/lead-claude/audits/key-delete-c4/audit_key_delete.py --check
```

默认重建 [key-delete-proof.json](key-delete-proof.json)，`--check` 比较重建内容而不写文件；两次均退出 0。脚本核验卷 UUID、五份原件 SHA-256、BK4 完整记录校验和、六个名称／配对／回调行、两份硬件配置记录和新增事件分派指令；完整读取前审计 JSON，独立反汇编比对其全部 **25 块、1,629 条原指令与 558 条模块重定位**。前审计的 565 ELF 导出提供者全量扫描没有重跑，也不需要它来确定本次六个键。

证据简称及完整路径／SHA 均在 proof `sources`：

| 简称 | 原件 | 地址域 |
|---|---|---|
| A | `menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/appFw.so`，SHA `545c5053…` | ELF VA，运行时需加实际装载基址 |
| O | 同目录 `libObj.so`，SHA `c4681d20…` | ELF VA |
| K | 完整投影 `input.ko`，payload SHA `d9fcf59b…` | ET_REL，写作 `.text+偏移`，不是运行时绝对地址 |
| C | `stage2/extraction/files/nflasha8/cpapp-b.bin`，SHA `c90d00d8…` | Thumb VA＝文件偏移＋`0x108000` |
| B | `original-seeds/FX3-CX95900_ALLLANG-Backup.bin`，SHA `bf3a9d85…` | **文件偏移**，不是 VA |

## 1. 六个键的 UI 枚举与物理码

A 名称表行是 `<u32 enum,u32 字符串长度,u64 字符串指针>`；`0x2f8f8d8` 起 1,114 对 `<u32 UI,u32 InfraInput>`。A `0x15948f8..0x159491c` 以原表建映射，`0x16ee3b8..0x16ee3f0` 执行转换，`0x16ef16c` 在物理状态查询前调用它。脚本逐一解析 ELF 重定位，未凭相邻枚举或 Linux evdev 值猜测。

| 键／原名称（省略 `UIBIZ_KEY_`） | UI 枚举 | InfraInput 码 | A 名称行 VA | A 配对行 VA |
|---|---:|---:|---:|---:|
| 删除／C4：`TACT_DELETE` | `0x23` | **`0x1f8`** | `0x4164fe8` | `0x2f8f9f0` |
| C1：`TACT_CUSTOM` | `0x0e` | `0x66` | `0x4164e98` | `0x2f8f948` |
| C2：`TACT_CUSTOM2` | `0xdf` | `0x70e7` | `0x4165ba8` | `0x2f8ffd0` |
| C3：`TACT_CUSTOM3` | `0xe4` | `0x70ec` | `0x4165bf8` | `0x2f8fff8` |
| 播放：`TACT_PLAY` | `0x22` | `0x1f7` | `0x4164fd8` | `0x2f8f9e8` |
| Fn：`TACT_FN` | `0x8d` | `0x7095` | `0x4165688` | `0x2f8fd40` |

六个物理码也全部出现在 A 原生回调列表：`0x2f964f0`（C1）、`0x2f965d4`（PLAY）、`0x2f965e0`（DELETE）、`0x2f96acc`（FN）、`0x2f96ea4`（C2）、`0x2f96ee0`（C3）。每行 `<key,event,status>` 为 `<code,code,0x7ffffffe>`，A `0x16ef2ec..0x16ef2fc` 注册 1,086 行；这里的 `0x7ffffffe` 是筛选值，不能用作按下或抬起值。

已扫描完整 `UIBIZ_KEY_*` 名称及其 772 个名称表行（A `0x4164dc8..0x4168718`），没有找到精确名字 `UIBIZ_KEY_TACT_CUSTOM4`／`UIBIZ_KEY_TACT_C4`。这是有限名称搜索结论，不声称所有可能的 C4/custom-function 名字都不存在；C4 的同按钮身份来自 Sony 机身说明，物理数字来自 A `0x2f8f9f0`。C1／C2／C3 是上述固件逻辑名称，不能仅由这些名称推定 FX3 全部机身数字标识与可自定义功能的当前分配。

## 2. libObj 键表与默认模板交叉检查

**O 的键表来自 B 的配置，未发现一份带 `TACT_DELETE` 名字的独立 libObj 内嵌表。** O `0xcd904..0xcdb1c` 读取配置，`0xcd4bc..0xcd4f0` 选择 BIN type2 并按 48B 步长取行；`0xc9bb4..0xc9c04` 以行 `+8` 搜索物理码。B record0 的属性 `0x007a0001` 位于文件 `0x53560`，首块为 `BIN! / type2 / 1112×48B`；以下是实际会被 O 解释的原始行，而不是自建的别名表。

| 键 | B 48B 行文件偏移 | infraName / localCode / osalId | 首次／后续重复间隔 | flag |
|---|---:|---|---:|---:|
| C1 | `0x53810` | `1 / 0 / 0x00410025` | `800 / 100 ms` | `0` |
| PLAY | `0x53b70` | `1 / 0 / 0x00410025` | `1000 / 200 ms` | `0x40` |
| DELETE／C4 | `0x53ba0` | `1 / 0 / 0x00410025` | `800 / 100 ms` | `0` |
| FN | `0x54f50` | `1 / 0 / 0x00410025` | `800 / 100 ms` | `0` |
| C2 | `0x55eb0` | `1 / 0 / 0x00410025` | `800 / 100 ms` | `0` |
| C3 | `0x55fa0` | `1 / 0 / 0x00410025` | `800 / 100 ms` | `0` |

B 的硬件属性 `0x01120000` 保留两个不同记录：record0 属性文件 `0x71190`（12 行），record1 属性文件 `0x13cdb4`（39 行）。K `.init.text+0x38` 取此属性，`+0x1dc` 对 64B 行计数；两记录均通过其整个 BK4 记录校验和。

| 键 | 模板记录／B 行文件偏移 | 类别／unit 或 bank／bit／active_level | on_value / ex_info |
|---|---|---|---|
| C3 `0x70ec` | record0 / `0x71468` | GPIO(2) / bank17 / bit18 / 1 | `1 / 0` |
| C2 `0x70e7` | record1 / `0x13d2cc` | GPIO(2) / bank17 / bit10 / 1 | `1 / 0` |
| C1 `0x66` | record1 / `0x13d30c` | GPIO(2) / bank17 / bit11 / 1 | `1 / 0` |
| FN `0x7095` | record1 / `0x13d34c` | GPIO(2) / bank17 / bit12 / 1 | `1 / 0` |
| DELETE `0x1f8` | record1 / `0x13d38c` | GPIO(2) / bank17 / bit18 / 1 | `1 / 0` |
| PLAY `0x1f7` | record1 / `0x13d44c` | FRONT(4) / unit`0x6000` / bit1 / 0 | `1 / 0` |

注意：record0 C3 与 record1 DELETE 都写 bank17/bit18，**不能跨记录拼成同一活动 GPIO 路由，更不能认定两个逻辑键可互换**。K `.text+0x1f74..0x1f80` 有原 GPIO 查询，C `0x49bdbe` 有 FRONT 配置名称，但本审计没有重建活动 VM 的记录选择、PCB 连线或 SysCon 完整帧。B 来源是同型号公开默认 `0110_backup/SYSIPSX-DSLR/ALCIN/CX95900_ALLLANG.bin`，完整封存来源在 proof `template_provenance`，不是当前相机设置读回。

## 3. 按下／抬起的精确 20B body

沿用前审计原生 OSAL 物理键入口：`dst=0x807a0020`、元数据 `src=0x00410025`，body 为五个小端 u32：

```text
+0 key_code | +4 sub_key_code=0 | +8 status=1/0 | +12 ex_info=0 | +16 from_type=1
```

格式由 K `.text+0x1318` 的 `len=0x14`、`+0x13d0` 的 `stp key,wzr`、`+0x13d4` 的 `stp status,ex`、`+0x13dc` 的 `str from` 绑定；C `0x49b8de/0x49b940/0x49b944/0x49b948` 是独立的原发送者证据。来源在 K `+0x13ac..0x13b8`／C `0x49b922..0x49b928` 设置，B 上节行全部 `on_value=1,ex_info=0`。O `0xcb754..0xcb78c` 复制前 16B 并强制 from_type1。

| 键 | 按下（40 个十六进制字符＝20B） | 抬起（20B） |
|---|---|---|
| DELETE／C4 | `f801000000000000010000000000000001000000` | `f801000000000000000000000000000001000000` |
| C1 | `6600000000000000010000000000000001000000` | `6600000000000000000000000000000001000000` |
| C2 | `e770000000000000010000000000000001000000` | `e770000000000000000000000000000001000000` |
| C3 | `ec70000000000000010000000000000001000000` | `ec70000000000000000000000000000001000000` |
| PLAY | `f701000000000000010000000000000001000000` | `f701000000000000000000000000000001000000` |
| FN | `9570000000000000010000000000000001000000` | `9570000000000000000000000000000001000000` |

这些是**物理消息 body**，没有 VDF `0d20` 头、command 或附加回复。OSAL 隐藏元数据必须由原分配器维护；O `0xcb6d0..0xcb6e4` 会将 `src==dst` 当作退出控制，不能把目标填成来源。原分配／发送／失败释放由 K `+0x132c/+0x13e0/+0x13f8` 与 O `0xcd7e8..0xcd8c8` 约束；成功交接后不得再释放。此处只给构造合同，没有执行注入，也没有验证按下持续时间或重复行为。

## 4. 首次设置页“Set on the camera”证据与缺口

### 已闭合：物理 DELETE → UI DELETE_ON／OFF

A `0x47cd758` 的原 16B 行是：

```text
23 00 00 00  00 00 09 00  05 00 00 00  01 00 09 00
UI key=0x23   press=0x90000   repeat=0x5   release=0x90001
```

A `0x479c560` 的重定位指向表首 `0x47cd6e8`；`0x16ec294/0x16ec298` 以 16B 步长读 `+4` 按下事件，`0x16ec2dc/0x16ec2e0` 读 `+8` 重复事件，`0x16ec308/0x16ec30c` 读 `+12` 抬起事件。A 名称行 `0x416c760`／字符串 `0x3c31c7a` 将 `0x90000` 命名为 `EVENT_INPUT_TACT_DELETE_ON`，`0x416c770`／`0x3c31c95` 将 `0x90001` 命名为 `EVENT_INPUT_TACT_DELETE_OFF`。因此这条链的码值已闭合：`Infra0x1f8 ↔ UI0x23 → DELETE_ON0x90000 / DELETE_OFF0x90001`。

### 已闭合：页面身份、原截图与事件／页面原表

- A `0x4159790` 是页面枚举行 `<0x18e,13,ptr0x31013f7>`，字符串为 **`scr0103_0023`**；控制器类型名在 `0x313d850`，typeinfo 在 `0x45819f8`。AP94 原日志 `LF63452`、`LF171143` 分别记录进入该页、MENU 从 `scr7096_0017` 返回该页；相邻 `LF63458`／`LF171146` 的原 open_screen 参数含 `0x18e`，见 proof `existing_ap94_evidence`。
- [AP94-r4 step6 原截图](../../../menu-repair-01/runtime/runs/ap94r4object-37305ab2/ap93-step-06-key-1ab.png) 已实际打开复核：上方说明可以用手机完成首次设置，底部为**垃圾桶图标＋Set on the camera**。PNG SHA256=`ccee0fd4b835a727a401114ae4c0e5c4947d3b7a0a3d8ad0a4622d733c304207`；step3 PNG 与其逐字节相同。它们是既有软件绘制页回执，不是本次新输入的结果。
- A **`0x3c8c1fc`** 存在精确原表项 `<event=0x90000,screen=0x18e>`；邻域同列也包括方向／ENTER／MENU 等事件。脚本保留原表邻域；这里只认定原始事件／页面配对值，**该项没有动作 ID 字段，不能单独当作完整键→动作表**。

### 已找到的动作候选，最后一跳未证实

A `0x1c3bfc4..0x1c3bfd4` 通过 GOT `0x4757f58` 绑定处理函数 **`0x23cd1d0`**；`0x1c3bfb8..0x1c3bfc0` 给对应动作槽赋值 **`0x922b`**。该处理函数 `0x23cd1d4` 设置下一页 `0x178`，`0x23cd208` 调用本控制器的 `open_screen@0x23ccd00`；页面名称行 `0x4159630` 将 `0x178` 绑定到 **`scr0103_0009`**。这是可以继续定位机身设置分支的静态候选，未以其函数形状推定 `DELETE_ON` 必定调用它。

作为对照，同一控制器还有 `0x9229 → 0x23cce8c`（GOT `0x4740a50`；`0x1c3bf58..0x1c3bf78`），默认下一页 `0x1cd`（`scr7096_0002`，名称行 `0x4159b80`），条件分支 `0x18b`（`scr0103_0019`，名称行 `0x4159760`）；不能将它仅因邻近 DELETE 事件就标成机身设置动作。

**未定位完整的 `DELETE_ON0x90000 → 动作0x922b（或另一动作）` 分派，也未定位英文提示／垃圾桶图标资源 ID 到动作 ID 的绑定。** `Set on the camera` 不是 appFw 中已定位的明文字符串；本文的英文文案与图标关系来自上述实际 PNG。原页面表、候选动作、截图分别证明不同环节，未连成完整运行因果链。

Sony 的 [首次设置说明](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000888870.html)（2026-11-02 查阅，适用 FX3 Ver.2+；文内手机设置从固件 3.00 起、隐私提示从 7.00 起）支持“不连接手机则进入区域／日期／时间设置”的产品行为；它没有公布私有 UI 枚举、InfraInput 码或动作 ID，不能用它填补上述静态缺口。

## 5. 交付边界

按键数值与 20B 格式已有 A `0x2f8f9f0`、O `0xc9bb4`／`0xcb754`、K `.text+0x13d0`、C `0x49b940`、B `0x53ba0`／`0x13d38c` 的相互印证，可供 Lead 后续将 `0x1f8` 纳入既有受控输入计划。该计划是否准入、实际消费及画面变化由运行链另行验收；本任务没有操作它。

仍未证实：首次设置页最后一跳动作绑定；删除键触发后的原事件消费和下一帧；初始设置完成／拍摄待机／菜单浏览；活动模板记录选择、实机 PCB／SysCon／CP 底层行为。静态 `--check` 通过仅说明这份 proof 能从固定原件重建。
