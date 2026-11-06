# AP95 删除/C4 与逐步界面测试

2026-11-02。第一轮完整请求300秒，实际301.146秒，QEMU生命周期检查通过（原应用assert，见末尾更正）；删除键成功进入机身设置。拍摄待机和 MENU 菜单尚未验收。

## 候选与检查

基线 AP94-r4；新输入 provider v6 显式启用经 Lead 批准的 DELETE/C4 0x1f8，其他模型不改。七键、30步、50..200ms、原20B包、真实 keyworker、原分配/发送/接收释放由 ASan/UBSan 检查；宿主12B控制区回读与 guest-done 检查通过。删除审计 --check 只读重建1629条原指令和558条重定位一致。CPIO仅 simulation/fx3-rm-empty-provider-v3-setup.so 成员体变化，init/GPE19r4/backend5/OSDv6/原件保持。

## 第一轮 ap95v6delete-ed48a6ed

QEMU退出0、process_reaped、独立PID不存在、两锁FREE、所有输入SHA独立重核、missing[]、旧分类未检出panic/symbol lookup，但原应用assert后停止，见末尾更正。im228结尾完整maps在uptime291.03；706条可解析GPE记录，未知/交错记录单列，不声称无损。24个合成down/up、24个原输入接收、12个guest_done、12张逐步物理PNG与原committed ring SHA匹配；全部provider分配lease原接收者释放0且恰好一次。

| step/key | 实际查看画面 | 下一键理由 | PNG |
|---|---|---|---|
| 1/0x3 | 上键后较晚原帧标题 Language；逐步 +2s 快照仍为旧日语帧，补看当前 ring 已确认英文 | 确认当前 English 选项，进入首次设置隐私页 | [ap95-step-01-key-003.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap95v6delete-ed48a6ed/ap95-step-01-key-003.png) |
| 2/0x1ac | 英文生物识别隐私说明，含 QR 与 sony.net/dics/privacy 链接，底部 MENU 返回提示 | 确认已阅读，继续原首次设置流程 | [ap95-step-02-key-1ac.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap95v6delete-ed48a6ed/ap95-step-02-key-1ac.png) |
| 3/0x1ac | 手机首次设置引导，文字 You can perform initial camera settings with your smartphone，底部垃圾桶图标 Set on the camera | 按画面垃圾桶提示使用已审计 DELETE/C4 0x1f8，选择在相机上完成设置 | [ap95-step-03-key-1ac.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap95v6delete-ed48a6ed/ap95-step-03-key-1ac.png) |
| 4/0x1f8 | 删除键后出现 Set Area/Date/Time，对话框含 Enter 与 Cancel | 确认 Enter 进入区域日期时间设置 | [ap95-step-04-key-1f8.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap95v6delete-ed48a6ed/ap95-step-04-key-1f8.png) |
| 5/0x1ac | Area Setting，Tokyo/Seoul，2021-1-1 12:00 AM GMT+9.0；底部 OK | 接受模拟器本轮默认区域，按 OK 继续 | [ap95-step-05-key-1ac.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap95v6delete-ed48a6ed/ap95-step-05-key-1ac.png) |
| 6/0x1ac | Date Format，列表 Y-M-D、M(English)-D-Y、M-D-Y、D-M-Y | 接受原默认日期格式，继续下一设置页 | [ap95-step-06-key-1ac.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap95v6delete-ed48a6ed/ap95-step-06-key-1ac.png) |
| 7/0x1ac | Date/Time，当前 2021-1-1 12:00:00 AM，底部 OK 与 MENU Cancel | 接受本轮虚拟机默认日期时间，按 OK 完成设置 | [ap95-step-07-key-1ac.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap95v6delete-ed48a6ed/ap95-step-07-key-1ac.png) |
| 8/0x1ac | 提示三脚架拍摄可将 Auto Power OFF Temp 设为 High，选项 Set now / Set later | 下移到 Set later，先完成首次设置并保留默认温度选项 | [ap95-step-08-key-1ac.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap95v6delete-ed48a6ed/ap95-step-08-key-1ac.png) |
| 9/0x30 | 下键后仍在 Auto Power OFF Temp 的 Set now / Set later 页；当前导出未显示可辨识的选中高亮 | 按确定确认刚才下移的 Set later 选择，并以随后的实际页面验证 | [ap95-step-09-key-030.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap95v6delete-ed48a6ed/ap95-step-09-key-030.png) |
| 10/0x1ac | 原页标题 Would you like to set up HOME for use，当前 +2s PNG 未显示清晰的选项文本 | 使用白名单确定键尝试原默认选项，下一帧确认实际去向 | [ap95-step-10-key-1ac.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap95v6delete-ed48a6ed/ap95-step-10-key-1ac.png) |
| 11/0x1ac | Creators App 信息页：说明可用于图像传输和遥控拍摄，可从 MENU 网络 Smartphone Connection 设置 | 关闭提示继续进入拍摄界面 | [ap95-step-11-key-1ac.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap95v6delete-ed48a6ed/ap95-step-11-key-1ac.png) |
| 12/0x1ac | 确定后早期截图仍为 Creators App 信息页，原开屏日志已继续到 screen0；拍摄待机画面尚未读回证实 | 尝试 MENU 检查首次设置退出后的菜单响应，以菜单截图确认是否可用 | [ap95-step-12-key-1ac.png](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap95v6delete-ed48a6ed/ap95-step-12-key-1ac.png) |

首步 +2秒物理PNG仍是旧日语语言帧。实际另查看 osd-frame-001380-format0-RGBA-opaque.png 的 Language 标题，才发第2步确定；不是将旧帧宣称为变化成功。

第13步 MENU 在宿主控制区写入并读回，但 guest 未见 step13 发包/完成，也无该步截图；300秒时限已到。不能把单步文件或宿主write当作菜单输入消费。第12步后原开屏日志到screen0，不能据此替代可见拍摄待机。

[独立复核](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap95v6delete-ed48a6ed-ap95-review.json) · [每次选键与原截图SHA](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap95v6delete-ed48a6ed-visual-decisions.json)

## 后续

同候选另开300秒轮次，继续逐图放行以留足待机/MENU与方向浏览窗口；不改原件、旧runs或已冻结helper。遇未知输入、新绘制拒绝或异常即停。

本轮在线核对了 [QEMU QMP 参考](https://www.qemu.org/docs/master/interop/qemu-qmp-ref.html) 与 [Sony 首次设置说明](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000888870.html)；这些文档只说明通用接口或产品流程，不替代私有按钮码、软件模型或当前画面证据。

## 第二轮配置切换与第三轮600秒结果

`ap95v6r2ui-84d0cc84` 在Lead将窗口改为600秒后，于无输入阶段正常停在53.541秒；exit0/reaped/PID不存在/双锁FREE/输入SHA一致。missing为新目标与nearest_v2两个尚未到达的标记，不算完整UI验收。

`ap95v6r3ui600-3715c225` 请求600秒、实际601.070秒，完整QEMU生命周期检查通过，原应用存在assert：exit0/reaped/PID不存在/双锁FREE/输入SHA独立核回/missing[]，无新GPE拒绝；原应用assert已补检。再次完成12个按键步骤并查看全部PNG；宿主第13条MENU写回成功，但原worker始终无KEY_CACHE13/SYNTH_KEY13/DONE13，终止时控制页cmd13/done12。这复现首轮现象，不能仅归因为300秒不足，也不能据缺少日志直接宣称线程已退出。

原开屏0不替代拍摄待机；较晚独立PNG仍为Creators App说明，待机与菜单均未验收，未发送后续导航。菜单前只读Backup快照2232320B保存于该run的backup-after-setup.bin，SHA256 `191924ef39d996171ae06ab4ca85e249b655b16db6b68fd1e2ddea45efc60bdc`；回执明确可见待机未证实、raw liveRAM并非已验证存储文件。

数值键解析位于runtime/ap95v6r3ui600-3715c225-backup-after-setup-keys.json；25664个AP参数可解析，相对原回放输入20项改变。语言/地区的Backup键语义仍需绑定原getter映射，不能将同名BKID枚举直接当低16位BackupID；日期状态原键02cf01b4从2到0，010d01b4仍2，UUD1841/1842仍4/4，枚举语义另以原代码核对。

Lead msg_48dccc7b7d3d授权AP96：以本快照作下一次Backup RAM输入、同模型600秒、输入worker只读逐轮门控诊断和独立/proc线程状态/stack/wchan，开机稳定后MENU作为step1；本轮不扩大协议模型。

## 健康结论更正（以此节与review-v3为准）

原先复核只搜索panic/exception/symbol lookup，遗漏assert。首轮和600秒轮分别LF203342/LF160777出现`assert at infra_wrapper_bb.cpp:870`，随后`FX3_SIGNAL_OBSERVE(api=assert,signal=6)`与`lib_assert.cpp:30 Assertion false`；因此撤回“guest健康/无fatal”。QEMU退出0、进程回收、输入不变与锁释放是独立成立的生命周期回执；im.elf maps仍存在也不证明应用仍执行。已生成两轮`*-review-v3.json`，`lifecycle_pass=true,health_pass=false,native_application_failed=true`。完整原证据在`runtime/ap95-ap96-native-assert-correction.json`；旧run和旧复核文件原样保留，不改写历史。
