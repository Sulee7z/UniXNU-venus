# 011显示缩放修复：按原要求重建MG缓存

2026-10-29。用户要求尝试修复并多查同版本成功方式。

最新011实机未取得失效结果。原inode869和字节未变，tmp journal会受原清理任务影响；
真实APFS复现也发现UID-2/权限0缓存被原guard拒绝。012已修正并通过实际APFS改名检查，
见`SCALE-REFRESH-012.md`。以下保持011原验证记录，不把模型guard成功当实机修复。

## 采用的依据

- 官方`docs/zh/guide/mobilegestalt.md`明确：`/chosen/display-scale`提供MG缩放，
  身份变化后应删除旧MG缓存或重建Data。
- 显示/ABI指南要求保留原MobileFramebuffer接口，先CPU呈现后GPU。
- umi固定`3eb72578597d2ca16471b172d45eddc096a34a04`：iPad7,1/21H461，机主确认CPU Hello/Setup，
  其LegacyDisplayProbe从`/chosen`发布typed display-scale。
- tb128fu固定`a9c3863dedbee6f319bff16d3b609ec6cef409bf`：README报告同21H461 CPU主屏，
  相同typed scale发布流程。两个仓库所取文件逐一核Git blob/长度/SHA256，
  收据在`references/scale-fix-umi/<pin>`、`references/scale-fix-tb128fu/<pin>`。
- 这两个版本未找到独立的“FBS零缩放”补丁；成功UI记录说明原CPU接口可工作，
  不等于已证明它们遭遇或解决过Venus完全相同的故障。

010已经提供正常启动/19次SIGTRAP/5份真实FBS校验IPS，ADT早期scale2保持存在，
持久MainScreenStaticInfo仍保存0且文件SHA不变。当前优先按官方缓存失效要求验证重算。
旧001从未实机推进到缓存改名，不视为已经验证过该修复。

## 实际改动

原Data挂载、原watchdog策略完成后，normal launchd之前运行一次，`venus-gestalt-refresh=1`才启用。

1. 独占创建`/private/var/tmp/venus-scale-011.jsonl`，写begin状态并file/parent/full/UFS同步。
2. 只有初始状态确实完成同步后才尝试旧缓存失效。
3. 原三处MG缓存/偏好普通文件按同Data/UID0或501/大小检查，原子改名为原路径加`.venus-scale-011.bak`。
   `RENAME_EXCL|RENAME_NOFOLLOW_ANY`拒绝覆盖或穿越符号链接；不存在的路径跳过。
4. fsync缓存父目录及UFS，写complete状态/结果/moved/missing并同步。
5. 原正常launchd继续运行，由系统自行重建缓存；缓存操作失败保留原链和明确状态。
6. journal/备份已存在时拒绝重复本次操作，保留之前数据。

`BootGestaltCache.h`的默认001后缀仍保留，011通过macro选择独立后缀。
新增`BootScaleRefresh011.h`仅用scratch+0/+0x200/+0x800，保留SystemOS环境+0x400–0x600。
生产C模型覆盖当前moved1/missing6、缺文件、拒绝备份覆盖、重入/重启、rename/file/dir/full/medium同步失败。

当前010快照只存在7477B shared MG文件，SHA
`661cdb8356befb18dae67ecb839db8d228b513482437db2c820fed68755f16a7`；两份偏好不存在。
011 journal及三处011备份在快照中都不存在，准备器已经核验。

## 候选与身份

```text
G:/UniXNU-Port/artifacts/venus-scale-refresh-011/phone/boot-venus-unixnu.img
168960000B
SHA256 e5da7c4fd4acddb961f945a6d11d2d13b888843d56d59b47722401bea162cc41
kernel c2f380cabf82bccb80b962440292568a5f3c5c92187e0dd681f93055a19e20b6
```

独立新kernel，不声称复用010/4b1。对重建baseline85c80c31...仅BootWatchdogPolicy成员内容变化，
保留原策略，再调用新cache/journal；display成员相同、Data002 RamBlock.o字节相同。
原010 ADT/seed/trust/6GiB FD/EFI保持原字节，KT zones120/watchdogd-disable1保留。
本修复用原接口让MG重算，不提供合成MG返回值或改写原FBS校验。

## 完成的验证

- 当前实际两个C事务在ASan/UBSan模型下通过，含失败前不改缓存、独占备份及环境slots保留。
  最终收据`host-tests-r3/report.json`。
- 新kernel实际QEMU SystemOS stage6/status0、6GiB、AKS/HID通过。
- 本次还实际使用PackedRAMDisk/原Data在QEMU推进到post-Data新checkpoint。
  Data stage4/status0/RW、journal返回EIO5、cache_requested0/moved0：没有UFS同步后端时拒绝缓存改名。
  **这是实机前的同步失败保护测试，不是实际成功缓存重算或UFS持久化测试。**
- 唯一native/prelink输出使用refresh-link-2，原活动worktree对象不改写。
- 逐项FAT/原ADT/seed/trust/FD/EFI身份/boot roundtrip及`--check`通过。
- 默认新QEMU wrapper保持原行为；`--packed-data-fixture`仅用于显式Data/ADT测试。

收据`evidence/scale-refresh011-candidate.json`，所有构建/测试在`artifacts/venus-scale-refresh-011`。
首个GNU-source主机编译碰到Linuxstat64同名冲突已改为DEFAULT_SOURCE；失败输出保留，最终r3通过。

## 实机判读

| 结果 | 解释 |
| --- | --- |
| begin+complete0、moved1/missing6，备份原SHA、新缓存scale2且出现界面 | 缓存失效与重算通过，继续验实际显示/交互 |
| complete非0 | 精确按rename/fsync/权限/backup等错误定位，不称缓存已刷新 |
| begin没有complete | 执行进入但后续未完成，结合Data/launchd证据定位 |
| complete0、备份正确，新缓存仍scale0/FBS仍拒绝 | 旧缓存被隔离，但计算/输入链仍需检查 |
| 无journal/备份/新日志 | 未证明进入该操作，不以缺文件充当零答案 |

读取器已支持011 journal及三处备份，旧证据输出保留。当前Data页数据约508.9MB，
下次读回应允许明确的1GiB上限并继续只读；不默认重置Data。

复核：`python3 scripts/prepare-scale-refresh011-phone.py --check`。
准确镜像、三文件备份改名、状态写入、同步及正常Data写入需要本次具体操作确认。

## 本次实机启动已执行

用户“Android中，确认011一次”批准上述准确镜像、三处独占缓存备份与journal/同步/正常Data范围。
ADB5037核venus、fastboot核55870427；Sending4.329s/Booting0.193s OKAY，总4.565s。
授权已消费，不自动重试。日志`logs/venus-scale-refresh-011-phone.txt`；
实机记录`evidence/scale-refresh011-phone.json`。
同步/备份/journal/重建缓存/新scale/界面均待手动返回Android后的只读证据，读回上限明确1GiB。
