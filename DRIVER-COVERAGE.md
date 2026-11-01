# 实际驱动覆盖核对（2026-10-28）

最新2026-10-29：用户已确认012准确镜像进入欢迎页面，记为UI用户观察。
Data002持久化和A660有界提交也有各自实机证据；Metal、物理触摸及完整外设资格仍待开发。
以下是10-28旧镜像审计，不覆盖当前012成功结论。

依据[官方驱动清单](https://unixnu.com/zh/porting/drivers)，核对当前已测试镜像
`b31baa584619f9b9909103b1c691b2723a6a99be83f60360abeedcc4dd78ed7c`
的组件、参数、最终内核指令和实机照片。**这不是已完成全设备适配的系统。**

| 项目 | 已有结果 | 仍缺少的验证/实现 |
| --- | --- | --- |
| UFS | 容量/GPT/已知块读取、根卷与用户态实机通过；本次约897260个4K块验证，failures/integrity为0 | 跨重启Data写入读回、长时间与错误恢复、冷初始化及电源状态转换等完整资格验证 |
| Data | 已实现受限持久存储窗口，候选启用mode2 | 不能仅凭root=1或参数存在声称跨重启持久性测试完成 |
| 显示 | 固件画面、GOP与原生显示服务初始化可用 | OS交换/复制仍0，未出锁屏；FBSDisplayMode拒绝的具体字段待采集 |
| A660 | GMU/GX/CP/ZAP与发布、两轮有界用户客户端提交检查通过 | Metal前端、已知渲染像素、OS帧呈现与长期稳定性未完成 |
| HID | 离线键盘/Home服务启动成功 | 物理触屏与实体按键未接入；不能把HID start成功称为触控适配完成 |
| 加速度计/陀螺仪/磁力计/光感/距离传感器 | 当前板级移植没有接入这些硬件后端或验证OS事件 | 芯片/固件、总线/传感器处理器、IRQ、电源、样本与OS接口均需逐项适配 |
| 电池/温度/充电信息 | 电池probe为空函数 | 没有完整的XNU/iOS电池与热传感器数据通路；固件自行充电是另一回事 |
| 音频/Wi-Fi/蓝牙/摄像头/GNSS | 没有已验证的完整板级到OS通路 | ADSP/audio/Wi-Fi入口仍为空函数，其他硬件后端未接入 |
| CPU/平台电源 | 单核启动、定时器工作，逻辑PMGR兼容接口可用 | CPU调频为空桩，多核/休眠唤醒/物理电源控制未完成 |
| 看门狗 | watchdogd本次SIGTRAP可见 | 尚无经过验证的Venus硬件看门狗后端 |
| 内核日志 | 已核对现有独立预留区与底层接口 | 完整写入器、读取器及一次手动抓取尚未完成 |

`package/DisplayProbeStubs.c` 中的 touch、buttons、battery、audio、ADSP、Wi-Fi、
backlight、DPU、CPU频率入口，以及touch/buttons的sink注册函数，在最终内核中均核对为
直接 `ret`。它们使未实现的可选接口可以链接，不构成对应硬件功能。
ShengHidInput解析出的Novatek/GENI源码依赖，也不等于使用了Mi 11的物理触控协议。

本次 `G:/20261028_102002.JPG` 的详细CRASH是watchdogd，近期失败列表仍有SpringBoard。
MODE未显示是详细页选择了最新崩溃；不能据此断定模式采集失败或参数正常。
当前主线按`ORDERED-BRINGUP.md`先补前置适配和阶段验收；专门日志与单点崩溃镜像后置。
显示模式分析仍保留为该阶段的参考，具体字段未测得时不指定修复值。
缺少传感器是实际移植缺口，但尚无证据把某个传感器指定为这次FBSDisplayMode错误的原因。

证据：`evidence/driver-coverage.json`、`evidence/frontboard-mode-phone.json`。
检查脚本：`scripts/audit-driver-coverage.py`。核对不执行任何手机命令。
