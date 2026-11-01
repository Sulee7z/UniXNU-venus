# 继续XNU10063：zeta全链路参考与039插件/信任修正

2026-10-30。用户明确要求保留现有内核版本、继续GPU移植、改为真正iOS/iPhone系统，
并停止HackiOS路线，改参考完整 `none24smu/UniXNU-zeta`，包含ARM64e方案。

## 参考身份和范围

- zeta HEAD重新核对：`eb489285a1d9153872f00c93ebb519a269b249b5`。
- `audit-zeta-reference-tree.py` 对完整188个文件核对Git blob/长度/SHA，当前本地快照全部一致。
  固定副本和manifest在 `artifacts/venus-zeta-audit/reference/`。
- 阅读其完整README，以及GRAPHICS三个专题、board/feeds/CI脚本、graphics profile、
  GPU/插件/TRUST/ARM64e相关实现与对应测试。
- zeta当前OS目标是iOS26.5.2/XNU12377，不把其OS profile和私有ABI直接换入Venus。
  当前NativeAdreno→Turnip→metal2vulkan→NativeAdrenoMetal路径与其原生路线一致。
  不选择其OnePlus AIR/Gallium替代实验，也不切换到Redwood/MiniIOSurface栈。

## 保留当前内核版本的iPhone路线

真实iPhone XR (`iPhone11,8`/n841ap) 的可查iOS17目标是17.7/21H16。
已仅提取BuildManifest和kernelcache，核对实际Darwin23.6.0、
`xnu-10063.142.1.700.5`、ARM64e subtype2。当前native源仍为XNU10063.141.1。
`XnuPrelink.macho()` 对该原始kernelcache明确返回：
`Only ordinary little-endian ARM64 is supported`。
证据：`artifacts/venus-iphone17-compat/21H16/report.json`。

原生XNU源码本身不是一个只能服务iPad的内核。平台CPU/UFS/触摸和现有native代码可保留；
iPhone身份必须与真实iOS根卷及用户态配套，组件和前端ABI需逐项核对。
现有预链接组件能否复用也需要OS接口验证，不能仅凭设备系列标签宣称全部可用或全部须替换。

## ARM64e的准确采用边界

zeta方案是离线代码证明后建立普通指针ABI，不是PAC硬件仿真，也不是只改Mach-O subtype。
需要同时处理指令、dyld与cache认证指针、分页、代码签名/信任和所有指针生产/消费方。
其 `rewrite-zeta-userland.py` 还为macOS26 KDK AMFI写入platform_identifier26/CS_RUNTIME；
Venus当前使用原始iOS17 AMFI，不能直接照搬该签名策略。
SM8350相同也不能代替Venus启用核的功能寄存器及keys-off合同确认。

当前XNU10063的 `vm_shared_region_slide_page_v3/v5` 在认证分支后已经无条件
`memcpy(rebaseLocation,&value,...)`，因此无PAuth时会保存普通目标指针。
zeta的 `native-shared-region-plain-auth.patch` 修的是XNU12377变化，这条补丁无需重复套用。
另一方面，当前4KiB pager仍按输入的 `slide_info_page_size` 直接拷贝。
若目标cache使用16KiB slide页，则须适配其跨页复制/链处理；目标cache与完整用户态转换尚未完成。

执行的参考测试：

- userland PAuth lowering：4 tests通过（含36种组装/解码正例、拒绝和不改动控制）。
- bounded kernel PAuth plan：8 tests通过。
- code proof：17 tests通过；两个实际Apple改写产物检查因未提供产物而跳过。
- 原始EL1正/负probe在本机QEMU遇到 `retab/original: FAIL` 后停止，不能报整套通过。
- 独立正例probe执行21个实际lowering结果，寄存器/SP/NZCV/link合同通过。
  保留上述负例问题，未借此宣称Apple用户态或Venus硬件通过。

## 039：按zeta补当前插件接线

当前简化插件缺少上游进程内framebuffer/IOSurface压缩约束、持久cache优先级及初始化失败信息。
新入口：

1. 在原iOS17/536-byte `_MTLDevice`合同下，设置与zeta一致的plain-row压缩约束。
2. 先尝试用户Library/Caches下的backboardd持久目录，再尝试用户cache/temp，核对路径截断和cache写入条件。
3. 串行化每进程device初始化；marker、client选择、loader、registry、cache/runtime拒绝都有实际原因日志。
4. 保持当前被选进程backboardd；不将iOS26的Mercury/SBRenderer名字直接加入iOS17。

这些是接线差异修正，不是已捕获038 GPU未生效的唯一根因。Device创建和真实GPU像素仍未实机验证。

## 静态TRUST修正

原打包把包含两个owner条目的新模块放在最前，原系统两个模块随后。
当前XNU10063 `kern_trustcache.c:1074–1090`：第一模块必为static，后续模块需second-static或engineering许可。
是否跳过原模块取决于真实runtime设置；没有本轮加载日志，不能断言038具体跳过了哪个模块。

039按zeta单静态模块模式合并：2554个原始条目及其全部四字节属性逐项保留，新增plugin/Turnip两个条目。
一个module，共2556 entries，避免依赖后续模块许可。没有更改kernel AMFI规则或原始程序的签名。
四个wire/原属性冲突/坏几何/去重测试通过。

## 构建与验证结果

- cache/path实际POSIX失败用例ASan/UBSan通过。
- 新Objective-C入口以原真实iOS17配方/-Werror编译。
- NativeBridgeMetalFrontend对象与Rust/Turnip既有实现保留，新bundle链接及4KiB CodeDirectory独立验证通过。
- `check-venus-zeta039.py`：实际FAT addon五文件、签名、单static2556条目、全部原属性、源码/对象和镜像SHA核对通过。
- 039与038的kernel、ADT、Data seed逐字节一致；内核仍为
  `bd312e850bc3741d27c79cf748990f59fadd5f023c9e66ec424507adb2cd3423`。
- 039 `--check` 通过；没有新的完整SystemOS QEMU通过，也没有任何手机操作。

候选：`G:/UniXNU-Port/artifacts/venus-metal-touch-039/phone/boot-venus-unixnu.img`

SHA256：`ab13d6cacbd2052156dac1d6c901c0263623aaa6f79cf3f2b3dfdcb466485733`

039尚未授权/启动，仍是当前iPadOS17系统的GPU接线候选；iPhone17用户态迁移未完成。
原iOS16.7.16准备输入保留为历史产物，不继续该内核降版路线。

证据：`artifacts/venus-zeta-audit/qualification039.json`、
`artifacts/venus-zeta-audit/plain-pointer-el1/report.json`、
`evidence/zeta039-reference-and-iphone17.json`。
