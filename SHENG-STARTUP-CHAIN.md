# 原版sheng启动链复用与010对照

2026-10-29。用户明确要求对照`https://github.com/UniXNU/UniXNU-sheng`。
API确认HEAD仍为`08cde20edc3254ed6f7df8d0f5384fb887786e8f`，重新取回19个相关文件，
逐一核Git blob SHA1/长度与SHA256，保存在`references/sheng-startup/<pin>`。
它是SM8550的设备配置，启动器和主要XNU交接实现来自共享UniXNU组件。

## 可以直接沿用的链

```text
Venus UEFI发布payload FAT
→ UniXNU读取unixnu.toml
→ DarwinBoot交接kernel/ADT/Data/trust
→ XNU原OS根挂载/owner检查
→ SystemOS union挂载及环境参数
→ Data挂载
→ sheng_boot_watchdog_policy
→ 原/sbin/launchd
→ 原launchd_cache_loader/缓存服务/系统早期任务
```

Venus已有的SystemOS/Data/launchd主体顺序与它一致。Data002保留的watchdog-policy源码，
去掉本地Data资格检查hook后，与此次官方源码归一化比较一致。
无需用自有进程替换这条通用启动链。

原board实际启用、当前4b1内核也包含实现的两个通用项：

| 参数 | 作用 |
| --- | --- |
| sheng-disable-watchdogd=1 | 原启动策略把未实现后端的watchdogd写入disabled.plist |
| kt_fixed_zones=120 | 同版本XNU kalloc类型分配器的固定zone数量 |

当前Venus原启动参数没有这两项。官方还有ml-timeout-lock-panic-scale/boot-ui-focus4，
但4b1内核没有对应实现，不把这些字符串当有效功能。

## 板级输入仍使用Venus

Sheng的CPU/GPU电源、A740/Metal/scanout、SMP、触控、UFS SID0x60、userdata布局与Data UUID
是SM8550板级输入。Venus使用已测SM8350/SID0xe0、64GiB unixnu、自己的UUID和6GiB窗口。
相同的是21H461/iPad7,1软件ABI与根OS UUID，不能据此替换其余输入。

BootLog.c确有持久内核日志实现，但它依赖native_ufs_log_*等后端与Sheng的日志/export窗口；
需要按Venus保留区适配并编译。复制参数不能生成未链接的日志写入器。

## Seed初始化也不是完全相同

共享`seed-data-skip-setup.py`会合并迁移/Setup/SpringBoard/managedconfiguration的五份偏好，
选择跳过Setup进入SpringBoard；可选no-auto-dim。
对本次只读快照检查发现：migration的LastSystemVersion与SpringBoard的BKNoWatchdogs等未设置，
purplebuddy及managedconfiguration相关三份文件不存在。
原路径、真实EOF、SHA与键差异已保存在本次快照`sheng-startup-prefs/report.json`。

这说明Seed/当前持久Data并非该skip-Setup配方；不证明它造成零缩放，也不证明跳过Setup是唯一有效启动模式。
010先对齐原启动链的两个通用项；Seed偏好合并是另一个明确操作范围。

## 009读回已确认的阶段

用户授权只读，快照`artifacts/venus-data-forensics/read-20261029T052623Z`：
50274页/31段/205922304B，前后metadata稳定、SHA/覆盖通过。
三个009文件均为root:root/0755，完整字节匹配payload。
009-launch.jsonl/009.json/009.stderr均无目录记录，所有四份launchd/cache-loader日志仍与008逐字节相同。

disabled.plist从1263B binary变为1083B XML，SHA
`510ba0f8fb4523f45ea0696a21c5f8c96744ff8025dcb5a62cca3f50e701a138`，
完整字节等于009编译源码生成的策略。源码先执行MG mount helper，再写策略，
因此helper已返回或被gate跳过；不能只凭没有journal宣称安装失败或mount内部卡住。
后续fstat/marker/launchd exec与实际mount status仍没有实机checkpoint。
收据`evidence/mg-task-readback.json`。旧008日志不能被归因到009。

## 已准备010原链对照

```text
G:/UniXNU-Port/artifacts/venus-sheng-chain-010/phone/boot-venus-unixnu.img
168960000B
SHA256 5f9061214acfd829ec893af61904d438844e1fb4ae584122565360653fb9a57d
```

采用已实机进入用户态的kernel4b1ae1c0，和002的原ADT/seed/trust/6GiB FD/EFI；
功能参数只加入上述两个通用项，tag改为sheng-chain-010。
使用原正常/sbin/launchd流程；没有009的实验/usr/libexec union或新查询任务。
原watchdog-policy会正常改写Data的disabled.plist，以启用此次选定策略。

实际QEMU在两个新增参数下仍到SystemOS stage6/status0、6GiB、AKS/HID初始化通过；
测试在Data之前停止，未实测新的disabled.plist或用户态UI。
逐项FAT读回/原输入身份/boot roundtrip通过，镜像未上机，MG/UI恢复未验证。

收据`evidence/sheng-startup-comparison.json`、`evidence/sheng-chain-control-candidate.json`。
复核：`python3 scripts/prepare-sheng-chain-control.py --check`。

010随后获“Android中，确认010一次”准确镜像/正常Data及原策略写入授权并已启动一次：
ADB5037核venus、fastboot核55870427，Sending4.331s/Booting0.193s OKAY，总4.564s。
日志`logs/venus-sheng-chain-010-phone.txt`；实机记录`evidence/sheng-chain-control-phone.json`。
授权已消费；界面/新日志/策略效果仍待单次观察和Android返回后的只读取回。

010只读取回现已完成：新日志完整参数匹配、early boot/原任务/bootstrap成立，watchdogd停用已验证。
用户报告计数持续；日志中SpringBoard19次SIGTRAP，5份真实IPS均在FBS显示模式初始化的同一BRK。
正常启动链取得实机证据，显示缩放故障仍在。详见`SHENG-CHAIN-010-RESULT.md`。
