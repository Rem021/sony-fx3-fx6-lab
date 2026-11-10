# EVIDENCE 659–661：Big-6 六格与三层菜单项——静态数据边界的最终定位

时间：2026-11-08（America/Los_Angeles）

## 1. 通用工厂的真实契约（`appFw+0xc1935c`）

反汇编确认工厂签名：

```
factory(container /*x0*/, layer /*w1*/, desc /*x2*/, count /*x3*/)
    for i in 0..count:
        tag   = *(uint8_t**)desc              // descriptor +0x00
        idx   = *(int32_t*)(tag + 8)          // tag+0x08，不是 desc+0x08
        ctor  = creators[idx]                 // creators = appFw+0x2911720（40 项）
        obj   = ctor(cap, arena, &out_size, parent, &param)
        [vt+0x140](obj)                       // onCreate，返回 obj+0x1d0 子对象
        [vt+0x148](obj)
        [vt+0x30](obj, 0)
        // 然后按 tag 的 vtable 把 descriptor 字段写入子对象相对偏移
```

关键点：**工厂是「带 sized placement-new 的批量构造」**，`ctor(cap, cursor, &out_size, parent, param)`
会在 `arena + cursor` 处雕刻对象并回写大小。它和「`calloc` 后直接调 ctor」不是同一套契约。

## 2. 六格外框（Big-6 上下六格）

`TABLE 0x2e9e210` 里上下六格的条目（索引 91–96）全是 `view_menu_item` 类（tag `0x42d58d0`）：

```
[96] No101_BUTTON_01 (96,72,257,122)   q18=0  layout=0200a02a  font=02006032
[92] No102_BUTTON_02 (349,72,262,122)  q18=0  ...
[95] No103_BUTTON_03 (607,72,257,122)  q18=0
[94] No104_BUTTON_04 (96,382,257,122)  q18=0
[91] No105_BUTTON_05 (349,382,262,122) q18=0
[93] No106_BUTTON_06 (607,382,257,122) q18=0
```

六格的外框几何、字体、对齐全部来自原生表，但 **caption ResID（`+0x18`）静态就是 0**，
FPS / Shutter / ISO / ND / WB / Look 的标题与数值由 controller 在运行时按
`menu_item_id_t` 从 model 注入。表里同样找不到任何 `FPS/SHUTTER/ISO/ND/WB` 命名的
静态文本控件（全表转储 1893 条里只有 `No28_THUMBNAIL_PROPERTIES_FPS_*` 这类其它页面条目）。

## 3. view_menu_item 直接构造 → 崩溃

659（`cp-bind-9e8b981f`）与 660（`cp-bind-1eb02dd3`）都验证了同一件事：

```
APPFW_SEGV sig=11 addr=0x7f7c0dc018 pc=... sp=...
APPFW_X0=0x7f7c0dc000  X1=...  X3=0
```

崩在 `calloc` 出来对象内部的指针解引用，原因是：

1. ctor `0xc341d4` 把子控件雕刻进对象自身的 `+0x23c / +0x634 / +0xa30 / +0xe28 / +0xd7e0`
   等偏移，内部还有 `call 0xc16768` 初始化子结构；
2. `onDrawNotice`（`0xc35358`）按 `+0x200` 的 16 项 style 表分发到 `0xc347b0` 行渲染器，
   该渲染器读取 `self+0x1d0/+0x1d8/+0x1e0/+0x228` 与子控件链表；
3. 直接 `calloc + ctor` 缺少工厂的 sized-placement 契约与父容器，
   子结构里的指针全为空 → 首次解引用即 SEGV。

**结论**：`view_menu_item` 必须经通用工厂（`0xc1935c`）随整棵容器一起构造，
不能单独 new。661 已回退到 `view_string` 方案，基线恢复（gpe0 nz 正常）。

## 4. 三层菜单表 `0x2ea02f8` 的行文本

35 项里 `No4_item1..No10_item7inthesecondlayer`（索引 10–16）与 `No24_Itemnumber`（27）
的 `+0x18` 静态为 0，只有 `No3_Backstringinthesecondlayer`（18）有 `0x02004c3e`。
这与 657 的实测一致（text=1、fill=15、icon=1）。
所以三层页的「真实菜单项文字」同样来自 controller 注入，不是描述符缺字段。

## 5. 下一步唯一可行路线

要把六格与三层列表填上真实文字，必须走：

1. 用工厂 `0xc1935c` 一次构造整页容器（arena + cursor + parent + param 四个参数齐全），
   让 `view_menu_item` / `view_list_scroll_item` 在正确的对象图里被创建；
2. 找到 controller 的 `set_value(menu_item_id_t)` / `update_setting_list(menu_item_id_t)`
   （`procam_big6_menu_setting_presenter::update_setting_list`，字符串在 `0x23bfe10` 附近）
   以及 `menu_item_id_t → 字符串 ResID` 的映射表，喂真实 id；
3. 再触发 onDrawNotice + `processCommands(0)`，文本就能经已验证的字形链路落进 gpe0。

当前阻断点不是绘制，而是**对象图与 id 映射**。
