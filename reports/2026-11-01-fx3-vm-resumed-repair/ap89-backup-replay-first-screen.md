# AP89：RAM 重启越过 UUD，首屏创建；像素仍被 GPE 合同阻塞

**原 UUD 返回0，mode/option=1/0，后续 screen 的 controller/presenter 已创建；尚无非均匀菜单像素。** 本轮77条完整 GPE 记录中3次FillRect成功，73次BitBlit及最终Flush被现模型拒绝。没有注入ready事件、补画界面或放宽资源边界。

## 输入与原启动

Lead验收[AP88两次原reset返回0](ap88-cp-backup-reset-shutdown.md)，授权关键UUD4/4、日期2、CP默认值齐备后，以保存RAM模拟下一次启动。输入2232320B，SHA256：

38cf44637c44d3f47d7b8541dddf7ecc443e262f40dec3aec59f7b94d5b8b38f

原backup.ko的Load1启动路径会把seed读入预留RAM（init+c0→backupfile_load→backupfile_init+65e8→vfs_read+6304，随后Data_init），因此单纯CPU启动前增加QEMU loader会被覆盖。原模块/seed/Load1/Save0保持原样；保存的活RAM flags100且stored checksum已失配，没有把它冒充有效存储文件。

首轮 ap89replay-b736403b 在4.823s、bootin前被工具门停止：原BusyBox无sha256sum applet且dd不支持conv选项，dd显示usage后返回1，未写RAM或启动im。该失败及缺失marker保留。

第二轮使用独立有界 guest helper。它先校验固定源长与完整SHA，再检查已有两bank头，只映射404000000/221000预留区，保存旧RAM、原样复制、撤映射后以只读映射重读完整SHA；失败恢复旧RAM。未修改原seed、checksum或任何协议字段。ASan/UBSan覆盖SHA padding与完整输入、部分读、错误源/短文件/错误bank和实际回滚，均通过。

helper后有5秒仅用于启动前输入验收的有界窗口。宿主见VERIFIED即QMP stop，物理pmemsave完整区域后核对SHA，并确认原bootin marker尚未出现，再cont。guest重映射SHA与独立QMP SHA均逐字匹配上值，启动前条件为true；不是只凭copy成功。

候选：runtime/ap89-r2-backup-helper-replay/candidate.json。协议、GPE v15、CP reset、headless/lifetime全部沿AP88r4；最小preset provider只增加4个被动原点，记录UUD分支、开屏入口、controller init返回和presenter factory返回，无libObj诊断池。原指令与寄存器自测通过。

## 运行回执

run **ap89r2replay-a55f292d**，原定300秒，在177.411秒由既有软件OSD pair诊断期限sequence524停止；非新fatal，没有提高时长上限。

| 项目 | 结果 |
|---|---|
| QEMU / 回收 / 输入 | exit0 / process_reaped / inputs_unchanged |
| 独立收尾 | host PID缺席，两把锁均FREE |
| marker / fatal | receipt和combined missing均空；fatal空 |
| 原im末次完整maps | PID232，guest uptime161.91，包含/usr/bin/im.elf |
| 重放证据 | guest remap SHA、QMP启动前物理SHA一致 |
| UUD与reset | native_update_return0，mode143=1、option145=0；原reset API与UUD协议commit均0次 |

原开屏顺序及原表名称：

| 一次调用的三个引用参数 | 新目标 | 原返回证据 |
|---|---|---|
| 407 / 2ae / 407 | 2ae scr0039_boot | controller init与presenter factory返回 |
| 2ae / fa / 2ae | fa scr0099_0001 | controller init与presenter factory返回 |
| fa / 2c7 / fa | 2c7 dlg_dbl021_base | controller init与presenter factory返回 |

名称来自固定原appFw表，controller/presenter返回点分别为218ffe8/218fff4。这里证明对象创建与原初始化返回，不能仅凭ID将fa命名为拍摄主界面，也不能把一个三参数调用写成三次开屏。

## GPE：原界面确实提出绘制，模型尚未执行这些BitBlit

77条完整marker，序号0..76，无不完整marker；另保存73条完整144B拒绝参数。这是现有适配器已绑定入口的marker统计，不覆盖尚未绑定的StretchRotateBlit等原入口。地址列表示实际请求地址是否在当前545区43feb5000/140000内，不代替完整跨度/租约验证。

| op | dst/src fmt | flags | dst在545 | src在545 | result/reason | 条数 |
|---|---|---|---|---|---|---:|
| FillRect | 0 / — | ff | 是 | — | 0 / OK | 1 |
| FillRect | 0 / — | 1ff | 是 | — | 0 / OK | 2 |
| BitBlit | 0 / 0 | 1000000000001 | 是 | 否 | 5 / UNSUPPORTED | 64 |
| BitBlit | 0 / 2 | 10000000e0001 | 是 | 否 | 5 / UNSUPPORTED | 9 |
| Flush | — | 0 | — | — | 5 / UNSUPPORTED | 1 |

reason2是UNSUPPORTED，不唯一指出失败阶段。实际参数有q115=1（另有q117=0e的变体）、src_fmt2→dst_fmt0，以及41052…/41092…/410c6…等545以外的源；这些各自均超出现模型。不能把所有拒绝只归因于DMM范围。原日志还显示资源heap410524000–410924000，但这不是已经建立的GPE租约/注册合同，不据此直接开放任意物理读取。

前一次BitBlit失败会触发现有sticky raster_failed规则，故末次Flush拒绝；没有伪造成功完成。下一步需要分别闭合真实资源DMM生命周期、q115/116语义及fmt2的原格式/CLUT，再决定后端扩展。

## 真实读回结论

通过原lease与软件ring保存315个可复核物理快照、74张PNG；这些已读样本只有一个像素SHA，均为均匀黑，没有非均匀PNG。ring允许覆盖未采到的中间帧，不把315个样本说成所有生产帧。

独立最终QMP物理读回545后备，payload从+100开始，640×480、stride640、模型fmt0：307200个16位像素全部000f，唯一像素值数1；payload SHA256为：

a058732fe374201a91ab2ee9885f3fc1c34241a0e355d1717ad9f96b63db8db9

因此本轮未满足非均匀菜单像素与输入反馈闭环验收，也没有可嵌入的首张非均匀图。screen创建、GPE请求、软件执行和可见菜单分别保留结论。

## 复核入口与参考

- runtime/ap89r2replay-a55f292d-review.json、ap89-gpe-command-statistics.json、同run的post11a请求时间线。
- runs/ap89r2replay-a55f292d/ap89-host-input-readback.json、ap89-input-before-AP.bin、receipt.json、serial.log、printk ring。
- 同run的osd-ring-readback.json、原raw/PNG和gpe-surface-545.bin；全部历史run与原失败回执不改。
- [A7C II维护者最新README](https://github.com/chocotan/a7c2-qemu/blob/master/README.md)与[研究进展](https://github.com/chocotan/a7c2-qemu/blob/master/docs/tech/2026-10-31-current-progress.md)已于2026-11-02重新联网核对：其菜单与部分设置恢复有独立成果，原拍照录像仍未贯通。这里只参考分层验收和启动/持久化方法，不借用A7C2地址、像素或运行回执证明FX3。

Lead复核接受本轮为“原厂正常开机首屏创建通过、像素未达”；下一步等待gpe-fmt2-resource-extents审计和AP90/GPE v16合同，不以本轮替代菜单像素验收。
