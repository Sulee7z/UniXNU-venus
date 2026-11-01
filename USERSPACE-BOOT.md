# 正常用户态 / CPU显示启动尝试

2026-10-28：Data002的受控跨重启读回已经通过，用户要求继续尝试进入系统。

## 镜像

- 路径：`artifacts/venus-userspace-001/phone/boot-venus-unixnu.img`
- SHA-256：`72630cd0d5771caec5ce7c870a371fdd0c863dcd5c0b89b0261bccf97b5ca897`
- 大小：168960000字节。
- 内核：`4b1ae1c0bc6ea2b7dbb440099ef5c0a0c413d26aab8bfe304f1fbc8b1a2760be`
- ADT：`f3b2327feaa5fa4888831f7bbd4d19eb15184c77471d26ed77e5ecd41eccd152`

从Data002 read的准确payload派生，只替换菜单配置：去掉`venus-data-check=2`与
`venus-data-token=...`，build tag改为`userspace-001`。正常参数来自当前完整board数组。
校验代码默认关闭，因此原启动流程会继续执行既有启动策略并进入launchd。

## 核对范围

- 已验证内核、ADT、Data seed、trustcache和固件逐字节保留。
- 当前board和实际converter重新生成的ADT与保留侧车除随机种子外一致；镜像使用原已测字节。
- 保留1GiB owned、post-SystemOS Data发布、`sheng-data-persist=2`和1024MiB尾保留区。
- 保留AKS/HID初始化、sRGB、scale2与CPU呈现参数；GPU呈现/探测为0。
- 同一内核已有真实QEMU SystemOS mount/owner授权检查，新的菜单不启用任何测试停止点。
  这不是QEMU用户界面成功的证明。
- payload逐项读回、boot roundtrip、固件一致性通过。

本轮正常运行会包含APFS Data挂载、既有`sheng-lite`启动策略文件更新及普通系统服务的数据写入。
它不是只读marker测试。具体手机重启与一次RAM boot需要准确镜像授权。

## 实机观察

确认SystemOS/Data mount returned与launchd/后续进程推进，再观察：

1. 是否出现锁屏或桌面。
2. `SWAP`、`COPY`、`retired`是否增长，以及显示是否真正接管画面。
3. 若仍停在诊断页，保存运行时间、procs、最后启动阶段和CRASH行。

原FBSDisplayMode错误仍是此前证据中的未解决项；当前准备工作不宣称UI已经可用。
物理触摸/按键继续作为下一独立阶段。

## 复现

```sh
python3 ports/UniXNU-venus/scripts/prepare-userspace-phone.py
python3 ports/UniXNU-venus/scripts/prepare-userspace-phone.py --check
```

打包器拒绝覆盖既有目录。证据：`evidence/userspace-candidate.json`。
准确输入收据：`artifacts/venus-userspace-001/linked-inputs/`。

## 一次授权RAM启动与当前照片

用户对上述准确镜像和正常Data/系统服务写入范围确认“已回Android，确认正常启动一次”。
核对venus/55870427后执行一次：Sending3.688s、Booting0.193s OKAY，总3.923s。
日志 `logs/venus-userspace-001-phone.txt`；实机记录 `evidence/userspace-phone.json`。
授权已消耗，已观察到launchd签名接受与系统服务启动，仍未出现锁屏/桌面或CPU交换。

| 照片 | 屏幕时间 | 进程/结果 |
| --- | --- | --- |
| `G:/20261028_192645.JPG` | 34s | procs1；launchd exec signature accepted；失败退出0，SWAP/COPY0 |
| `G:/20261028_192932.JPG` | 约87s | procs86，securityd p112签名接受；失败退出7，SWAP/COPY0；UFS读取失败/完整性错误0 |

第二张的可见失败为watchdogd p52/p92 SIGTRAP、`IOMFB_FDR_Loader` p79 exit1
（照片raw status100是十六进制等待状态，不是退出码100）。初次小图把FDR误读成FIR，
放大图 `artifacts/venus-userspace-001/failures-192932.png` 已核对正确名称。
可见空闲4KiB页1152；单次空闲页快照不足以认定OOM，需结合后续行为与错误记录。
这两张说明服务启动在推进；尚未证明可用系统界面。

**用户随后确认：87s照片就是最终不再变化的页面。** 因此该次启动记录为屏幕/启动推进停住，
不再要求继续等待。准确失败记录保留在 `evidence/userspace-phone.json`。
按用户“无通用文档建议就给6g”的要求，已完成6GiB窗口与对应固件的主机准备，见 `MEMORY-6G.md`。
用户随后提供了6GiB测试上下文的实机照片；画面报告6144MiB和root=1，但仍无UI、SWAP/COPY为0并有SpringBoard SIGTRAP。详细转录及镜像关联限制见 `MEMORY-6G.md` 和 `evidence/userspace-6g-phone.json`。

### 原系统启动任务核对

`scripts/inspect-userspace-launch-jobs.py`只读已部署21H461 OS原始镜像，核对镜像/reader SHA，
复用已检查的APFS读取逻辑；补充严格marker/长度检查的decmpfs9原样数据读取后，
取得原版plist和相关可执行文件。输出在 `artifacts/venus-userspace-001/launch-jobs/`，
证据 `evidence/userspace-launch-jobs.json`。

- `com.apple.iomfb_fdr_loader`运行 `/usr/bin/IOMFB_FDR_Loader --launchd_boot`，RunAtLoad为true，
  监听`IOMFBLaunchFDR`/`IOMFBLaunchFDRUserCal`属性的IOKit事件。程序包含FDR显示校准
  数据读取、panel/ALS/DIC身份和IOMobileFramebuffer接口；二进制中的错误字符串只是可能路径，
  未取得它本次退出时的实际错误文本。
- `com.apple.watchdogd`监听IOWatchdog服务，KeepAlive/SuccessfulExit=false；
  程序包含服务发现/打开/检查失败路径。照片SIGTRAP尚未映射到具体失败条件。
- 这些plist不能证明任一退出阻塞了SpringBoard；不根据进程名直接禁用任务或添加硬件服务。
  下一观测为后续SpringBoard/显示进程是否出现、SWAP/COPY是否增长及准确错误。
