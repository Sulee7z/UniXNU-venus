# 触摸源码复核与更正（035）

本轮仅在主机核对源码、运行测试、编译。没有新的手机命令。

## 文档与原厂依据

用户分享的 DeepSeek 回答正文已通过公开分享接口读取：
`https://chat.deepseek.com/api/v0/share/content?share_id=40r33dpwpkkso7gbto`。
正文强调传感器、HID 发布与 backboardd 是不同层，也要求适配坐标和报告。
其中 myron 的 FT3683 是另一个传感器，不能据此把 Venus 认作 FocalTech。

官方输入指南：<https://unixnu.com/zh/porting/input>。
板级、传感器和 OS 报告需要分别适配，识别错误或未通过校验不能继续称为成功帧。

Venus Android 参考固定为 `Evolution-X-Devices/kernel_xiaomi_venus`：
`df169d0b934bd8e372c5c5e2ffab5f9c50f3d052`。
文件已保存在 `artifacts/venus-touch-audit-035/vendor/`，SHA 在 `manifest.json`。

| 原厂文件 | 可以直接核实的事实 |
|---|---|
| `fts_spi/fts_lib/ftsHardware.h` | 文件头为 STMicroelectronics；SPI 硬件读 0xFB、写 0xFA、FIFO 0x87、一个 dummy byte；ID 低字节在前 |
| `fts_spi/fts_lib/ftsSoftware.h:273-281` | READY=03、ENTER=13、MOTION=23、LEAVE=33、STATUS=43、ERROR=F3 |
| `fts_spi/fts_lib/ftsIO.c` | `fts_write` 直接发送命令字节；读写阶段共用 CS，最后延时 10us 后释放 CS |
| `fts_spi/fts_lib/ftsCore.c` | GPIO 复位低 10ms，等待 READY；scan 是三个原始字节 A0 00 01；echo 为 43 01 A0 00 01 |
| `fts_spi/fts.c:3720-3953` | 进入和移动共用坐标处理；抬起单独释放 slot；普通 XY 为 12-bit，ID 在 event[1] 高半字节 |
| `fts_spi/fts.c:4538-4572` | FIFO 剩余条目在 event[7]&31，不是触点数量 |
| `pinctrl-lahaina.c`、`pinctrl-msm.c:469-539` | CTL bit9 为输出方向；IO bit0 是输入电平，bit1 是输出 latch |

## 已修正的代码错误

1. **协议认错**：`fts_touch_spi` 和日志前缀 `[ FTS ]` 不证明 FocalTech。此前改用
   FT3680 的 0x01/CRC framing 没有依据。现已移除该路径，恢复有原厂依据的 STM 协议。
2. **移动/抬起颠倒**：旧 `vst_process_events` 将高半字节 2 当抬起、3 当移动，
   原厂定义恰好相反。这能在主机用原始 `13 -> 23 -> 23 -> 33` 字节序列复现：
   旧代码在第一条移动时发 tip-up，修复后四条报告构成连续拖动并正常释放。
3. **复位未真正拉低**：旧 `(io & ~1u) | (high ? 2u : 0)` 在 OUT 已为 1 时不能清 bit1。
   修正为只对 OUT bit1 置位/清零。输入方向只改 CTL OE，不写采样电平。
4. **忽略初始化失败**：旧 FocalTech ID/scan 失败后无条件 `stage=7/status=0`。
   修复为 READY -> 严格 ID -> STM scan -> echo 的有界检查，失败保留状态并停止。
5. **CS 延时位置错误**：旧 keep_cs=0 完成后才 IODelay，实际是 CS-high 间隔。
   改成完整消息 keep_cs=1，延时后发 GENI CS_DEASSERT=9，并检查完成/超时。
   opcode 9 定义见 Linux v6.12 `drivers/spi/spi-geni-qcom.c`；旧“未定义 opcode9”说法错误。
6. **移动批次丢中间位置**：同一 FIFO 批次的每条移动都发布，最后一次移动不会被紧接的
   抬起吞掉；重复 ENTER 不凭空插入一次抬起。
7. **测试和收据失真**：旧测试用自己生成的错误事件码，重复了实现错误。新增 raw fixtures
   并在保存的 029 源码上确认必败。打包不再把变化后的 HID/codec 当作旧 QEMU 三报告测试通过；
   头文件也纳入构建哈希，主线消费者与生产者的唯一链接由符号检查验证。

## 纠正此前结论

- 022 同时改变了供电和 GPIO，不能仅凭 MISO 电平从 0 变 1 归因于“输入使能修复”。
- `transfer=0` 仅代表控制器完成传输；禁掉 CRC 后累计的 77 次读取不证明有 77 个有效触摸帧。
- 所有 `sample=prelaunchd` 文件早于用户在欢迎页点击。`native_reports=0` 不能说明之后
  backboardd 没收到手势，更不能据此断定整个 HID 链路正常或异常。
- IOHIDEventDriverSafeBoot 是 codeless personality 包，不是另一个有不同 vtable 的 HID 实现。
- 先前所谓“31 个驱动全量编译”只是单文件兼容性试编译，且误用过 C++ recipe 编译 C；
  不能当作 HackiOS 整个项目无法构建的证据。
- 当前采用的是基线归档里实际链接的 `NativeHidInput.late.o`。复制到 package 的同名文件
  并不等于它已进入内核；035 链接记录验证消费者对象和基线逐字节相同。

## 验证范围

`check-venus-st-audit.py`：ASan/UBSan，原始拖动序列、GPIO 高低转换、就绪/echo/超时、
严格 ID、dummy/FIFO 长度、native HID 坐标及 palm/hover 过滤、CS 释放与错误传播。

结果见 `artifacts/venus-touch-audit-035/host-tests/report.json`。
旧 029 的事件解析必须失败；新实现测试通过。新的 iOS17 对象、native link、prelink 通过。
未用编译或主机 mock 冒充实机触控成功。035 仍需一次后续单独授权的物理验证。

候选：`G:/UniXNU-Port/artifacts/venus-touch-035/phone/boot-venus-unixnu.img`。
SHA256：`db727796ae044c84feaf27fcc745357ddaee4ca064e60b7541b655ebac5fb98a`。
`prepare-venus-metal-touch-phone.py --kind touch --version 035 --kernel-dir
/mnt/g/UniXNU-Port/artifacts/venus-metal-touch/kernel-link-33 --skip-qemu --check`
已通过；`qemu_verified=false`，旧 HID QEMU 三报告没有复用。
