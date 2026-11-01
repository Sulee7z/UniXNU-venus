# 多核038与匹配的 iPhone 目标准备

2026-10-30。用户要求使用更多 CPU 核心，并按文档切换 iPhone 身份。
在解释 iPhone 身份需要配套 iOS 根卷后，用户选择“准备完整 iPhone 构建”。

## CPU：修复实际启动缺口

- 当前 BCM2837 配方的 `board_config.h` 明确 `MAX_CPUS=4`、`MAX_CPU_CLUSTERS=1`。
  八个 DTS 节点或 `cpus=8` 不能改变编译后的数组、拓扑和 CPU 数据容量。
- 当前非 Apple 的 `reset_vector` 只取 `MPIDR & 0xff`。
  Venus 实际 affinity 是 `0,0x100,...,0x700`，所以旧入口会把所有次核识别成 CPU0。
- SoC 新补丁 `sm8350-psci-reset-affinity.patch` 将非 Apple 入口改为保留 Aff0/Aff1，
  并先安装异常向量、建立 PSCI 的 SCTLR 初始状态，再进行 debug-register 访问。
  HackiOS `redwood.patch:2393–2435` 有相同的 PSCI/Affinity1处理依据。
- 通过原始 iOS17 assembler recipe 重编译 `start.o`，只替换独立 native archive 的这一个成员。
  其他1008成员按内容哈希逐项核对一致。现有源树没有被覆盖。
- 038请求四核：`0,0x400,0x500,0x700`，即启动核心加三个性能核心。
  使用 `cpus=4 sheng-smp=1 armcpu-self-ipi=1`，PSCI为SMC，保持单一SMP调度簇。
  E/P调度和八核完整重编译另需资格验证。
- 037曾请求八核，但核编译容量仅四；已记录 `qualification-blocked.json`，不能上机。

## 主机结果与边界

`check-venus-smp038.py` 核对真正编译的旧/新复位指令：旧mask255，新mask65535。
固定的八个 Venus MPIDR 在旧指令下全部别名到0，新指令下唯一。

QEMU真实 UEFI→DarwinBoot→原始预链接内核：三次级核到stage7，
`processor_avail_count=4`，PSCI返回0，失败字段全0；实际 `rtclock_intr` 返回。
这次有界快照的四核timer计数为 `[14,2,1,0]`，IPI计数0。
不能称为“每核timer与IPI都通过”，不能称为全系统/性能或 Venus 实机通过。
`gCPUsRunning` 的现有观察值1也保留，不能用它替代scheduler可用数。

038仍使用当前iPadOS17系统与036 Metal代码。035触摸producer/consumer和036GPU归档哈希不变。
原始 OS/SystemOS 主机raw文件缺失；本次QEMU是CPU启动检查，不是完整系统启动验证。

候选：`G:/UniXNU-Port/artifacts/venus-metal-touch-038/phone/boot-venus-unixnu.img`

- image：`ec14bf7cba2f28335ccf884be84df045b63ecb73658bde060296a3670de31a15`
- kernel：`bd312e850bc3741d27c79cf748990f59fadd5f023c9e66ec424507adb2cd3423`
- 038随后按单次授权启动：Sending4.337s/Booting0.193s，总4.572s。
  用户随后确认GPU/Metal未生效；失败具体阶段尚未捕获。授权已消费。

## iPhone：匹配真实系统，而非改名称

[MobileGestalt文档](https://unixnu.com/zh/guide/mobilegestalt) 要求iOS根配phone身份。
已采用[官方第二目标](https://unixnu.com/zh/guide/requirements#目标-ipsw)：
iPhone X / `iPhone10,3` / D22 / iOS16.7.16 /20H392。

实际Apple BuildManifest的Erase身份校验：d22ap、ApChipID8015、ApBoardID6。
KernelCache、原始ADT、OS、SystemOS和两个trust cache均以HTTP range取得，完整ZIP CRC/SHA核对。
系统输入约7.47GB，保存在 `artifacts/venus-iphone-inputs/20H392`。

原始内核实测版本：Darwin22.6.0，`xnu-8796.142.1.703.8`，普通ARM64 subtype0。
公开源码准备为Apple `xnu-8796.141.3` / commit
`1b191cb58250d0705d8a51287127505aa4bc0789`，实际原始组件ABI仍须单独核对。

准备profile：`profiles/ios-16.7.16-20H392/profile.toml`。
其中根 `model=iPhone10,3`、`target-type=D22`、产品iPhone X、idiom phone、subtype2436、
scale3和无menu/home-button-type2与原始iPhoneADT核对。
保留真实板compatible和Venus sRGB，不引入Apple硬件驱动匹配。

官方userdata builder已构建 `SHNGROOT` 根镜像，原始OS/SystemOS只读窗口字节不变：

`G:/UniXNU-Port/artifacts/venus-iphone-root/20H392/userdata/userdata-root.img`

- bytes：`8380219392`（7.80GiB）
- SHA：`2c2aca3feb7585c91b80ec6b50cc1888ac9315f4c77d981566de5dd902eabefa`
- manifest与全部窗口内容哈希已重新独立核对。

## 完整 iPhone 启动尚缺的部分

- 当前native是XNU10063/iOS17；需要XNU8796/iOS16的版本化补丁、编译和预链接。
  现有Linux环境入口 `scripts/unixnu/kernel.py:73–79` 固定iOS17 SDK/triple。
- 当前storage/display/HID绑定和原始accelerator C2/D2/meta是iOS17输入。
  `VenusMetalPlugin.mm:38` 还明确拒绝majorVersion不是17的系统，不能直接用现有插件。
- 需要与iOS16根卷和持久存储身份匹配的Data seed，不能沿用旧iPadOS缓存和UUID来声称迁移完成。

因此新iPhone根卷已经准备，但 **iPhone启动候选尚未就绪**；本轮没有部署新根卷。
检查记录：`artifacts/venus-iphone-root/20H392/preparation-check.json`，
CPU记录：`artifacts/venus-smp-038/qualification.json`。
