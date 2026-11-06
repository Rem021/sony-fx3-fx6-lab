# AP88：CP Backup reset 通过；原关机后段另有断言

**两次原 `Backup_reset_all` 已返回0，远端CP reset等待越过；原关机尚未完成。** 最终运行 `ap88cpr4-e71668cb` 在后段 SeqQueueSetYuvO 的28B VDF0119触发原断言后按规则停止。关键UUD计数4/4、日期2及CP默认值已保存，Lead验收reset并授权AP89以保存RAM作为新启动输入；没有修复或跳过该新断言。


## 冻结合同与捕获

原件审计：[boot-screen-controller](../../work/fx3-vm-20261101/lead-claude/audits/boot-screen-controller/README.md)，只读复核 `--check` 为 93 指令/2 次开屏/3 份 Backup 等待栈/317+2 项投影通过。原 AP 本地 reset 已经完成，缺的是发往 CP `903e0811` 的同步第二步。

捕获模块通过原 `osal_reg_public` 注册唯一公共发送者，不改原模块或内核代码；只有 send 槽，sync 保持 NULL，未知目的保留既有无回复/不 free/返回0行为。首轮 small code model 的 ADRP/RELA275 不被原内核接受，改用 large code model 后实际加载成功；没有修改原内核以迁就新模块。Linux 4.9 上游[arm64 模块加载器](https://github.com/torvalds/linux/blob/v4.9/arch/arm64/kernel/module.c)仅用于核对重定位类别，FX3 接受能力以本轮加载回执为准。

`ap88capture2-061ecbfd` 捕获原 40B：

```text
330000000000000011083e90c2613e80
01000000010000000200000000000000
0200000001000000
```

source=Q=`803e61c2`，op33/selector2/F1/页数字段1，逐字匹配原件推导；Q仅属于本轮，模型不会硬编码沿用。`ap88capture3r-d0263fb2` 保存相同请求与原24B头 `50074e0080ffffff02410100c2613e802800000055555555`。原 `backup.ko+12dc/12ec` 按40B请求分配，`osal_uipc+3248/34e8` 与实际 block_count=2、私有前缀40B共同证明：池块128B，消息头24B、尾canary4B、数据容量60B，logical length=40B。协议页数字段1不等于原来包有4096B可读内容。

捕获只读，不回复、不 free、不写存储。串口存在用户态/printk字节交错，原 receipt 的 serial-only 缺失保留；独立 printk ring 恢复捕获记录后 missing_markers 为空，不篡改旧 receipt。第三次重跑因串口停止 marker 被交错打断走满300s，未增加观察上限。

## CP 软件后端的实际边界

新增 `fx3-cp-backup-reset-v1.ko`，精确校验 destination/op33/全部初始化40B/source与Q/原消息头与canary，只接受本次启动 F1→F4 各一次。全 BK4 header/checksum/索引和选中默认源边界均复验；显式独立 CP profile 使用已有预留区第二 bank `4040d2000 / 1369580B`，首个 AP bank 不重复 reset。它是软件 backing 声明，不把 header 的04000000冒称原 CP/AP 地址等价。

F1 逐项复制原默认值到317项（其中重复项2个、repeat4），F4复制2项；即便本 fixture 为0diff，仍实际复制并逐项读回。初始/预期 bank SHA256 为 `5dc5883fb86d87d14c1c3d530d4d65d903361c189a64edabcd1f636df289f5b7`。事务有 epoch/独占/顺序、重试身份与回滚；未实现 flags/异常索引不返回成功。

每条另分配4096B回复，仅复制初始化40B，+4写真实结果，其余4056B清零；这是与原 CP 复制整个4096B页的可控软件差异。source=003e0811、目的为当次Q。来包按原 destination 的原分配记账释放；回复在 AP 原Q池分配、交原Q消费释放（不冒称原 CP 分配器运行）。分配/发送失败保留未提交阶段，恢复 backing；不重复 free。后续未知消息只捕获、不补回复。

宿主 ASan/UBSan：实际差异复制、全索引/默认界限/checksum/repeat4、F1→F4、重复/错误flag、错误重试身份、分配失败、发送失败rollback、独立回复清尾、source与目的/来包释放记账均通过。另 `fx3-backup-return-v1.so` 只转发原 `Backup_reset_all` 并观察原返回，原 flag/result/errno/调用次数检查通过。宿主通过不等于运行消费通过。

## 运行回执与 GPE 竞争更正

| run | 总时长秒 | 结果 |
|---|---:|---|
| ap88capture-a957c31e | 3.06 | 原内核拒绝RELA275，加载门停止，未启动im |
| ap88capture2-061ecbfd | 27.70 | 原请求捕获后冻结；末次im maps uptime25.37 |
| ap88capture3-c4772f04 | 12.71 | 既有display-v4 libObj近跳转池分配失败(result−3)，诊断门停止 |
| ap88capture3r-d0263fb2 | 301.26 | 捕获完整原头；300s末次im maps uptime299.42 |
| ap88cpreset-a6a5f2b1 | 7.44 | reset前GPE external abort，自动停止；CP reset未执行 |

以上均 qemu_exit=0/process_reaped/inputs_unchanged，独立PID缺席、两把锁已释放；退出0不代表guest健康。失败运行的缺失marker逐项保存在独立 review，未补齐或升级为通过。

AP88故障：原 `libgpe.so+dc88`，raw `026821b8` 是 **STR w2,[x0,x1]**，写入值15到物理f3400280；PC=7f70097c88，LR=7f70097c50，绝不把faultVA当PC。线程MPGRM_GPE0，原worker dcb0→Initialize(db74)，随后还会在dc98写f3400080；另GPE1对应f3400380/f3400180。原表156e0/156e8与原断言名 `void mpgpe::Initialize(mpgpe::Gpe)` 直接支持初始化写语义，具体芯片寄存器官方名称未证实。

现有v14已替换db74入口，但另一线程可先进入原函数，在绑定完成后仍从函数中段写MMIO。不能再把AP86B首轮同为页内280的 external abort 归因为 display DSO 本身；AP88直接证实初始化竞争，AP86B旧现场缺完整PC，属高度吻合同一竞争而非独立PC逐字确认。

Lead批准的v15只在精确 gpe0_info297c0/entrydcb0 与 gpe1_info297e8/entrydce4 的原 `osal_create_thread` 调用前同步完成既有setup/GOT绑定，再原样创建线程；无寄存器模型、无新增硬件返回值。宿主并发检查覆盖“创建早于绑定”、binder在途、未知descriptor透传、失败不启动hardware，及原raster/extent/completion/snapshot guard回归均通过。AP88b-r2 `ap88cpr2-f2e98625` 在12.91s被既有display id15近跳转池分配−3停止，无fatal，GPE0门先armed后原create返回267已保存；GPE1 marker未保存，不补造。Lead同意仅诊断v5将obj_pool可接受距离由64MiB扩至120MiB（A64原±128MiB branch检查仍保留；app/test池仍64MiB、40原点不变），80MiB正反向槽接受/129MiB拒绝/非MAP_FIXED宿主检查通过。AP88b-r3 `ap88cpr3-997a7009` 仍因同诊断门停止，依Lead指示不再扩大诊断工具。最终移除display DSO，新增仅0404原entry/RET两个点的 `preset-context-v1`：原task四字/tid/epoch/退役重读守卫与完整ASM寄存器自测保留，无libObj池；其宿主检查及guest自测均通过。

## 复核入口

- runtime `ap88-request-frozen.json`、`ap88-cp-storage-profile.json`、`ap88-gpe-setup-proof.json`。
- 每轮 `receipt.json`/serial/printk ring和 runtime `<run>-review.json`、`<run>-post11a-requests.json`；请求时间线只覆盖已保存的有界观测，不称全系统无丢失。
- `helpers/cp88-host-check.json`、`backup-return88-host-check.json`、`gpe-early88-host-check.json`。
- 下一关：两次原 reset API 的消费/返回，真实关机后续事件/未知等待；最终保存RAM哈希并单独判定是否关机完成，不以 `backup-after-shutdown.bin` 文件名作证明。


## AP88 最终运行：两次消费与新断言

`ap88cpr4-e71668cb`，总时长27.908s，原300s上限因新fatal自动提前停止。GPE0原线程创建先armed后返回267；没有再发生f3400280 external abort。未保存GPE1创建marker，不强制补建未选用的线程。原0404上下文进入/退役均记录，无display诊断池。

| 原reset | Q | 选中/重复项/复制槽 | before/after FNV64 | 软件发送/来包free | 原API返回 |
|---|---|---|---|---|---|
| F1 | 803e61c5 | 317 / 2 / 323 | 9c88411e0172b013 / 同 | 0 / 0 | index1 flag1 result0 |
| F4 | 803e61c0 | 2 / 0 / 2 | 9c88411e0172b013 / 同 | 0 / 0 | index2 flag4 result0 |

printk ring记录1251/1255保存完整commit；原 `libbackup.so+1ae8` 消费status、原kernel wrapper `.text+154c..157c` 完成reply读取/free/dynamicQ释放后，两个原libbackup API先后返回0。只有消费后的原返回被记录，不把软件send0单独当消费。317+2项在最终RAM再次按原默认源逐项复核，changed均0；native CP未执行。

随后原路径发出 `90040193`/12B `0500a5404200008000000000`、VDF0118 paneloff，以及 `90030001`/12B `0500b8400000000000000000`，仅捕获未增加回复。实际新致命为 **SeqQueueSetYuvO / tid411**：原 `appFw+2dec02c` 构造28B VDF0119并走 `2dec0ec→2de70a8`，保存raw `0d2019011c0001800101000000000000000000000000000000000000`，随后 `infra_wrapper_bb.cpp:870 send_and_wait_cmp_i` → `lib_assert.cpp:30 notify_model_system_error()` → SIGABRT。PC=libc基址7f7b005000+3107c，LR=+31008；信号观测的原调用者为appFw+2ebf424。它不是前述GPE MMIO故障，也不是CP reset失败。未审计该28B变体的成功合同，遵Lead指示只记录、不修复。

本轮 qemu_exit=0 / process_reaped / inputs_unchanged / hostPID缺席 / 两锁独立FREE。原receipt serial-only缺F4 commit一项（字节交错）；printk ring补证后combined required missing为空，**fatal仍存在，末次im maps仅uptime25.47，不能宣称末端健康存活**。无非均匀原菜单PNG或原关机完成回执。

## 保存RAM与AP89准入

已保存 `runtime/runs/ap88cpr4-e71668cb/backup-after-shutdown.bin`，2232320B，SHA256 **38cf44637c44d3f47d7b8541dddf7ecc443e262f40dec3aec59f7b94d5b8b38f**。文件名只沿用任务要求，实际为致命停止时的原Backup预留RAM，未完成关机。

关键直接读回：`02cf1841=04000000`、`02cf1842=04000000`（4/4）；`02cf01b4=02`、`010d01b4=02`。CP第二bankSHA仍为5dc588…，全索引/原默认源投影317+2项均0差异，见 `ap88-backup-final-keys.json`。

原后段仍有额外动作：`285d128..168` 调用后续model任务，`285d064..0c8`清volatile e85并安排其他任务；未穷举整个关机后段的所有Backup写入图，不声称完整持久化。当前可直接复核的UUD准入、日期、CP默认值已经齐备，Lead据此接受条件式AP89 RAM回放。

AP root当前flags100，stored checksum与当前RAM内容不一致，这是原运行写过的活RAM，不能直接冒充有效存储文件交给Backup_load。AP89保持原module/seed/Backup_load1/Save0不变，在它们初始化后、bootin前，仅将保存RAM原样写回同一guest预留范围并全量SHA读回；不改原seed或重算checksum，不称真实掉电持久化。AP89另行记录其原UUD分支、首个controller/presenter创建返回和实际像素。
