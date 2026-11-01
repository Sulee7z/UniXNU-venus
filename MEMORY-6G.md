# 正常启动的6GiB内存方案

2026-10-28：用户确认1GiB正常启动最终停在87s页面，并要求“文档有建议内存设置吗，没有就给6g”。

## 文档结论

已查官方[平台/内存](https://unixnu.com/zh/porting/platform)、
[配置](https://unixnu.com/zh/reference/configuration)与
[payload](https://unixnu.com/zh/concepts/payload)。它们没有给所有设备统一的推荐容量：
`owned_memory_size`是独立的连续窗口请求，需要满足真实UEFI图、保留区、对齐和DMA地址范围。
sheng的具体容量属于该设备配置，不能当作Venus通用建议。

当前DarwinBoot `WindowSize.h`允许256MiB至8GiB，按2MiB对齐；6GiB=`0x180000000`
满足解析边界。实际分配仍由`AllocateWindow`在真实conventional-memory连续区中查找，失败会拒绝，
不会偷偷降低请求容量。

## 此前停住的证据

- userspace001在34s有1个进程，最后约87s有86个进程；用户确认随后画面不再变化。
- 没有锁屏/桌面，SWAP/COPY0；watchdogd SIGTRAP、FDR加载器exit1仍是未归因的观察。
- 当时总内存1024MiB、空闲1152个4KiB页，接近free_min1146；单次空闲页快照不证明OOM。
- `check-userspace-stall.py`核对准确已编译BootProgress源及真实核心：continuous模式在87/120/300s
  都不主动冻结。四个可选monitor回调在最终内核中是`mov w0,#0; ret`；不是正在执行复杂抓取。

按用户要求，本次选择6GiB测试内存容量对正常启动的影响；根因与修复效果仍需实机确认。

## 固件与窗口同时配置

默认固件高区原为 `[0x100000000,0x200000000)`，只有4GiB，不能仅修改ADT请求6GiB。
新增显式 `VENUS_6G_MEMORY=TRUE` / `UNIXNU_VENUS_6G_MEMORY` 分支，使高区为：

```text
Kernel RAM G: base=0x100000000, bytes=0x180000000, end=0x280000000
```

该范围完整位于本机live DT第二bank `0xc0000000 + 0x1c0000000`，无已声明reserved-memory重叠。
21个既有保留区仍覆盖，DXE heap和ABL initrd不重叠。默认4GiB固件分支也已重新核对。
这是主机内存图核对；实际设备报告见下方实机照片记录。

本候选的ADT只把 `darwinboot-memory-size` 从1GiB改为6GiB；与当前board的明确6GiB覆盖值
经实际converter生成的结果一致。其余ADT节点、随机种子、kernel/Data/trust输入保持准确对照，
build tag改为`userspace-6g-001`。板级默认1GiB控制保留，6GiB由专用候选和固件构建开关记录。

## 主机结果

- QEMU实测 `_max_mem=6442450944`（6144MiB），SystemOS mount/owner授权stage6/status0，AKS/HID通过。
- QEMU旧fixture脚本原先限制4GiB，尚未进入虚拟机就拒绝6GiB；新增主机adapter使其与
  已支持8GiB的真实DarwinBoot边界一致，保留2MiB对齐与实际分配检查。
- 6GiB固件已成功构建，编译报告含6GiB开关，实际`Sec.efi`包含对应base/length描述符。
- UniXNU、UniXNUDxe与DarwinBoot EFI模块SHA与原正常启动对照相同；固件卷更新了内存支持。
- payload回读、boot roundtrip和固件布局检查通过。没有进行新的内核代码修改。

## 准确候选

- 路径：`artifacts/venus-userspace-6g-001/phone/boot-venus-unixnu.img`
- 镜像SHA：`66f5314a97fb0fb052ded3c0c6d7ceb9d259c9eadd7519367bfef69b8ee5d660`
- 大小：168960000B。
- kernel：`4b1ae1c0bc6ea2b7dbb440099ef5c0a0c413d26aab8bfe304f1fbc8b1a2760be`
- ADT：`92c8d627f1cb667d9b3db7bdf20ab57f12aac5cb6efbff4d481b7f0c0473ae54`
- 新FD：`f9457a90d624e312d2e4f19eb6c7d61f8af41ed186f180b8f260a5b1c44b7092`

正常Data挂载、启动策略和系统服务写入保留；GPU0、单核和CPU显示参数保留。

## 实机照片

用户提供 `G:/20261028_234010.JPG`，SHA-256
`a9f9f286e4f9f7dc39aadf6ecb207eb70f565abb6ba4f29f26f4d40047224939`。画面报告
`MEM totalMiB=6144`、`root=1`、`procs=124`、`OS t=172s`；SWAP/COPY均为0，
SpringBoard仍有三条SIGTRAP退出行，非零退出计数16。UFS verified为919935个4KiB块，
read failures与integrity failures均为0。没有锁屏或桌面。

该照片按用户交接上下文关联到本候选；画面未显示完整镜像SHA或RAM-boot日志，故精确镜像身份
未由照片独立证明。单张照片也不能证明172秒之后仍在推进，或确定内存与SpringBoard失败的因果。
记录见 `evidence/userspace-6g-phone.json`。不得据此自动重启或重试。

2026-10-29重新核图补齐此前漏读的MODE：preferredScale=0、scaleOverride=0、120Hz。
这是原版FBS拒绝的参数组合。已准备早期缩放属性+保留式MG缓存刷新候选，见`LOCKSCREEN-SCALE.md`。

证据：`evidence/userspace-stall-host.json`、`highmem-6g-map-check.json`、`userspace-6g-candidate.json`；
QEMU：`artifacts/venus-ufs-root/qemu-userspace-6g/`；编译/输入快照：`artifacts/venus-userspace-6g-001/`。

```sh
python3 ports/UniXNU-venus/scripts/check-venus-highmem-map.py --six-gib
bash tools/check-userspace-6g-systemos.sh
python3 ports/UniXNU-venus/scripts/prepare-userspace-6g.py
bash tools/build-userspace-6g-firmware.sh
python3 ports/UniXNU-venus/scripts/prepare-userspace-6g.py --finish
```

已有候选目录时prepare拒绝覆盖；finish用于核对已构建产物。
