# 索尼电影机固件安全与引导架构研究实验室

[![English](https://img.shields.io/badge/语言-English-0969da?style=flat)](./README.md)
[![版本](https://img.shields.io/badge/版本-v1.0.0-1a7f37?style=flat)](https://github.com/Rem021/sony-fx3-fx6-lab/releases/tag/v1.0.0)
[![审计模式](https://img.shields.io/badge/审计范围-只读静态结构分析-8250df?style=flat)](#一五阶段安全引导流水线)
[![合规声明](https://img.shields.io/badge/合规原则-净室逆向与互操作研究-0969da?style=flat)](#五合规与免责声明)
[![开源协议](https://img.shields.io/badge/开源协议-MIT-656d76?style=flat)](./LICENSE)

> **语言切换**：[**👉 Switch to Pure English Documentation (`README.md`)**](./README.md)

面向索尼电影摄影机系列的只读固件容器静态分析工具集与硬件信任链参考文档。本仓库提供净室实现的文件头解析脚本、分区结构说明以及加密边界审计报告，不包含任何专有二进制固件或加密密钥。

---

## 一、五阶段安全引导流水线

官方固件升级容器从最外层升级包直至相机操作系统根分区，采用硬件锚定的五阶段逐级验签机制：

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="./assets/boot-pipeline-zh-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="./assets/boot-pipeline-zh-light.svg">
    <img alt="五阶段安全引导流水线" src="./assets/boot-pipeline-zh-light.svg" width="100%">
  </picture>
</p>

| 引导阶段 | 核心组件 | 安全校验职责 |
| :--- | :--- | :--- |
| **阶段 01** | 固件升级容器 | 校验外层升级包魔数标识、机型代号与文件头完整性校验和。 |
| **阶段 02** | 一级引导程序 | 依托芯片只读掩膜与硬件熔丝密钥，验证一级引导程序数字签名。 |
| **阶段 03** | 安全监控固件 | 初始化安全世界隔离环境，保护底层硬件密钥与密码学加速引擎。 |
| **阶段 04** | 二级引导程序 | 在移交执行权前校验系统内核镜像摘要与硬件设备树配置。 |
| **阶段 05** | 相机操作系统 | 挂载通过完整性校验的只读根文件系统，启动核心影像服务进程。 |

---

## 二、核心分析模块

| 模块名称 | 功能说明 | 输出形式 |
| :--- | :--- | :--- |
| **容器文件头解析器** | 以只读方式解析升级包文件头、数据块偏移量与版本元数据。 | 结构化数据与表格报告 |
| **信息熵与分段扫描器** | 计算滑动窗口香农熵，区分压缩文件系统分区与高熵加密载荷。 | 分段映射图与统计摘要 |
| **信任链边界审计文档** | 梳理从芯片只读引导区、安全监控器到系统内核的验签传递边界。 | 架构安全审计报告 |
| **净室合成向量测试集** | 使用合成二进制样本验证解析器准确性，无需依赖任何厂商固件文件。 | 确定性单元测试报告 |

---

## 三、快速上手

### 1. 运行净室自测套件

使用内置合成测试样本验证所有静态解析模块（无需准备任何真实固件文件）：

```bash
python3 -m unittest discover -s tests -v
```

### 2. 只读解析本地固件升级包

对本地下载的官方固件容器进行非破坏性结构剖析并导出报告：

```bash
python3 tools/inspect_firmware.py --input /path/to/BodyData.dat --json > report.json
```

---

## 四、仓库目录结构

```text
sony-fx3-fx6-lab/
├── assets/                   # 自适应深浅色矢量流程图
├── docs/                     # 引导信任链与分区边界规范文档
├── tools/                    # 只读文件头解析与信息熵分析脚本
├── tests/                    # 净室合成样本单元测试集
├── README.md                 # 纯英文说明文档（默认首页）
└── README.zh-CN.md           # 纯中文说明文档
```

---

## 五、合规与免责声明

- **零专有代码与密钥**：本仓库**不包含任何厂商二进制代码、固件镜像、私有密钥或未公开工程资料**。
- **安全性与互操作研究**：所有文档与只读分析脚本均在净室规范下独立编写，仅用于硬件安全审计、互操作性研究与技术教学参考。
- **不提供绕过工具**：本项目不提供任何用于绕过数字签名校验或篡改相机固件的工具。
