# 009：从实际早期任务启动一次MG查询

2026-10-29。008已证明Data安装成功，但新增LaunchDaemons名字不在原签名缓存中，未产生查询。
009修复执行入口。MG API答案、FBS与锁屏效果仍待实机报告。

## 执行路径

原launchd的`__TEXT,__config/Boot/prng_seedctl`直接执行`/usr/libexec/prng_seedctl`，
AllowCrash=true；在记录的008启动中，该任务紧邻launchd_cache_loader之前执行。
原cache-loader的`launchd_unsecure_cache`只是验签开关，不会选择新的缓存路径。
008内核也没有编译AIR init，不能靠参数启用它。

新`MGTaskMount.h`在已存在的post-Data watchdog-policy调用点执行，只有`venus-mg-task=1`才启用：

1. 检查Data的boot目录、自有shim及原版任务是root-owned/0755普通文件。
2. readonly/union bindfs：`/private/var/ngpu/boot`覆盖`/usr/libexec`。
3. 确认原launchd_cache_loader与自有prng_seedctl都可查找。
4. 失败只记stage/status，继续原正常启动。

挂载参数用scratch+0xa00/+0xa20/+0xb00，保留原SystemOS环境的+0x400/+0x500/+0x600。
没有新增或改写系统任务缓存。现有早期任务的明确路径查找会命中shim。

`MGTaskLaunch.c`自有ARM64程序：

- 启动时独占创建`venus-mg-query-009-launch.jsonl`；已存在则只执行原任务，不再发起查询。
- fork一次supervisor后，父进程立即exec完整复制的原版prng_seedctl，保留argv/environment。
- supervisor关闭继承的标准输出管道，等5s后fork一个worker。
- worker清除补充组、setgid/setuid501；独占创建JSON/stderr后exec原已签名MGQueryProbe。
- 沿用launchd任务继承的bootstrap上下文；这点尚未实机确认。
- supervisor最多轮询30s，超时kill/reap，保存wait状态，fsync输出与journal。
- shim/exec/identity/open/timeout错误都有独立journal事件；缺输出不再被解释成MG0。

源OS任务真实EOF53440B，完整SHA：
`873619dd215aac7a61e7776f458fad231a93c234cc555d1cb469a6f2df6fc5e4`。
复制文件保留整个Mach-O及原签名；原OS文件不改写。

## 构建身份与边界

独立重链到G:输出，不修改活动worktree对象：

- 保留Data002的BootProgress归档；从前DT探针的Adreno-live归档恢复LegacyDisplayProbe成员，
  保留后来HID/AKS成员，去掉004–007镜像行为。
- 重建对照kernel：`85c80c31e1163f1033f4aa9f74565df581cd648126277dbb998e54debf26f921`。
- 加执行入口kernel：`dee27774986ba8ac0154dff235df3eeaa0cf54e186c795beac1428f252ea4965`。
- 对这份重建对照，BootProgress归档仅BootWatchdogPolicy.o内容改变；display所有成员相同。
- 同一native对象归档；RamBlock.o逐字节等于Data002保留的合格对象。
- **这不是复用008的4b1内核**；重建对照也不是已实机测试的4b1，不能偷换实机资格。
- 采用原prelinked crypto启动模式；没有禁用完整性或自检。两份kernel实际QEMU原crypto/AMFI/SystemOS路径通过。

当前shim r2：67296B、17个4KiB签名页逐页核验，SHA
`e693ec444b874ceec70a89a09c898852900d01b9b37aa1973c1a3137542463da`，
CDHash `b3a9d1d4321b5a3e3451da5eb39bbd753d4af5d5`。
新增它自己的trust模块；008的查询模块及两个原系统模块均原字节保留。
最初r1仅为主机产物，未上机；r2补齐journal低号fd情况下的标准句柄处理。

## 当前准确候选

```text
G:/UniXNU-Port/artifacts/venus-mg-query-009/phone-r2/boot-venus-unixnu.img
168960000B
SHA256 34635bc461ec668e87066a3d9bff58c07a7312ef40f8d656e3a989553d9f91c0
```

原008的ADT/seed/6GiB FD/EFI保持原字节；增加`venus-mg-task=1`、新tag与三个addon文件：

| Data路径 | mode | bytes |
| --- | --- | --- |
| /private/var/ngpu/bin/venus-mg-query | 0755 | 67232 |
| /private/var/ngpu/boot/prng_seedctl | 0755 | 67296 |
| /private/var/ngpu/original/prng_seedctl | 0755 | 53440 |

输出：`/private/var/tmp/venus-mg-query-009-launch.jsonl`、`venus-mg-query-009.json`、`venus-mg-query-009.stderr`。

## 验证

- 实际生产C wrapper在host POSIX fork/exec、真实501身份和ASan/UBSan下：success、missing-query、
  timeout、existing-output、closed-stdio五种情况通过。每次原任务立即exit0；marker拒绝重复。
- 生产mount helper的实际C在模型VFS/ASan/UBSan下覆盖selector0/1/2、源缺失、权限、copyout、
  mount、lower/own可见性各失败点，环境slots不变，boot-mount flag必复位。
- 新kernel及重建对照在6GiB QEMU到原SystemOS stage6/status0，AKS/HID初始化通过。
  **测试止于Data之前，没有在QEMU挂这个union或执行shim**。
- addon inflate/wire往返、FAT逐项读回、原seed/ADT/FD/EFI身份、boot roundtrip通过。

收据`evidence/mg-task-candidate.json`；各主机测试、native/prelink命令保存在
`artifacts/venus-mg-query-009`；QEMU在`artifacts/venus-ufs-root/qemu-mg-query-009[-baseline]`。
部分失败的主机重链尝试保留，最终仅activation-link-3/baseline-link-4用于候选。

复核：

```sh
python3 ports/UniXNU-venus/scripts/prepare-mg-task-phone.py --check
```

下一实机操作需准确009-r2镜像、三个安装文件/readonly union/正常Data写入确认。
boot完成命令不等于执行入口或MG成功；回Android后只读获取journal与两个输出即可判读。

## 已执行的一次实机启动

用户确认“已回Android，确认009-r2一次”，包括准确SHA、正常Data写入、三个文件安装和readonly union。
ADB5037核venus、fastboot核55870427；Sending4.331s/Booting0.193s OKAY，总4.564s。
授权已消费，不自动重试。日志`logs/venus-mg-query-009-r2-phone.txt`，实机记录`evidence/mg-task-phone.json`。
实际安装/union/包装器/原版任务/MG返回值/锁屏都尚待报告；下次确认返回Android后只读取回。

## 009只读结果及原版启动链对照

本次`read-20261029T052623Z`稳定快照确认三个文件全部root:root/0755且SHA正确，
但三个输出不存在；四份launchd日志仍是008原字节。
disabled.plist已成为完整1083B源码匹配XML，说明安装之后的启动策略写入也执行了。
因此不是简单的“安装失败”，也不能断言卡在mount内部；后续执行阶段待定位。
实际MG/API值仍为null。收据`evidence/mg-task-readback.json`。
用户要求沿用官方sheng启动链，已准备原4b1链010对照，见`SHENG-STARTUP-CHAIN.md`。
