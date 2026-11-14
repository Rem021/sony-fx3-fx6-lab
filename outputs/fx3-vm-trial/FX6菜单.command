#!/bin/zsh
# Local FX6-on-FX3 VM Big6 HOME menu interactive launcher (supports internal SSD & KAFU2T)
set -euo pipefail
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
if (( $# > 1 )) || { (( $# == 1 )) && [[ "$1" != --check ]]; }; then
  print -u2 '仅支持双击启动，或 --check 检查入口。'
  exit 2
fi
script_dir="${0:A:h}"
mac_root="${script_dir:h:h:h:h}"
if [[ ! -d "$mac_root/work" && -d "$HOME/AI-Workspace/AI/Projects/Mac/work" ]]; then
  mac_root="$HOME/AI-Workspace/AI/Projects/Mac"
fi
if [[ ! -d "$mac_root/work" ]]; then
  volume_uuid="$(/usr/sbin/diskutil info -plist /Volumes/KAFU2T 2>/dev/null | /usr/bin/plutil -extract VolumeUUID raw -o - - 2>/dev/null)" || {
    print -u2 '本地 work 目录不存在且 KAFU2T 未挂载；未启动模拟器。'
    exit 2
  }
  if [[ "$volume_uuid" != F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B ]]; then
    print -u2 '外盘身份不符；未启动模拟器。'
    exit 2
  fi
fi
runner="$script_dir/run_fx6_menu_trial.py"
python_bin=""
for cand_py in "$HOME/.local/bin/python3" "/Library/Frameworks/Python.framework/Versions/3.14/bin/python3" "/opt/homebrew/bin/python3" "$(command -v python3 2>/dev/null || true)"; do
  if [[ -n "$cand_py" && -x "$cand_py" ]]; then
    python_bin="$cand_py"
    break
  fi
done
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
