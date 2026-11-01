# 再次对照官方 UFS 文档：当前完成条件与证据缺口

2026-10-28，用户要求多读 `https://unixnu.com/zh/porting/ufs`。
重新阅读UFS步骤、ShengUfs/RamBlock组件页、sheng storage记录及bring-up阶段。

**后续验收更新：**新Data002已经完成实际Data/父目录/文件身份核对、全部同步返回0、
持久write计数增长及规定重启后的53B读回，见 `DATA-SYNC-QUALIFICATION.md` 与
`evidence/data-persistence-qualified.json`。以下保留复核时发现的缺口及原marker失败事实；
本轮受控文件门槛现已通过，长期与故障恢复仍是单独范围。

## 文档约束与本板对应实现

1. **先核目标资源和所有权。** 文档示例为SM8550/sheng，并不能直接作为SM8350参数。
   Venus已核对host `0x01d84000/0x3000`、Lahaina PHY `0x01d87000/0xe10`、GCC资源、
   GIC SPI265和SMMU stream `0xe0`。来源为live FDT和固定版本vendor代码。
   既有实机寄存器/DMA/GPT结果的范围保留；不把节点声明当运行证明。
2. **固件接管或冷初始化各有明确前提。** 本板使用已验证的固件状态接管、独占轮询队列；
   不要求无依据地重写PHY冷初始化。DMA地址宽度、context-bank和cache维护仍按实际路径核对。
3. **组件、archive和OS ABI一起核对。** 本板采用固定SM8350 UFS源
   `af785c1777161a62931425c2faaa536ce0bebd5b`加设备补丁；
   `link-venus-ufs-survey.py`接入已检查的UFS/root support和当前RamBlock构建。
   原始IOStorageFamily的190槽ABI与XNU10063输入已核。不能只打开 `native-ufs-root=1` 当作完成。
4. **读取、根卷、Data写入、重启恢复分别验收。** 文档要求实际已分配Data中的写入在规定
   重启/复位后保留；根卷可读、store头有效、SCSI状态0或模型通过都不能替代此条件。
5. **每项结果按source/host/device等级记录。** `porting.toml`和13区域checker要求来源版本；
   文档中的sheng storage主要是实现描述，不是Venus设备证据。

## 当前实际Data链路

```text
APFS文件/目录与事务
  → 原IOStorage接口（512B逻辑请求）
  → NativeRamBlock的8GiB Data设备 / DirectDisk
  → PersistOverlay的4KiB页和presence bitmap
  → native_ufs_store_read/write/sync
  → hostRead4k / hostWrite4k(FUA=true) / hostSyncCache
  → UPIU、UTRD/PRDT、cache维护、有界doorbell/OCS/SCSI完成
  → UFS LUN0内的已分配Data store
```

不是把8GiB文件当作完全常驻RAM的易失盘：big seed只保存原始非零页；mode2改变页直接
放在UFS store中。store按64GiB `unixnu` 分区和固定1024MiB保留区计算，
绝对4KiB LBA `[59299519,61396736)`，逻辑2097152页、头1块、位图64块。
root image结束LBA47190528，Data与root/4MiB guard/尾保留区不重叠。
当前两次恢复仍使用原seed身份和布局；不改reserve或重新部署来掩盖恢复失败。

## 按官方完成条件逐项看当前结果

| 文档阶段 | 已有证据 | 尚不能推出的结论 |
| --- | --- | --- |
| 控制器/时钟/链路 | 有寄存器检查和固件接管实机结果 | 冷启动、所有电源状态均已完成 |
| DMA与命令 | 已知读取实机，源/模型覆盖错误与隔离 | 成功的真实Data写入必然已持久 |
| 块读取 | LUN0/4096B容量、GPT CRC/SHA及root验证读取 | 写命令、cache flush和掉电恢复也通过 |
| 根卷 | 已有owner-root与launchd/userland实机记录 | 可用UI或Data跨重启完成 |
| Data写入 | 原write轮53B fsync/同次启动重开比对通过 | 文件内容及目录项已进入可恢复checkpoint |
| Data恢复 | 原read与恢复002均store2，但打开marker得到ENOENT | 持久化完成；或已确定是父目录/fsync/硬件FUA问题 |

002恢复镜像已在手机越过SystemOS阻塞并挂载Data，39s仍为
`phase=2 step=6 rc=2 match=0 bytes=0 token=dbb03eb9 store=2`。
这明确否定“仅修发布顺序便完成原marker恢复”的预期。

## 补齐成功写命令的主机验证

既有`ufs_root_commands.cpp`重点覆盖读取、写范围拒绝和等待锁期间被隔离的情况；
未完整验证成功Data FUA写入、flush和重开。新增
`scripts/check-ufs-data-command-contract.py`从**实际已编译UFS源**提取三个store callback，
使用同一`RootCommands.h`、真实PersistOverlay及模型DMA/介质运行：

- 成功WRITE(10)的FUA位、UPIU方向、UTRD方向与数据长度。
- 原非FUA缓存写与实际SYNCHRONIZE CACHE(10)命令分别核对。
- 头/bitmap/页经真实callback写入，模型重置传输后Overlay重开与字节比对。
- store窗口越界、SCSI失败、超时及后续命令隔离。
- ASan/UBSan通过；实际compiled NativeUfs SHA仍为`22f25334…`。

证据 `evidence/ufs-data-command-contract.json`；脚本只操作主机模型。
此检查验证请求编码/完成处理和覆盖层合同，**不能证明真实UFS执行了持久写入**，也未模拟APFS。

## 下一项应补的实机证据

当前缺少能区分故障层级的以下观测：

1. 校验文件及其父目录的实际设备身份，是否与已挂载Data设备一致。
2. 文件事务前后 `native_data_persist_writes/syncs/errors/present` 的变化，
   证明操作确实进入已分配Data的持久块路径；屏幕root读取失败计数0不能替代这些写计数。
3. 实际写命令与flush的完成状态，以及写后、重启后同一store元数据/选定页的对照。
4. APFS恢复选择的checkpoint/目录项与文件数据的一致性。

已读当前XNU实现：普通fsync调用`VNOP_FSYNC(vp,MNT_WAIT)`；F_FULLFSYNC走
`VNOP_IOCTL`并定义为file/journal/drive flush。原RamBlock的`doSynchronizeCache()`目前
因store使用FUA而直接返回成功，只有store callback才实际发SYNCHRONIZE CACHE。
这些语义值得核对，但现有照片尚不足以指定哪一层失效。

先补可区分层级的验证，再决定是否改文件/目录同步、驱动同步或APFS接入。
当前手机上机授权均已消费；后续设备操作要绑定新的准确范围和镜像。
