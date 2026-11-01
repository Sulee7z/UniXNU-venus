# 012：修正真实缓存元数据识别，并保护状态与备份

2026-10-29。用户提供`G:/20261029_154011.JPG`并确认011无系统界面、返回Android允许只读。
照片SHA `4a45bd0273eecf524be3e9cdac47829bd0e93175d390dc96499a08a2e53d8a2c`。

## 011实际结果

只读快照`read-20261029T074228Z`，141394页/72段/579149824B，前后metadata与全部SHA/覆盖校验通过。
原缓存仍inode/private_id869、7477B、SHA661cdb...；三个011备份和tmp journal均不存在。
原launchd新log参数确实匹配011，early boot complete，3条SpringBoard SIGTRAP退出；用户未见界面。
旧5份IPS保留自010，不当作新的011报告。

两项缺陷已找到：

1. **状态位置不可靠。** 原OS `/tmp` symlink实际目标`private/var/tmp`；
   原launchd早期`dirs_cleaner`确实清理/tmp，pre-launchd journal不应放在其中。
   原路径/二进制只读证据在`artifacts/venus-scale-refresh-012/cleanup-inspection`。
2. **缓存安全检查错误拒绝真实文件。** 用捕获的真实APFS元数据和原7477B缓存，在实际QEMU重现：
   lstat报告UID4294967294(-2)、mode32768(S_IFREG且权限0)、size7477；
   旧检查只接受UID0/501，返回EPERM1、moved0。不是已完成失效后又计算0。

011 exact运行的同步失败步骤仍因tmp journal缺失而未确定。UID拒绝点是在同一真实缓存元数据的
APFS路径上确切复现，不能把它冒称为从缺失journal读到的唯一实机分支。
其新trace最后一块因手动重启不完整（0x5bea0），有效解压前缀保留；不称缓存文件损坏。

## 修复

- 仅对**共享MG缓存这一个固定路径**，在同owner Data、普通文件/大小限制成立时，接受实际
  UID-2且权限0的元数据；其它偏好仍要求root/mobile，异常权限与文件类型继续拒绝。
- 创建root-owned0700目录`/private/var/db/venus-scale-012`，不放在临时/缓存清理目录中。
- 三个缓存源分别独占改名到`cache-0.plist`、`cache-1.plist`、`cache-2.plist`，
  检查同Data/普通类型，RENAME_EXCL/NOFOLLOW_ANY不覆盖原备份。
- `refresh.jsonl`记录source UID/mode/size、源检查、rename、源/备份目录同步、full/media诊断及complete。
- 缓存本身按原rename/父目录/medium同步事务执行。额外journal FULLFSYNC诊断不能代替或阻止该事务；
  cache medium错误仍返回并记录，不伪装成功。
- 错误不改变原watchdog-policy返回值，原launchd继续；已有journal拒绝重做。

同010 ADT/seed/trust/6GiB FD/EFI与原启动参数保留，新kernel只改重建基线的BootWatchdogPolicy成员。
新kernel不是010/4b1，但原Data002 RamBlock.o与所有display归档成员身份核对保留。

## 不只是模型测试

从这次Data快照生成**QEMU专用**fixture：完整metadata/空间映射与原MG缓存数据保留，
其它live file data归零以满足256MiB loader限制。不是可安装的用户卷副本或生产seed。
178833136B、SHA363b32e1...，receipt保存在`snapshot-fixture/report.json`；原快照不修改。

实际QEMU验证链：

| 版本 | Data状态 | 原缓存metadata | 结果 |
| --- | --- | --- | --- |
| 旧检查 | stage4/status0/RW | UID-2/S_IFREG/7477 | EPERM1、moved0，拒绝点source_validation |
| 修正检查 | stage4/status0/RW | 相同 | rename成功、moved1/missing6，journal status0 |

修正版本已经跑过真实APFS改名与两个目录fsync；missing6证明程序经过它们后完成两缺文件扫描。
最终cache status5仅因为QEMU没有UFS medium，真实错误保持记录；不称实机持久化/UI已验证。
RootSystemOS/6GiB/AKS/HID检查也通过。

实际C ASan/UBSan模型同时覆盖旧默认、UID-2正确缓存、异常权限拒绝、偏好UID不放宽、
独占备份/marker重复拒绝、FULLFSYNC与cache事务分离、rename/write/目录/medium错误、env slots保持。
最终使用host-tests-r3、refresh-link-3、qemu-data-checkpoint-r3。

## 准确候选

```text
G:/UniXNU-Port/artifacts/venus-scale-refresh-012/phone/boot-venus-unixnu.img
168960000B
SHA256 38245b0ec67db7766f9ef91ce251569c199872bf94e133b53c81e6b7c17cda11
kernel c1c16fbc9a9630ea3ff46e9cefe196612cd4a6c9677419333cb5409ed115c68c
```

文件/FAT/保留输入/boot roundtrip及prepare --check通过；收据`evidence/scale-refresh012-candidate.json`。
读取器已支持protected012 journal和3备份。后续实机一次授权范围：normal Data写入、
创建上述目录/journal、3固定cache源→3固定backup路径的独占改名、目录与medium同步。
目标验证备份原SHA、新生成缓存缩放和界面，缺报告/非0状态不称修复成功。

012随后获“Android中，确认012一次”准确镜像/目录/3源→3backup/journal/正常Data与同步授权。
ADB5037核venus、fastboot核55870427，Sending4.329s/Booting0.193s OKAY，总4.566s。
唯一一次，授权已消费。日志`logs/venus-scale-refresh-012-phone.txt`，收据`evidence/scale-refresh012-phone.json`。
等待Android返回及只读确认后核journal、backup/fresh缓存与界面；不自动重试。
