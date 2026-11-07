# 原厂路线“忠实配置”设计（native-faithful profile）

属 [Big6 依赖闭包报告](README.md) §4 的落地设计。**只是设计说明，未编译、未打包、未运行；不修改 DeepSeek 的 `/tmp/libgrm-fbinit25-*.c`。** 运行线若采用，应自行在其文件或新文件中实现，并按单变量原则分轮引入。

## 0. 目标

在真 FX6 `appFw.so` 路线上，shim 只承担“VM 没有的硬件”（GPE/OSD 显存、`/dev/ma`、`/dev/backup` 等）的最小替身，**不替原厂决定颜色、图像、可见性和锁语义**。判据：原厂代码画什么，帧里就是什么；原厂代码失败，日志里就能看到失败。

## 1. 编译开关与日志约定

- 建议单一开关 `FX6_NATIVE_FAITHFUL`（编译期宏或环境变量），关闭时行为与 301 完全一致，便于对照。
- 每个“替身”函数保留一个计数器，并在每次 `FX6_OSD_FLUSH` 行尾追加：
  `subst_color=<n> subst_image=<n> forced_render=<n> skipped_node=<n> lock_bypass=<n>`。
  原厂帧验收要求这些计数全部为 0。

## 2. 逐函数规则

| 301 中的函数/行为 | 忠实配置下 | 理由 |
|---|---|---|
| `GRM_gpermFillrect` 颜色替换（`0xFF101820`、伪随机蓝、焦点色、`g_big6_layout` 判定） | 删除替换；`a==0` 时按 blend 处理：SRC/COPY → 写 0，OVER → 不写；记录 blend 值 | 原厂透明层不可被涂色；避免全零帧被伪装 |
| `GRM_gpermFillrect` 参数解析 | 保留现有偏移（`fp+0x08..0x13`），新增打印 blend 字段原值，便于确认 ABI | 现偏移来自 241–271 实测 |
| `GRM_gpermRectblit` | 读取 src 矩形宽高与 dst 宽高，不等时做最近邻缩放；按 `info+0x1c` 解码（2=ARGB8888，4/glyph=8-bit 覆盖度，其余格式先计数并跳过，不猜）；glyph 颜色取调用方提供的前景色（需确认 blit_param 中颜色字段，未确认前计数为 `subst_color`） | 原厂九宫格/拉伸背景与彩色文字 |
| `BitmapImpl::create`（两个重载） | 只替换内存来源；保留 `info+0x1c` 原格式，pitch 按 `BMP_PixelFormatToBytesPerPixel` 表（`0:非法,1:2,2:4,3:2,4:4,5:1`）计算 | 防止 268 类行距错位 |
| `Render2DWalker::skipRendering` | 不导出（使用原函数） | 原厂隐藏层不应出现 |
| `ImageElementBase::registerImage/unregisterImage` | 不导出（使用原函数）；若崩溃，先记录 `self+0x68/0x78/0xd0` 再中止 | 不再挂自制准星 |
| `ensure_icon_raw_img`、`g_icon_*` | 排除 | 仅为 AdjChk 准星 |
| `app_adjchk_ui::*`、`g_big6_layout`、`k_*_opts`、`fb_draw_*`、`glyph5x7` | 排除 | 自建 Big6 专用 |
| `poll_key_gate`、`FX6_MENU_INPUT_ACK` | 保留门本身，但日志改名 `FX6_HOSTGATE_ACK`，不再修改任何画面状态 | ACK 仅表示宿主门收到 |
| `LinearList::remove`、`TreeNode::*`、`NodeWalkerBase::visit*`、`TreeWalker::traverse` | 改为“记录后调用原函数”；命中无效指针时打印并 `abort()`（走现有 `FX6_ABORT_BT`） | 原厂 presenter 构造缺陷必须暴露 |
| `HashRecord::decRef/release`、`XDBTable::releaseBankItem`、`GenerateImageCommand::cancelListen` | 第一轮保留（避免回到 libra 生命周期崩溃），但每次调用计数并定期打印 | 先量化泄漏，再决定是否恢复原函数 |
| `ImageData::detach`、`TextSprite::ImageDataContainer::onImageLoad` 守卫 | 保留 | 267 已证明必要，且不改像素 |
| `GetFlag` 守卫、`pthread_mutex_*` 空桩、`ObjShLock::Lock` 补丁、`0x20efbb8` 改写 | 移除，改由 §3 生命周期补齐 | 见闭包报告 §2.3 |
| `0xc09e50` NOP（start_utimer） | 第二步移除（MWF 补齐并稳定后单独一轮） | 恢复 App 周期消息 |
| `Backup_*` | 保留“不写内存/返回 0”的保守行为，但逐函数记录 `id` 与调用者 LR | 为可分配按键等 ID 建立清单（闭包报告 Q5） |
| `FBResourceManager::initialize`、`FrameBuffer::initialize` 跳过、`getOnscreen/getOffscreen`、`update/swap`、`GRM_fbrmUpdate`、`gperm*Flush` | 保留 | VM 无 `/dev/gpe`，这是显示桥本身 |
| `GRM_fbrmRegisterChangeFramebufferCb` 立即回调 1024×540 | 保留 | 241 证实为必要 |

## 3. 生命周期补齐（launcher 侧，草案）

**前提**：闭包报告 Q1（`MWF_Init` 参数）确认后再实施。以下为结构示意，参数待定处以注释标出。

```c
/* 放在全部 pre() 之后、init("AppConfig.so") 之前；只执行一次。 */
static void fx6_mwf_lifecycle(void) {
    void *mwf = dlopen("/usr/lib/libMWF.so", RTLD_NOW | RTLD_GLOBAL);
    void **mon_err = mwf ? (void **)dlsym(mwf, "_ZN3MWF6RsrcDP10smp_monErrE") : 0;
    void *init = mwf ? dlsym(mwf, "MWF_Init") : 0;
    fprintf(stderr, "FX6_MWF_PRE init=%p smp_monErr@%p=%p\n",
            init, (void *)mon_err, mon_err ? *mon_err : 0);
    if (!init || (mon_err && *mon_err)) return;      /* 已初始化则不重复 */
    /* TODO(Q1): 按 im.elf 实际调用形态传参；未确认前不要猜参数。 */
    int rc = ((int (*)(void))init)();
    fprintf(stderr, "FX6_MWF_POST rc=%d smp_monErr=%p\n", rc, mon_err ? *mon_err : 0);
}
```

验收（与闭包报告 §2.2 预测一一对应）：
1. `FX6_MWF_POST` 中 `smp_monErr` 非空；
2. 去掉三层掩码后不再出现 `pthread_mutex_lock` 低地址参数；
3. 首次看到 `RsrcAcsr` 原始错误文本（若有），并据此决定下一步；
4. 若 2 不成立，记录 `ObjShLock` 对象地址与其 service 字段，交 Codex 线核对 Q2。

**不在同一轮做**：`KikiLogGenerator_init`（需要 `/dev/usb/kikilog` 248:10，节点存在与否未证）、恢复 `start_utimer`、触发泵。

## 4. 帧触发泵（条件性设计）

只有当 Q3 证实“`GRM_fbrmRegisterTriggerFrameworkCb` 注册的回调由 `FBResourceManager` 的内部线程/中断驱动，而该线程因 `initialize` 被跳过而不存在”时才需要。

- 在 shim 中拦截 `GRM_fbrmRegisterTriggerFrameworkCb`：先转发给真函数（保持其内部登记），同时保存 `cb/user`。
- 启动一个低频（例如 25 Hz，与现有 flush 节拍一致）线程，按 Q3 确认的参数形态调用 `cb`。
- 每次调用记录序号；**回调的参数结构未确认前不实现**，避免向 App 投递伪造内容。
- 验收：App 侧在不依赖 AdjChk 主循环的情况下出现 `FX6_GPE_*` 原语，且 `subst_*` 计数为 0。

## 5. 与现有门禁的关系

- 不改变 DeepSeek 的运行预算、QMP 抓帧方式和 7 键门。
- 忠实配置下帧可能长期为全零——这是**真实状态**，比 301 的替换色更有诊断价值。
- 271 的自建 Big6 继续作为“管线能力演示”，与原厂路线结果分开归档、分开命名。
