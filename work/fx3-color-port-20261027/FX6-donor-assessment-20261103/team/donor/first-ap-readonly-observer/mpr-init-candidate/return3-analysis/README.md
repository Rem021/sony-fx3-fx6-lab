# MPR Init 返回 3 的根因：FX3 把 FX6 回调指针读成 count

**结论：`w0=3` 不是 FX3 `mpr::Init` 的初始化结果，而是参数布局错位触发 `count > 4` 保护分支后的固定拒绝码。** FX6 的 `0x290` 记录把回调指针放在 `+0x1d0`；固定 FX3 `libmpr.so` 在同一偏移读取 `count`，读到该指针低 32 位 `0xE3FB3DE0`（3,824,893,408），大于 4，于是在正常初始化路径之前直接 `w0=3` 返回。FX6 的真实 `count=2` 位于 `+0x268`，FX3 从未读取。

本轮只做静态判读，没有运行 QEMU、没有访问相机/USB、没有改任何二进制或既有报告。

## 1. 输入与身份

| 项 | 值 |
|---|---|
| 运行 | [`mpr-ro-b22ccc48`](../runs/mpr-ro-b22ccc48/receipt.json)，29.235 秒，`qemu_exit=0`，API16 已还原 |
| 观察记录 | [`mpr-observation.json`](../runs/mpr-ro-b22ccc48/mpr-observation.json) |
| 固定 FX3 `libmpr.so` | SHA256 `9aeef3b9edb3d011c0c90cd2387b3a47bd3b506ebfa57be39ad1a9729771b57c` |
| FX6 `appFw.so` | SHA256 `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` |
| `0x290` 参数记录 | SHA256 `585d8918da368cec6ef689aa3c14dc3306311ab6661c0bffc9a02e1685430cf1`，656 字节 |
| 调用点 / 返回点 | AP 原 VA `0x212f7b8` / `0x212f7bc`，同一 TLS、同一参数 `0x7ed5e763b0` |

固定 FX3 库可从以下任一等价副本取得（两处 SHA 相同）：

- `work/sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/libmpr.so`
- `work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libmpr.so`

## 2. 参数记录的关键偏移

从 `mpr-observation.json` 的 `records[2].parameter_0x290_hex` 直接解码（小端）：

| 偏移 | 原始字节 | 解释 |
|---|---|---|
| `+0x1d0` | `e03dfbe37e000000` | FX6 回调指针 `0x7ee3fb3de0`；低 32 位 `0xE3FB3DE0` |
| `+0x1d8` | `0000000000000000` | 下一 8B 槽为 0 |
| `+0x1f2` | `fae37e00` | u16 `0xE3FA` = 58,362 |
| `+0x268` | `0200000000100000` | u32 `count=2`；紧随 u32 `0x1000` |
| `+0x28a` | `a0050000` | u16 `0x05A0` = 1,440 |

即：FX6 侧 `count` 在 `+0x268`，回调在 `+0x1d0`；FX3 侧 `count` 在 `+0x1d0`。这是本轮的根因偏移冲突。

## 3. FX3 `mpr::Init` 的反汇编证据

固定 FX3 库符号表：

```text
00000000000b6844 g DF .text 0000000000000884 _ZN3mpr4InitERKNS_11initInParamE
```

入口与提前返回路径：

```text
b6848: 52803f01  mov  w1, #0x1f8          ; 参数大小 504
b6870: b941d260  ldr  w0, [x19, #0x1d0]   ; 读 FX3 count
b6874: 7100101f  cmp  w0, #0x4
b6878: 54000349  b.ls 0xb68e0             ; count <= 4 才进入正常路径
b687c: 52800061  mov  w1, #0x3
b6880: b90083a0  str  w0, [x29, #0x80]
b6898: 52800073  mov  w19, #0x3            ; 返回值 3
b68c8: 2a1303e0  mov  w0, w19
b68dc: d65f03c0  ret
```

该函数内只有这一处 `mov w19, #0x3` 和这一处 `ret`；正常路径从 `0xb68e0` 开始，先读取 `[x19,#0x8]` 到 `[x19,#0x1c8]` 的字段，并以 `+0x1d4` 作为后续数组/记录区。也就是说，`count > 4` 是唯一的“返回 3”路径。

把本轮记录代入：

```text
count = u32(record + 0x1d0) = 0xE3FB3DE0 = 3,824,893,408
0xE3FB3DE0 > 4  →  b.ls 不成立  →  w0 = 3  →  ret
```

正常路径没有执行，FX6 的真实 `count=2`（`+0x268`）也没有被读到。

## 4. 因果链与边界

1. AP 原调用点把 FX6 `0x290` 记录指针传给固定 FX3 `mpr::Init`。
2. FX3 按自己的 `0x1f8` 布局读 `+0x1d0` 作为 `count`，实际读到 FX6 回调指针的低 32 位。
3. 该值远大于 4，命中 `count > 4` 保护分支，直接返回 3。
4. 因此 `w0=3` 只证明“调用进入了 FX3 `mpr::Init` 并在入口保护处返回”，**不能**证明 FX6 参数的其他字段、CAPID 初始化或 MPR 后续服务可用。

未证明/不能声称：

- 修正布局后 FX3 `mpr::Init` 是否会继续执行、是否会成功；
- `+0x1d4` 起数组的元素语义与长度；
- FX6 `0x290` 其余字段与 FX3 `0x1f8` 的逐字段对应；
- MPR 入口断点未命中（GOT 前为 lazy resolver）与 CAPID 未武装，本轮不能反证“未执行”，但也不能用返回 3 代替入口证据；
- 任何 FX6 菜单、RAW/ISP、像素或实机效果。

## 5. 下一步（仅静态，先不申请 VM）

1. 以 FX3 `mpr::Init` 的 `0x1f8` 布局为基准，逐字段比对 FX6 `0x290`：`+0x8..+0x1c8`、`+0x1d0`、`+0x1d4` 起数组、`+0x1f2` u16、`+0x268` count、`+0x28a` u16。
2. 判断是否存在最小适配记录：`count` 放到 `+0x1d0`（值 2），条目区 `+0x1d4` 由 FX6 数据转换；若条目语义不匹配，明确停止，不做猜测性填充。
3. 产出 host-only 候选与正反例；在独立复核前不申请 VM 窗口，也不改固定平台、不碰相机。

## 6. 复核命令

```sh
LIB=work/sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/libmpr.so
shasum -a 256 "$LIB"
objdump -d --start-address=0xb6844 --stop-address=0xb68e0 "$LIB"
```

```python
import json
p = "work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/" \
    "first-ap-readonly-observer/mpr-init-candidate/runs/mpr-ro-b22ccc48/mpr-observation.json"
r = [x for x in json.load(open(p))["records"] if x.get("kind") == "call"][0]
b = bytes.fromhex(r["parameter_0x290_hex"])
print(len(b), hex(int.from_bytes(b[0x1d0:0x1d4], "little")),
      int.from_bytes(b[0x268:0x26c], "little"))
```

预期：`656 0xe3fb3de0 2`。

---

**范围**：本报告只解释 `mpr-ro-b22ccc48` 的 `w0=3`，不把静态判读当作 FX6 初始化成功或可运行证据。
