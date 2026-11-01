# iamOJZ/haydn 参考核对

用户提供：https://github.com/iamOJZ/UniXNU-haydn

固定版本：`70ef03e5fc0cf1c909a913a73c641df9ebcb0994`（2026-10-29）。
15份文件按Git blob SHA与大小核验，保存在
`G:/UniXNU-Port/references/haydn-iamOJZ/<revision>/`，收据`SOURCE.json`。

## 对当前锁屏工作的价值

同属SM8350、同iPadOS17.7.11/21H461，值得借鉴**日志通路和板级资源组织**。
该版本README仍是bring-up，porting记录的storage/display/input均未实机验收；
所有area.evidence为空。最新提交把UFS诊断传输接入链接，但owner-root实现是拒绝桩。
没有可复用的FBSDisplayMode/MobileGestalt修复或锁屏成功流程。

## 可借鉴内容与核对结果

| 内容 | haydn实现 | Venus处理 |
| --- | --- | --- |
| 物理定时器异常 | `0001-sm8350-el1pcen-physical-timer.patch`删除fiq_context_init的CNTP_CTL写，保留CNTV | 与Venus已实机验证的修正方向一致；保留当前计时器基线 |
| 完整控制台 | `0002-sm8350-geni-uart-console.patch`接GENI UART、保留CNTVCT超时 | 可作为后续UART驱动参考；COM3是他使用的外部串口适配器，不能当成本机现成USB通道 |
| 控制台与照片解耦 | UART为主，framebuffer与QR为辅助 | 支持本项目的证据优先框架；当前先用已有Data只读解析与自有MG查询报告 |
| SPI总线板级描述 | `HaydnTouchBoard.h`区分SE/IRQ/reset/引脚/GCC投票与芯片协议 | 地址`0xa8c000`、GPIO22/23与Venus的已有DT清单有交集，可作为资源审计清单 |
| 触控协议 | haydn FocalTech FTS5652，6MHz | Venus是ST FingerTipS SPI参考、7MHz，命令/事件/固件不能混用；该haydn函数目前只握手，无HID事件发布 |
| PMGR服务 | provider-less状态发布配方 | Venus已有原版nub ABI与QEMU/实机结果；无需替换已测路径 |
| 存储ABI | 编译公开IOBlockStorageDevice.cpp满足链接 | 这只解决符号依赖，不能单凭源码版本声称匹配已预链接Apple二进制对象；Venus保留190槽运行时/原版ABI绑定 |
| owner-root | `HaydnRootStub.cpp`所有认证拒绝、policy_count0 | 是早期硬件诊断用途；不能替代本项目已经通过根卷/用户态的实际验证策略 |

## 文档与实现差异

最新提交启用了UFS，但该pin的porting.toml仍说没有驱动，README也说storage未适配。
硬件值也需重新核对：porting记录的UFS PHY为`0x1d80000`，Venus已测参考为`0x1d87000`；
内存、面板、userdata LUN和GPT均来自另一台设备。采用时应以实际源/最终配置和测量为准。

UART代码在运行前写DMA模式/IRQ使能等寄存器，不是只读日志导出；Venus已有MMIO写指令限制，
需检查最终STR指令与控制器所有权。haydn源码中的SPI时钟超时后继续初始化、
芯片ID接受任意非零值，不能当作Venus芯片已识别的证据。

## 本轮采用的思路

采用它的“板级事实与通用控制器分离、持续日志优先”做法。
本轮继续对已有MG缓存做严格只读解析，以及单次API查询；没有接入haydn硬件写入。
取证修正和查询候选见`MG-QUERY-OBSERVATION.md`。
