#!/bin/zsh
# Local FX6-on-FX3 VM Big6 HOME menu interactive launcher
set -euo pipefail
if (( $# > 1 )) || { (( $# == 1 )) && [[ "$1" != --check ]]; }; then
  print -u2 '仅支持双击启动，或 --check 检查入口。'
  exit 2
fi
volume_uuid="$(/usr/sbin/diskutil info -plist /Volumes/KAFU2T 2>/dev/null | /usr/bin/plutil -extract VolumeUUID raw -o - - 2>/dev/null)" || {
  print -u2 'KAFU2T 未挂载或无法识别；未启动模拟器。'
  exit 2
}
if [[ "$volume_uuid" != F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B ]]; then
  print -u2 '外盘身份不符；未启动模拟器。'
  exit 2
fi
script_dir="${0:A:h}"
runner="$script_dir/run_fx6_menu_trial.py"
python_bin="/Library/Frameworks/Python.framework/Versions/3.14/bin/python3"
if [[ ! -x "$python_bin" ]]; then
  python_bin="$(command -v python3)"
fi
if [[ ! -f "$runner" || ! -x "$python_bin" ]]; then
  print -u2 'FX6 入口文件或 Python 3 缺失；未启动模拟器。'
  exit 2
fi
if [[ "${1:-}" == --check ]]; then
  "$python_bin" -B "$runner" --check
  print 'FX6 菜单入口检查通过；未启动网页或模拟器。'
  exit 0
fi
print 'FX6 菜单（FX3 QEMU 虚拟机运行 FX6 固件 Big6 HOME 菜单）：'
print '即将自动打开本机浏览器页面，支持 7 键导航（↑/↓/←/→/SET/MENU/C4）及参数实时切换。'
exec "$python_bin" -B "$runner" --port 8768
