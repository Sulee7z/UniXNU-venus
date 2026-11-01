# 锁屏推进：零缩放模式与 MobileGestalt 缓存

2026-10-29，接续 `G:/20261028_234010.JPG`。

最新010已经正常持续启动并得到5份真实FBS校验IPS，缓存仍旧scale0。
011把官方缓存失效接在原策略之后，加入持久begin/end与独占011备份，
实际QEMU推进到Data后的同步拒绝checkpoint，不再仅用SystemOS前的测试代替此路径。
准确新候选和资格边界见`SCALE-REFRESH-011.md`。以下001为历史失败记录。

## 当前实机结果：001在SystemOS入口停滞

新照片`G:/20261029_083930.JPG`，SHA
`1a54ca764fc70d3931447e13b081c12f75e18d31a8443b40014f25b39fcf9f41`：
OS t=2s、root1/procs1、6144MiB、free4K1490219、UFS verified480/requests504，
读取和完整性错误均0；最后阶段SystemOS mount enter，无MG CACHE、无CRASH，SWAP/COPY/CLIENT均0。
用户确认“一直停在2秒”。本轮启动推进失败，缓存刷新与锁屏修正结果仍未知。

`check-lockscreen-stall.py`核对当前构建与Data002实机基线：

- RamBlock的源、两层发布补丁、实际NativeRamBlock.o及storage-bindings.o完全一致。
  ar整体SHA不同，但两个成员逐字节一致；不能据归档SHA差异认定驱动回退。
- UFS仍是既有合格归档；Data延后发布补丁没有丢失。
- 实际`load_init_program`先SystemOS、再Data选择/挂载、最后调用带缓存刷新的启动策略。
  照片没有证明运行到该缓存操作。两个PC是历史timer样本，不是异常或当前卡死位置。
- 相同43825a72内核已在QEMU完成SystemOS，但该虚拟环境没有物理UFS；不能据此排除实机问题。

主机记录`evidence/lockscreen-scale-stall-host.json`，原始反汇编/归档/裁剪在
`artifacts/venus-lockscreen-scale-stall/`。目前未确定实际锁等待或读请求故障。

### 002缩小范围的对照候选

复用上次已到用户态的4b1ae1c0内核，保留001的新ADT（早期scale2/rotation0）、6GiB固件及
原Data/trust。不编入或调用缓存改名代码。相对原6GiB控制仅更新早期ADT、tag与Tools菜单。
这用于隔离新内核/初始化时序变化，不是已证明的SystemOS修复。

```text
G:/UniXNU-Port/artifacts/venus-lockscreen-scale-002/phone/boot-venus-unixnu.img
SHA256 345074da0e66babb5503e8b5f2d5854b8c6474c4c2a34b53b9895ea6bdd647d0
168960000 bytes; kernel 4b1ae1c0bc6ea2b7dbb440099ef5c0a0c413d26aab8bfe304f1fbc8b1a2760be
```

实际当前board/converter对照、payload逐项读回、固件/内核/Data/trust身份与boot roundtrip通过。
复核原同SHA内核的6GiB SystemOS/AKS/HID QEMU收据；本次打包没有重复运行QEMU。
准备器`scripts/prepare-lockscreen-scale-control.py`及`--check`；证据
`evidence/lockscreen-scale-control-candidate.json`。002尚未授权上机。
验收先看SystemOS是否返回、进程是否超过1，再看锁屏或FBS参数；002不会出现MG CACHE行。

## 照片中已有的证据

此前接手时漏读了照片的 MODE 字段。裁剪图保存在
`artifacts/venus-mode-scale-analysis/mode.png`、`memory.png`：

```text
p156 SpringBoard sig5 src=EL0
PC=1b07c4744 LR=1b07c4744 ESR=f2000000 slide=113f4000
MODE w=1440 h=3200 p=0 so=0 hz=405e000000000000 g=1 hdr=0 r=0 v=0
MEM totalMiB=6144 free4K=1082180
```

`p` 是 preferredScale；`so`、`hz` 是 double 原始位。刷新率解码为120Hz，
空闲页约4.13GiB。UFS verified应为 **919935**，此前的919995转录已纠正。
PC减slide仍为`0x19f3d0744`，实际21H461 SystemOS字节为`00 00 20 d4`。

原版初始化器在`0x19f3d05ec`检查preferredScale。为0时调用
BaseBoard的近零判定（`0x18f6e545c`，`fabs(x)<2^-52`）；scaleOverride同为0
会在`0x19f3d061c`进入失败分支，policy1通向已拍到的BRK。无需把SIGTRAP推测为OOM。

## 查到的读取路径

从已部署SystemOS只读解析：

- `CADisplayMode`的缩放getter位于`0x189570760`。主屏无单独模式缩放值时，
  它查询`MGGetFloat32Answer("main-screen-scale", 2.0f)`，再转换为整数。
- 该MG入口为`0x1a020afe4`。MG的显示信息采集在`0x1a0215704`，
  读取`IODeviceTree:/chosen`的`display-scale`，属性读取失败时默认值为0。
- `0x1a020fb6c`接受CFNumber或恰好4字节的CFData；CFData用原生小端u32读取。
- 当前旧ADT没有display-scale/display-rotation；`LegacyDisplayProbe.cpp`只在
  GOP映射回调中动态发布2/0。当前内核也没有MobileGestalt缓存失效代码。

这些是原版静态路径与实机零值的组合证据。**尚不能区分旧缓存、属性读取失败或初始化时序**。
新候选针对早期属性发布和旧缓存刷新，不修改原版FrontBoard/QuartzCore/MobileGestalt指令。
解析输出位于`artifacts/venus-mode-scale-analysis/cache/`，包括该照片的独立symbolication.json。

## log-capture 指南带来的调整

已阅读[官方日志指南](https://unixnu.com/porting/log-capture)、
[启动顺序](https://unixnu.com/zh/porting/bring-up)、
[显示](https://unixnu.com/zh/porting/display)与本地官方
`docs/zh/guide/mobilegestalt.md`。

- Advanced Logger只能导出ExitBootServices之前的固件日志，不能从旧UEFI菜单取回SpringBoard错误。
- Venus固件已包含AdvancedLogDxe、Mu producer和QR库。虽然board配置tools=true，
  旧正常用户态打包器手写配置却漏了Tools项；本候选使用官方`type=action/action=tools`格式补入。
- 持久内核日志仍需单独接入writer、boot ID、完成标记、同步和匹配reader，再做一次手动闭环。
  既有unixnu末端32MiB预留区不是已工作的日志；本候选不启用该writer。
- 本次照片已有模式字段，因此先利用该证据修正缩放输入。原计划中的独立MODE保留补丁未应用，
  现有通用崩溃环仍可能被后续崩溃覆盖。

## 候选变化

1. board的`[adt.chosen.u32]`明确写入display-scale=2、display-rotation=0。
   当前实际converter生成新ADT；与旧6GiB侧车比对，只多这两个属性，随机种子等其余字节保留。
2. `BootGestaltCache.h`通过候选参数`venus-gestalt-refresh=1`在Data挂载后、launchd前运行。
   默认关闭；只在当前已确认可写Data上处理以下三个官方缓存/偏好文件：

```text
/private/var/containers/Shared/SystemGroup/systemgroup.com.apple.mobilegestaltcache/Library/Caches/com.apple.MobileGestalt.plist
/private/var/mobile/Library/Preferences/com.apple.MobileGestalt.plist
/private/var/mobile/Library/Preferences/com.apple.mobilegestalt.plist
```

每个现存文件改名为原路径加`.venus-scale-001.bak`。检查同一Data设备、普通文件、属主与大小；
`RENAME_EXCL|RENAME_NOFOLLOW_ANY`禁止覆盖备份及经过符号链接。不存在则跳过；错误原样记录。
改名后fsync父目录，最后调用既有UFS同步。操作不删除原文件内容。

3. 普通诊断页第29行显示`MG CACHE rc=... moved=... missing=...`，掩码位0/1/2对应上述路径。
   `rc=0`表示本轮完成；非零不能当作刷新成功。候选仍正常启动，不添加自动复位或诊断等待。
4. 保留6GiB固件、GPU0/CPU呈现、单核、Data seed与trustcache。原Data验证和故障采集代码一致。

## 已完成检查

- 实际C缓存事务的ASan/UBSan：关闭/非法参数不操作、缺文件、已有备份拒绝、同设备/类型限制、
  单次执行、rename/fsync/UFS错误传播与备份保留通过。
- 实际像素writer：第29行成功/错误刷新，process行所有权、padding和显示交接通过。
- 完整内核编译与预链接成功。
- 新内核在QEMU实测6144MiB，SystemOS stage6/status0，AKS/HID初始化通过。
  该检查点在Data/launchd之前，不是实际缓存改名或锁屏验证。
- payload逐项读回、两项ADT差异、固件/loader/Data/trust身份与boot roundtrip通过。

## 准确镜像与下一次上机

```text
G:/UniXNU-Port/artifacts/venus-lockscreen-scale-001/phone/boot-venus-unixnu.img
SHA256 bd29388df4a1dd58be3fd81262f767f0ff2ea0ae92a0277faea379eb7ca3e251
168960000 bytes
kernel 43825a72e2c83e0db8eb30a58099a84c3fb77821d3fc323709560a175ae37d3a
ADT 5b29def26686809e164ec4655203292a4c8e99c9374ce0c3b2e0162a5076a965
```

用户已确认“已回Android，确认一次”，并授权上述镜像、三个文件的备份改名及正常Data写入。
ADB5037核venus、fastboot核55870427后执行一次RAM boot：Sending4.327s、Booting0.192s均OKAY，
总4.563s。日志`logs/venus-lockscreen-scale-001-phone.txt`；实机记录
`evidence/lockscreen-scale-phone.json`。授权已消费；新照片确认SystemOS入口停滞，见本文当前结果。
验收看MG CACHE状态、是否仍有p=0的FBS崩溃、SWAP/COPY是否增长，以及真正可见的锁屏。
若失败，拍清MG CACHE与完整CRASH行；不要因Sending/Booting OKAY就标为锁屏成功。

复现：

```sh
python3 ports/UniXNU-venus/scripts/check-gestalt-refresh.py
python3 ports/UniXNU-venus/scripts/check-a660-live-screen.py --output artifacts/venus-mode-scale-analysis/screen-tests
bash tools/build-venus-data-publication.sh
python3 ports/UniXNU-venus/scripts/prepare-lockscreen-scale.py
python3 ports/UniXNU-venus/scripts/prepare-lockscreen-scale.py --check
```

准备器拒绝覆盖候选目录。证据`evidence/lockscreen-scale-candidate.json`，
已编译源与测试快照在候选`linked-inputs/`；原始6GiB镜像保留。
