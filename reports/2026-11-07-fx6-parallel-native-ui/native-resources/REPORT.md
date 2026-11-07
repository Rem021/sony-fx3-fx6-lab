# FX6 原厂 UI 控件归属复核（2026-11-07）

结论：现有报告 10.7 给出的 `scr7286_0001`、`rep_shooting`、`rep_menu` 及其控件表属于本地 79 MB FX3 `appFw.so`，不能套到正在试跑的 50.5 MB FX6 `appFw.so`。本轮已在真实 FX6 donor 中重新确认三个 presenter 构造入口和 **489 条有效控件描述符**；未执行 guest，也未证明屏幕已经打开。

## 输入身份与范围

| 输入 | bytes | SHA-256 |
|---|---:|---|
| FX6 donor `nflasha15-files/lib/appFw.so` | 50,520,424 | `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` |
| stage2 / fx3-audit 的 FX3 `appFw.so` | 79,015,712 | `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f` |

FX3 身份交叉依据：`/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/fx3-audit/asset-audit.json` 的 `files[17]`（`partition=15`、`path=/lib/appFw.so`、`bytes=79015712`、`sha256=545c5053...`），其 `output` 为 `/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so`。本轮直接重哈此原件和表中 stage2 参考文件，两者均与 owning manifest 一致。两者不是同一个文件 strip 前后的版本；其入口、逻辑和字符串族均不同。

本轮仅写本目录。未启动、暂停或控制虚拟机；未改共享 donor、候选 CPIO、shim 或前端；没有复制固件。

## 原有 VMA 的问题

真实 FX6 的第二个 `PT_LOAD` 从 VMA `0x2911150` 开始，文件映射在 `0x303d978` 结束，其后是零初始化区域。原报告表地址 `0x451ab28`、`0x44af468`、`0x452ac48`、`0x44c0978`、`0x44c20d8` **全部落在 FX6 的 zero-fill / BSS 范围**，不是该 donor 的文件内静态描述符。

79 MB FX3 文件含 `scr7286_0001`、`No113_SelectButton`、`rep_menu`、`rep_shooting_presenter`；50.5 MB FX6 文件不含这些精确名字。仅凭它们不能把 FX3 布局称为 FX6 原厂布局。

## 在真实 FX6 中复核的入口

所有 VMA 均相对上方 `a1c58b69...` 的 ELF load base；运行时必须加真实模块基址。

| 真实类 | 构造入口 | 构造断言名引用 ADRP | 控件表 GOT | 表 VMA | count / stride |
|---|---|---|---|---|---|
| `procam_big6_menu_home_presenter` | `0xde10f4` | `0xde1228` | `0x2ee57b8` | `0x2e9e210` | 98 / `0x48` |
| `procam_shooting_presenter` | `0xdd3df8` | `0xdd3f88` | `0x2eee798` | `0x2e94910` | 356 / `0x48` |
| `procam_menu_layer_1st_presenter` | `0xdd7470` | `0xdd7588` | `0x2eec5a0` | `0x2ea02f8` | 35 / `0x48` |

复核方法：构造函数 prologue、函数体中引用的完整构造断言名、`mov x3,#count`、GOT 的 `R_AARCH64_RELATIVE` addend，以及所有 `row + 8` 指向有效 `No...` 控件名，五项相互约束。脚本均验证这些条件；JSON 保存其地址和全部控件名序列的 SHA-256，避免导出整套专有资源。

Big6 表含 `No463_BLOCK_TOUCH`、`No1071_TIME_CODE_VALUE`、`No210_AUDIO_LEVEL_METER`，并以 `No101_BUTTON_01` / `No2_MESSAGE_REQUEST` 等结束；其真实数量为 98，和先前 FX3 表的 57 不同。

上述构造形态需要已有 `i_view&`、`i_caution_resource_getter&`、display-layer 和 screen-id；不得把构造入口当作无参 `open_screen()` 直接调用。本轮未定位且未证明可独立调用的 controller `open_screen`，也没有推导控件坐标。

## 资源闭包（仅 donor 文件层）

真实 UI worker `appFw + 0xc0b470` 在 `+0xc0b494` 设置 `/usr/share/app/`，在 `+0xc0b4d4` 设置 `global.xdb`，再于 `+0xc0b520` / `+0xc0b528` 构造应用并进入主循环。这一链与前述真实 FX6 presenter 命名相符。

脚本从 donor 的 `global.xdb`、`fontlist.dat` 解析声明引用，加上数据库与语言入口共核验 **70 个资源文件，缺失 0 个**，并记录 bytes / SHA-256。范围包括 image/color/string UXC、字体、语言表。本轮未核验这些文件是否原样装入 Candidate 287，也未证明 guest 的路径、mount、read 权限和数据库加载成功。

## 最小下一步

1. 保持当前真 `appFw` 启动工作继续，由运行负责人独占 VM；先在真实 FX6 `procam_big6_menu_home_presenter +0xde10f4` 和表消费处观察调用，记录模块 SHA、base、count 与 table pointer。
2. 只有构造与真实数据库加载被观察到后，再通过应用现有 screen manager / 原生按键入口打开 Big6；不要移植 FX3 `scr7286` 的地址或手动摆放控件来替代结果。
3. 运行收据须将原始 guest framebuffer 绑定到同一 run 和按键序列。网页 Python 画布可作为设计参考，不能替代这一步。

## 重跑

```sh
python3 -B audit_native_resources.py \
  --fx6 /path/to/fx6/nflasha15-files/lib/appFw.so \
  --reference /path/to/fx3/nflasha15/lib/appFw.so \
  --app-dir /path/to/fx6/nflasha15-files/share/app \
  > audit-result.json
```

只依赖 Python 标准库，输入 SHA 不匹配时退出，不输出任何固件或资源载荷。本轮实物重跑通过；文件级静态验证不等于 guest 运行、菜单可用或实机验收。
