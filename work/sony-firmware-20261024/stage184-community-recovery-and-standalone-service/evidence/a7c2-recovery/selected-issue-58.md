https://github.com/QAQLeonard/a7c2-fl23-research/issues/58
3.0.3 一键安装后，机身快速切换到自定义槽位预览卡住，切走再切回恢复
### 环境
- A7C II (ILCE-7CM2) 固件 2.01
- 工具 3.0.3 原版一键安装
- 写入的是项目自带配对库里的 .a7look（未自改）
- 六个自定义槽位 base look 均为 ST

### 现象
在相机机身上用拨轮快速切换到某个自定义创意外观槽位时，实时预览画面卡住 / 不刷新；切到 ST 或其他 look 再切回该槽位即可正常显示。稳定复现。

### 疑问
这个症状看起来正是 `upload-retry-v4` / `prepare-preview-retry` 要修的那条切换上传路径。想确认：

1. 3.0.3 的一键安装走的是哪套布局（带 preview-retry 的 full7-v4，还是不带的）？
2. `prepare-preview-retry` 这个补丁是否已经并入正式安装流程？
3. 当前版本能否手动补打这个补丁？
