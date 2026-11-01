# 036：补齐 A660 的原始 Metal 发现入口

2026-10-30。用户确认035“触摸成功了”，之后要求参考
[HackiOS-Xiaomi11Ultra](https://github.com/g11930/HackiOS-Xiaomi11Ultra)
修复 GPU，并补充[官方驱动仓库目录](https://unixnu.com/zh/drivers/repositories)。

## 证实的缺口

旧 `build-venus-a660.py` 将 `NativeAdrenoAccelerator.cpp` 排除为 A740 专属文件。
实际上它是原始 iOS17 `IOAcceleratorES` 的通用薄适配层，将请求转给现有
`native_adreno_new_user_client`。与 A740 寄存器初始化无关。

旧 `GpuPowerProbe.cpp` 只向普通 `NativeAdrenoGpuPublished : IOService` 写
`MetalPluginName`，注释假定 zeta 内核中的类名映射存在。当前 Venus XNU 没有该映射。
原始 Metal 和实际编译的 Turnip Darwin 后端默认查找 `IOAcceleratorES`。
所以 CP 写内存、自测提交和私有服务发布成功，不能证明原始 Metal 能发现设备。

旧035二进制审计：私有服务存在，`native_adreno_accelerator_allocate` 不存在。
036二进制：两者都存在。不能将此源码缺口反推成某张旧照片上的 GPU 瞬时状态。

## 参考核对

- HackiOS pin：`e97863f8722ca3a8b7c12f24c899fa90c048b509`。
- `docs/STAR.zh-CN.md:34–49`：GPU 常驻、真实 Metal 设备发布、在 launchd 前准备插件，
  以及 Apple2/MPS 条件。`84–88` 明确区分硬件渲染与 CPU 缩放上屏。
- `xnu/files/iokit/Kernel/MiniIOMobileFramebuffer.cpp:1914–2015`：原始发现读取
  `MetalPluginName`/`MetalPluginClassName`，通过真实 `IOAcceleratorES` 服务发布。
- `xnu/files/bsd/dev/redwood_adreno.c`：GPU/GMU/GPUCC/SMMU 地址分别为
  `0x3d00000/0x3d6a000/0x3d90000/0x3da0000`；GX 投票后保持 OOB 请求。
  板级固件、SMMU 所有权和投票继续使用已核对的 Venus 输入。
- 官方 [GPU 适配](https://unixnu.com/zh/porting/gpu) 区分 GMU、提交、Metal 发现与呈现。
  采用已有 `NativeAdrenoAccelerator.cpp` 和原始 ABI 声明，不复制 HackiOS 的 iOS16 内核。
- 当前已编译的 Rust frontend `NativeMetalObjects.rs:390–397` **已经包含 Apple2/Apple3**。
  没有依据新增另一个 `metal_profile=1` 开关。
- 当前 Turnip `tu_knl_darwin.cc:109–127` 默认用 `IOAcceleratorES`、open type `0x4147`。

## 改动

1. 在独立 GPU 构建目录编入已有通用适配层；其 initializer 由
   `macho-late-init.py` 延期，代码字节不变。
2. 新 `VenusMetalPublication.cpp` 在真实 GPU transport 初始化后加载原始 IOGPUFamily，
   核对父类大小，注册适配类，设置完整属性，然后才 `registerService()`。
   任一失败不发布半初始化设备。
3. GPU Metal 模式移除任意10秒延迟；线程所有返回路径发布原子完成状态。
   现有 prelaunchd policy 等待至多30秒，确保首次进程内 Metal 枚举有机会看到设备。
   失败/超时仍返回普通 UI 启动。
4. GPU archive 和 policy 替换只进入独立036链接；035触摸 producer/consumer 没有重编译。
5. 打包检查包括实际 FAT 中的五文件 addon、配套插件/Turnip SHA、4KiB CodeDirectory，
   以及本次 GPU 输入哈希。

## 主机验证

- `check-venus-metal-publication.py`：实际 publication 源码，在同步发现回调中检查属性，
  覆盖禁用、缺 transport、kext/父类/注册/分配/属性/attach 失败、重复调用和有界等待；ASan/UBSan 通过。
- `audit-venus-metal-discovery.py`：当前原始 IOGPUFamily 全部可执行字节 SHA
  `d372b021ff816aaf6f2e3ca991d0f88d2322af0e06e6bb739740f5d6d5f23b35`；
  C2/D2/getMetaClass 字节与记录一致，基类136字节/168槽。
- 最终适配虚表仅覆盖槽 `0,1,7,39,40,41,140`；其余继承原始 IOService。
  最终二进制中的 watchdog policy 确有调用等待函数的 AArch64 BL 指令。
- iOS17 编译、native link、prelink、打包与 `--check` 通过。
  自动 initializer 总量仍824字节，没有提前运行新适配类。
- `check-venus-gpu036.py` 通过：ABI、实际调用、035归档、addon及镜像逐项核对。
- QEMU OS/SystemOS raw 文件缺失，未运行新 QEMU，也未借用旧通过结果。
- 本轮没有操作手机。上述主机结果不是 A660 实机渲染结果。

## 候选

`G:/UniXNU-Port/artifacts/venus-metal-touch-036/phone/boot-venus-unixnu.img`

- image：`210463da714a7f237116ba30ec90cdc1361732874bb3fe70d3c05fd2460583b8`
- kernel：`d8ed72910365ce81ff82ffc1bd90a41f6b497aa48d1f7d7d0eed7d04f9d17577`
- GPU archive：`1995eac6d557dacf8f8a704d6d64ac39c45d1bb5cbc654d32442a124e25bb91b`
- 保留035触摸 archive：`5d71ebc57a729231b184622a454a20457fb133b21c3de9b1c14045a8c1fa04b5`
- 保留 mainline consumer：`7510fab3cb560d2f9318eacafa696ebdac7e371e9b4e2165714a66d0a6f5368e`

GPU 渲染候选，`sheng-fb-gpu=0` 保持原 CPU 上屏路径。
036随后按单次授权启动，Sending4.344s/Booting0.194s，总4.583s。
用户反馈“很卡，好像还是cpu渲染”。卡顿已记录，实际渲染后端尚未观测。
036和035的启动授权均已消费。

启动参数核对：`sheng-gpu-power=9 sheng-gpu-metal=1 zeta-gpu-metal=1 sheng-gpu-addon=1`
都在实际036候选中。它们请求开启GPU/Metal，不证明初始化或渲染已成功。
`sheng-fb-gpu=0` 控制完成帧的 CPU 上屏拷贝，不是 CoreAnimation 的软件渲染开关。
当前插件只允许 `backboardd`；其他进程返回nil。被允许进程的ABI、插件文件、registry或cache
检查失败也返回nil。缺少实机的设备发现、插件返回、UI提交完成和逐帧耗时，无法将卡顿归因于某个开关。
源码还确认最小Venus插件没有接入上游的进程内压缩偏好；不能把这一差异当成本轮卡顿原因。
当前 `cpus=1` 且CPU上屏，CPU成本仍可能影响GPU路径的流畅度，实际成本尚未测量。
核对结果见 `evidence/gpu036-render-path-review.json`。

证据：`evidence/gpu036-discovery.json`、`evidence/metal-touch036-candidate.json`，
`artifacts/venus-gpu-036/qualification.json`，
`artifacts/venus-metal-touch/kernel-link-34/`。
