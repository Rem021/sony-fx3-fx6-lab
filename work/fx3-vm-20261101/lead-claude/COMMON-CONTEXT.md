# FX3 VM 菜单移植 — 工人公共上下文（Lead: Claude）

默认中文。外置盘 /Volumes/KAFU2T（卷 UUID F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B）不在或 UUID 不符就报错退出。

## 背景
原 FX3 固件 AP（AArch64 Linux, appFw.so）在 QEMU 中自然启动；缺失的 CP（Cortex-R/Thumb cpapp）服务由 guest 内的软件模型（LD_PRELOAD 的 fx3-capid-vNN.so）按原协议回复。
当前进度：AP66 中 VDF 0x161（监看 LUT）已被软件模型回复并消费。仍无菜单文字/图形。
AP66 运行日志中下列发往 VDF 服务 0x92840747 的请求被丢弃（"Skip snd to 0x747"，无回复）：
- 0x118 22B `0d201801160001800301000000000000000000000100` source=0x81cf6189 caller=appFw+0x2de6884（serial 行 7629）
- 0x11a 14B `0d201a010e000180010e000e0600` source=0x81cf61c1 caller=appFw+0x2de7264（行 7679）
- 0x159 10B `0d2059010a0001800700` source=0x81cf61c0 caller=appFw+0x2de8550（行 20123）
appFw 运行时基址 0x7f3c429000（caller 0x7f3f210264 = appFw+0x2de7264）。

## 路径（只读）
- 工程根: /Volumes/KAFU2T/AI/Projects/Mac
- AP: work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/appFw.so （其他 AP 库同目录）
- CP: work/sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin （Thumb，加载基址 0x108000，文件偏移 = VA-0x108000）
- capstone Python: work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python
- 先例（证据格式与已确认的协议规律，务必先读）:
  - work/fx3-vm-20261101/menu-repair-01/runtime/monitor-lut-original-proof.json 与 audit_monitor_lut.py（0x161→旧VDF 0x11d→回复0x1161 的完整推导）
  - work/fx3-vm-20261101/menu-repair-01/runtime/vdf161-caller-proof.json / audit_vdf161_caller.py（AP 调用者定位方法）
  - work/fx3-vm-20261101/menu-repair-01/runtime/fx3-vdf-config-proof.json（VDF 类 RTTI/vtable 表）
  - work/fx3-vm-20261101/menu-repair-01/runtime/helpers/fx3-monitor-lut.c, fx3-capid-v21.c（软件模型写法）
  - 最新运行: work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap66lut-ed5764ad/serial.log
  - 报告: reports/2026-11-01-fx3-vm-resumed-repair/uniform-surface.md

## 硬性边界
- 只写你自己的输出目录 work/fx3-vm-20261101/lead-claude/audits/<你的目录>/。
- 不改 runtime/ 下任何文件、不改 STATE.json、不启动 QEMU / run_*.py、不拿 .run.lock（运行链由 Lead 独占）。
- 不修改原件，不清空废纸篓，不 git 操作。
- 结论须有原代码地址+指令证据；推测必须标注"未证实"。不得把"回复格式可构造"说成"功能已实现"。
