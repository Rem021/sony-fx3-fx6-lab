# r34 原生资源边界只读审查

[REPORT.md](REPORT.md)是入口；[DECISION.json](DECISION.json)是限定结论：**分析完成，GPE UI parent可达性unknown，存储未准入，未实现/运行。** [NEXT.md](NEXT.md)列两个有限缺口。

在本目录运行下列离线分析脚本；均先检查目标卷UUID、只写本目录，不执行guest ELF或helper：

```sh
python3 -B extract_inputs.py
python3 -B analyze_native.py
python3 -B reproduce_disassembly.py
python3 -B select_gpl.py
/Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python -B decode_kernel.py
python3 -B decode_admission.py
python3 -B verify_inputs.py
```

libObj.so/dmm.ko是原CPIO未修改审计副本，禁止部署；grm_ma和DmmCfg只从原路径读取并与CPIO对比。GPL片段来自已验证的官方FX3 7.00包，仅作参考，实际kernel使用原7.02 Image逐字节绑定。capstone5.0.7/pyelftools只解析字节，不仿真或执行指令。

MEMBER-BINDING、CONFIG-403、LIBOBJ-FUNCTION-BOUNDARIES、MA-DISPATCH-TABLE、KERNEL-EXACT和DISASSEMBLY-RECEIPT保存实际来源/地址/字节；receipts目录保存最终复现stdout/stderr/exit；INPUTS前后和SHA256SUMS供复核。共享项目README不列技术冻结，也没有修改。
