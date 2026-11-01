# Touch014 停点与 Touch015 修复（2026-10-29/30）

## 实机停点

Touch014（`7f5f335a...`）一次启动后停在 BootProgress 早期页：`pid=0`、`procs=0`、
`UFS root=0`、`DISPLAY stage=0`，最后阶段为 `PE_lockdown_iokit`；照片
`G:/20261029_233657.JPG`。这不是触摸事件失败，因为尚未到达 HID 用户态阶段。

## 官方文档核对

按用户要求重读本地官方文档（与 unixnu.com/zh 同源）：

- `porting/bring-up.md`：先隔离启动阶段，内核入口/无根卷/用户态分别验证；优先使用
  QEMU 和 `boot-progress=2` 的最后检查点。
- `guide/debugging.md`：诊断页、最后阶段和 panic 屏幕是内核控制台停止后的证据来源。
- `drivers/xnu-drivers.md`：内核驱动是按 ABI 编译、`-force_load` 链接的 C++ IOKit 类；
  必须区分编译、对象 ABI、主机逻辑、内核启动和硬件验证。
- `drivers/kexts.md` 与 `concepts/prelink.md`：kext/trust cache 和预链接输入必须匹配；
  不能把 `fastboot boot` 的 OKAY 当作驱动初始化成功。
- `drivers/sheng-hid-input.md` 与 `porting/input.md`：ShengHidInput 使用已确认的原始
  IOHIDFamily ABI，触控 producer 与 HID consumer 分开；板级资源、时序和报告路径分别验证。
- `reference/troubleshooting.md`、`porting/log-capture.md`：保存失败命令、最后检查点和
  每次启动的证据；内核日志需要串口、诊断页或持久化存储。

## 根因

对照 ShengHidInput 的构建发现：`NativeHidInput.late.o` 没有
`__DATA,__mod_init_func`，而新写的 `VenusHidTouch.o` 有 8 字节自动初始化项。内核在
`PE_lockdown_iokit`/IOKit 初始化期间自动执行了该初始化，提前注册
`VenusHidTouch` metaclass；之后 `venus_st_hid_start` 再次调用
`__GLOBAL__sub_I_VenusHidTouch.cpp`，重复注册导致
`OSMetaClass::postModLoad` panic。QEMU 的 `venus-st-touch=3` 复现了完全相同的栈：

```
panic <- panic_with_thread_kernel_state <- OSMetaClass::postModLoad
      <- venus_st_hid_start <- native_hid_input_probe
```

更正：手机照片只有最后阶段标记，没有故障PC，不能把这个QEMU栈直接归因为手机停点。
015随后进入欢迎页，但触摸仍不可用。ShengHidInput 的构建模式使用
`scripts/macho-late-init.py` 删除自动初始化段，把 initializer 导出为普通符号，
等 IOHIDFamily/IOHIDResource 就绪后再手动调用。

## 修复

- `build-venus-st-touch.py` 现在对 `VenusHidTouch.cpp` 生成
  `VenusHidTouch.late.o`（`macho-late-init.py`，导出
  `__GLOBAL__sub_I_VenusHidTouch.cpp`），归档只含 late 对象。
- 新 native kernel 的 `__mod_init_func` 总量为 824 字节，与 012 控制相同；
  `VenusHidTouch.late.o` 不再含自动初始化段。
- `VenusStTouch` mode1 只做映射和日志，不读取手机 MMIO，供 QEMU 验证；mode3
  才执行手机硬件时钟/GPIO/GENI/扫描。
- 新 kernel `87145de7469d1c21e31146b12c8a75eb9a6b37271319f7695245089f09e36f9f`。

## QEMU 结果

- default-off（touch=0）：`qemu-metal-touch-default-off-r3` 到真实
  SystemOS/owner-cache checkpoint；AKS/HID 状态通过。
- mode1（touch=1）：`qemu-metal-touch-mode1-r4` 到同一 checkpoint；
  `_venus_st_stage=2`、`_venus_st_status=0`、`_venus_st_hid_status=0`，
  **这不证明触摸HID注册。mode1在metaclass/start之前返回，hid_status=0只是初始值。**
- `qemu-metal-touch-mode3`保留旧kernel的postModLoad故障；
  `qemu-metal-touch-mode1`是随后kernel-link-4访问QEMU不存在的MMIO导致的另一故障，
  两者不能混为同一对照。新 kernel 的硬件mode3不直接用于
  QEMU，因为 QEMU 没有手机 ST/GENI 硬件。

## 新候选（未启动）

| 候选 | 镜像 | SHA256 |
| --- | --- | --- |
| Touch015 | `artifacts/venus-touch-015/phone/boot-venus-unixnu.img` | `92018c0fe7793fffca2e8c8e0dd23f91f5e5ac05f21fe17100fc871bec42eb45` |
| Metal016 | `artifacts/venus-metal-016/phone/boot-venus-unixnu.img` | `82d3b33e53844e8fa1fe02dd4b14d57f3e5939b297a51a2a931387502bd2f742` |

均 168,960,000 B；kernel `87145de7...`；Touch015 保留 012 ADT/seed/trust/FD/EFI，
Metal016 保留同一 012 输入并带 own addon/trust。两候选的 FAT、roundtrip、
`--check` 均通过。Touch015 才是新的触摸实测候选；014/013 镜像和失败日志保留。

## 下一步

015已启动一次，用户确认欢迎页可见、点击滑动无反应。
真正的匹配/报告测试及017修复见[TOUCH-017.md](TOUCH-017.md)。
