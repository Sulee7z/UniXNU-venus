# 015无触摸：原版digitizer匹配依赖与017

用户确认015已到欢迎页，但点击/滑动无反应。只读快照
`artifacts/venus-data-forensics/read-20261029T181433Z`完整：169934页/91段，
含两次metadata共696582144B，checkpoint1115。launchd完整参数匹配touch-015；
trace28文件有效前缀已解压，1c末尾不完整。只有VenusHidTouch/IOHIDInterface字符串，
没有可归因的GENI/芯片/上报状态，不能声称硬件读取成功或失败。

## 修正上一轮资格结论

`venus_st_hid_start`在mode1启动映射线程后直接返回，跳过metaclass/init/attach/start。
因此mode1的`hid_status=0`不是执行结果。014照片最后标记也不是故障PC。
所有新meta/match/start/report返回状态初始化为-1，分别记录执行阶段。

## 原版匹配依据与实际测试

按官方`porting/input`、`drivers/device-tree-matching`、`drivers/xnu-drivers`核对
**21H461原kernelcache的PRELINK_INFO**，脚本`inspect-venus-hid-personalities.py`：

- 已加载的codeless `com.apple.iokit.IOHIDEventDriver`只包含键盘、按钮、特定传感器等匹配。
- page13 digitizer匹配在遗漏的 **`com.apple.iokit.IOHIDEventDriverSafeBoot`**。
- 017预链接并显式加载该原版codeless bundle，保持原IOHIDFamily代码；补充自己设备的
  HIDDefaultBehavior、DigitizerCollectionDispatch和base start之前可用的workloop。

实际QEMU对照（同一个独立测试producer提供按下、移动、抬起；不含真实ST硬件）：

| 运行 | 结果 |
| --- | --- |
| qemu-hid-before | 首次测试未提供Data，提前因scratch Data mount panic；无HID结论 |
| qemu-hid-before-r2 | 5秒内ready0/reports0；bootstrap阻塞式测试，资格有限 |
| qemu-hid-fixed | 仅workloop/属性修正仍ready0/reports0 |
| qemu-hid-fixed-r2 | 提供真实Data、独立等待30秒；timer311次，只有IOHIDInterface，ready0/reports0 |
| **qemu-hid-matching** | **加入原digitizer匹配后ready1/reports3/status0**；真实IOHIDEventDriver已挂接 |

后一个测试执行原版HID解析器和生产VenusHidTouch/codec，生产对象SHA与测试对象相同。
测试producer单独归档，`qemu_only=true`；打包器拒绝QEMU-only kernel。
这是匹配和handleReport验证，尚不是手机SPI或UIKit手势成功。

## 启动状态取证

`BootStTouchReport.h`在原postData policy后、launchd前保存一次采样：
`/private/var/db/venus-st-017/startup.jsonl`，目录root0700、文件0600，独占创建。
包括clock/GENI协议/FIFO/识别ID/transfer/CS/IRQ计数及HID各阶段，不伪造未执行状态。
报告只有prelaunchd采样，不能记录用户后续触点，也不会把计数0解释成成功。

真正APFS测试已执行write/pread逐字节比较、fsync/F_FULLFSYNC和目录同步；
scratch+400..700环境未变化；最后medium返回EIO5是QEMU没有UFS，原错误保留。
实际手机持久化效果待取回确认。既有报告不覆盖。

## 017候选

- Image SHA256 `f9937cf513b2f455953b36380110969a9b66975878f3a4da31b02a414ac4a230`
- Kernel SHA256 `a1701917b1a270df1c4b5ba6f590cb2ed9ace3ac03eea50df4bb125f4c2d316f`
- 镜像 `artifacts/venus-touch-017/phone/boot-venus-unixnu.img`，168960000B。
- 原012的seed/ADT几何/trust/FD/EFI保留，GPU关闭；触摸mode3的硬件配置只增加状态记录。
- 原版codeless匹配+HID修正+一次启动报告；不再失效MG缓存、不reset Data、不刷写触摸固件。
- 新生产kernel的default-off QEMU SystemOS/6GiB/AKS/HID、APFS报告检查和FAT/boot roundtrip/--check均通过。

证据：`evidence/touch015-review.json`、`evidence/touch017-candidate.json`。
后续一次准确实机启动用于判断匹配修正后的触控，并读取启动报告确定剩余板级失败点。

随后用户确认“Android中，确认017一次”，准确镜像已RAM boot一次：
Sending4.350s/Booting0.193s OKAY，总4.602s，venus/55870427匹配。
授权已消费，`evidence/touch017-phone.json`记录。用户回到Android并授权只读后，
`read-20261029T192825Z`已取回：171115页/93段/含两次metadata共701419520B，
checkpoint1159，metadata稳定/SHA/覆盖通过；`/private/var/db/venus-st-017/startup.jsonl`
362B，`stage5/status-19/chip_id0/transfer0/cs0/fifo_disabled0/hid_ready1/hid_reports0`。
结论：HID匹配成功，ST识别第一次0xFB传输完成但芯片ID0；见[TOUCH-018.md](TOUCH-018.md)。

本轮G:曾满盘。已按SHA核验回收本轮QEMU重复payload副本，收据
`artifacts/venus-st-touch/reclaimed-qemu-copies.json`。随后检测到工作区另有清理，
G:空闲约73GiB、部分QEMU-only旧kernel/vars已不在原位；附加归档尝试未执行删除。
017生产kernel/镜像/构建对象及015原始快照仍在，日志、JSON收据保留。
