# Data 持久视图的发布顺序

2026-10-28；按官方 UFS 步骤继续主机检查。用户要求其回来后再上机。

## 最新：001恢复镜像在SystemOS入口停住，002顺序修正待实机

**002最新实机结果：**照片 `G:/20261028_181833.JPG`，SHA
`c85a44bf70c33205078cfcf3cbbbc7f4dfcab969c652c1f5ce68a69d5f1a78c4`，39s显示
`DATA CHECK phase=2 step=6 rc=2 match=0 bytes=0 token=dbb03eb9 store=2`。
本轮越过SystemOS阻塞、Data挂载完成且监视继续，但打开原marker仍ENOENT。
因此延后发布未解决已知文件持久化；`data-read-recovery-002-phone.json`中推进通过、
文件及跨重启读回均false。下一步按 `UFS-GUIDE-RECHECK.md` 补写入/恢复证据，不把同步猜测记为根因。

`G:/20261028_174145.JPG`（SHA `2da6a246e8ba1f90d35ff114d6e6554a7abc07fb7571d1d0cff4a49ba4acabf6`）
显示root1/procs1、最后阶段 `SystemOS mount enter`，时钟2s；用户确认持续卡在此处。
没有 `DATA CHECK` 行，所以这是启动推进失败，不是新的ENOENT或成功读回。
`evidence/data-read-recovery-phone.json` 的文件结果保持null，boot_progression_passed为false。

同一aebf1da2内核已追加QEMU检查，实际SystemOS mount/owner授权达到stage6/status0。
照片两个timer PC样本按准确kernel extents均属于原版corecrypto；只是过去的定时采样，
不能作为当前停住的位置或corecrypto故障证明。静态核对中，Data gate→UFS transport锁与
root window→UFS transport锁均在completion前释放；未证明手机上具体哪条锁/等待导致阻塞。

新增顺序补丁 `patches/ram-block/publish-at-data-mount.patch` 接在原publish-restored-view补丁后：

- IOBSD阶段只准备seed对象；持久Data保持offline且不发布，APFS无法提前扫描该磁盘。
- 原 `native_ram_block_volume_seed()` 在SystemOS挂载成功后才恢复store、设置online并发布。
- 发布前仍保持完整持久视图；不回到先发布seed、后切换覆盖层的旧行为。
- 依据实际IOService接口，以30s纳秒单位有界等待UUID服务，再保留原唯一匹配/身份核对。
- stop/free清理未发布对象的指针；恢复失败和重复provider拒绝，mode0控制保持。

这是隔离Data/SystemOS发现时序的修正；001停住的实机根因仍未证实。
真实源代码段+Overlay/DirectDisk的ASan/UBSan检查通过阶段门控、首次持久读取/模拟重启、
幂等发布、重复对象/失败/关闭控制。新RamBlock仍匹配190槽ABI，完整内核构建通过：
`a8f3d1bcb6b39e0ad6afcda1d630becab3da29018746ca1dd4692a15ccfa0eaf`。
新QEMU实际到SystemOS完成检查点并核对AKS/HID；它没有模拟UFS或执行持久Data文件事务。

新候选：`artifacts/venus-data-read-recovery-002/phone/boot-venus-unixnu.img`，168960000字节，
SHA `fd22deba625e228bd1b5a57377d5a7ee77c8ecbcf864fc7e6d68c99a27086d23`。
原53B文件/token/seed/store/固件保留，phase2仍只读marker；正常Data挂载的持久元数据行为保留。
打包及镜像/ADT回读、编译收据、两层补丁和SystemOS控制绑定检查通过。
用户随后确认“已回Android，确认002一次”，一次RAM boot发送3.705s/启动0.194s OKAY，
总3.940s。设备venus/55870427匹配，授权已消耗；实际SystemOS推进及Data结果等待照片。
记录 `evidence/data-read-recovery-002-phone.json`，日志 `logs/venus-data-read-recovery-002-phone.txt`。

证据 `evidence/data-deferred-publication-host.json`、`data-deferred-publication-build.json`、
`data-read-recovery-002-candidate.json`、`data-read-recovery-002-check.json`。

```sh
python3 ports/UniXNU-venus/scripts/check-deferred-data-publication.py
bash tools/build-venus-data-publication.sh
bash tools/check-venus-deferred-systemos.sh
python3 ports/UniXNU-venus/scripts/prepare-data-read-recovery.py --deferred --out-name venus-data-read-recovery-002 --kernel-sha256 a8f3d1bcb6b39e0ad6afcda1d630becab3da29018746ca1dd4692a15ccfa0eaf
python3 ports/UniXNU-venus/scripts/check-data-read-recovery.py --out-name venus-data-read-recovery-002
```

以下为此前001模型/构建和上机记录，均保留原身份与实际失败结果。

## 实机失败与源码核对

第一轮已知文件在同次启动内写入、fsync、关闭/重开和比对通过。
第二轮在88s返回 `phase=2 step=6 rc=2 match=0 bytes=0 store=2`：打开文件得到ENOENT。
两轮原始镜像和记录保留在 `artifacts/venus-data-check-001` 与
`evidence/data-check-{write,read}-phone.json`，跨重启验收仍失败。

已核对实际路径：

- `kern_exec.c:native_owner_data_prepare()` 将选定UUID的Data设备挂载到 `/private/var`，
  并检查实际设备号、APFS类型及可写状态；成功后才进入现有测试hook。
- 两阶段内核、seed、store范围及完整token相同，未启用 `sheng-data-reset`。
- 文件测试只调用文件 `fsync`；同次启动重开可由文件系统缓存满足。
  底层store写页和位图使用WRITE(10) FUA，但这不能替代文件系统跨重启验收。
- 原RamBlock在 `start()` 中先 `registerService()` 发布seed视图，
  到 `selectVolumeSeed()` 搜索APFS卷UUID时才 `attachStore()`。
  这会在文件系统已有机会探测/缓存container或checkpoint之后改变磁盘可见内容。

此顺序缺陷已在主机缓存消费者模型中复现；尚未取得手机APFS实际选择的checkpoint，
因此不能把模型通过写成实机根因已证实或文件已恢复。

## 修正和构建接入

设备补丁 `patches/ram-block/publish-restored-view.patch`：

1. 初始化seed身份后、设置online和发布磁盘之前恢复store。
2. 请求持久存储但恢复/GPT检查失败时不发布seed-only磁盘。
3. UUID选择仅取既有设备/seed身份，不再切换存储视图。
4. 拒绝大磁盘的未实现只读恢复模式；保留明确mode0的seed-only控制。

本板 `NativeUfsRoot` 绑定 `IOPlatformExpertDevice`，提前建立已检查的root layout；
`NativeRamBlock` 绑定 `IOResources/IOBSD`。恢复所需provider未就绪时修正不会静默回退。
这项启动依赖还要通过实际手机启动检查。

`link-venus-ufs-survey.py` 检查并复制原有root support后调用
`build-venus-ram-block.py`。后者对复制的RamBlock源应用设备补丁，用实际XNU编译记录构建，
核对原始190槽ABI和共享alias，再安装新的RamBlock对象/归档。
原UFS、owner策略、Virtio及其历史artifact收据保留。`board.toml` 的完整归档顺序未改变。

## 主机结果

- ASan/UBSan执行从真实源提取的发布代码段，并使用真实PersistOverlay/DirectDisk核心：
  旧顺序得到cached checkpoint0而store为42；新顺序首次读取及下一次模拟启动均为42。
  恢复失败不发布、mode0保持、big read-only拒绝通过。消费者是模型，不是APFS。
- 新RamBlock ARM64/iOS17编译成功；190槽、24个override、11个原始导入和共享alias核对通过。
- 完整内核及预链接成功，SHA：
  `aebf1da232089c88c0a2c1534fa72e06addd74c66cf69db18914c8b7b6795460`。
- 真实QEMU到owner-root接受检查点，AKS/HID初始化检查通过。
  QEMU关闭UFS且未执行Data挂载/文件事务，不能代替持久Data实机结果。

证据：`evidence/data-publication-host.json`、`evidence/data-publication-build.json`。
保存的内核、源与归档收据：`artifacts/venus-data-publication/`。
构建日志：`logs/venus-data-publication-build2.log`；QEMU日志：`logs/venus-data-publication-qemu.log`。

## 复现与待验收

```sh
python3 ports/UniXNU-venus/scripts/check-data-publication.py
bash tools/build-venus-data-publication.sh
bash tools/check-venus-data-publication-qemu.sh
python3 ports/UniXNU-venus/scripts/record-data-publication-build.py
```

在G盘挂载对应的WSL项目根目录运行。

## 已准备的原marker只读恢复镜像

新镜像已由当前board和修正后的converter生成ADT并完成payload读回/boot roundtrip：

- `artifacts/venus-data-read-recovery-001/phone/boot-venus-unixnu.img`，168960000字节。
- SHA `6c1dff2d86b48ce5f811398db78d5929ed23eac82b9755d730cedbd3aeeca9ac`。
- 内核为上述 `aebf1da2…`；保留原001测试的完整token、marker路径与内容，phase2只读文件，
  不创建/重写/删除。Data的正常APFS挂载仍使用原来的持久元数据路径。
- seed/trust/固件不变；owned1GiB，GPU探测0，reserve1024，未启用reset或日志writer。
- 预期成功行：`DATA CHECK phase=2 step=11 rc=0 match=1 bytes=53 token=dbb03eb9 store=2`。
- `evidence/data-read-recovery-candidate.json`、`data-read-recovery-check.json`绑定实际镜像、
  ADT、原marker、原001不变的已编译测试代码、新RamBlock对象和QEMU控制。

```sh
python3 ports/UniXNU-venus/scripts/prepare-data-read-recovery.py --kernel-sha256 aebf1da232089c88c0a2c1534fa72e06addd74c66cf69db18914c8b7b6795460
python3 ports/UniXNU-venus/scripts/check-data-read-recovery.py
```

输出目录已存在时打包器拒绝覆盖。用户回来后已具体确认此镜像和正常Data挂载/只读marker
的操作范围（“已回Android，确认一次”）。一次RAM boot已完成：设备venus/55870427匹配，
Sending3.688s、Booting0.193s OKAY，总3.923s。授权已消耗，文件读回结果等待照片。
实机记录 `evidence/data-read-recovery-phone.json`；日志 `logs/venus-data-read-recovery-001-phone.txt`。
Fastboot成功不等于Data或kernel验证通过。待结果页检查原文件能否通过新的首次探测视图读回。
无论结果如何，保留原失败记录；不能用新候选的主机通过改写原001的实机失败结论。
该阶段过关后继续CPU显示实机验收；若原文件仍缺失则继续文件系统同步/恢复核对。
