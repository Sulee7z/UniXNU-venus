# Data 002：受控文件跨重启验收通过

2026-10-28。原001 marker及两张read-recovery镜像的历史结果保留。
新文件的实际Data归属、写入提交和规定重启后53B读回均已实机通过。
验收范围为此次已知文件事务，接下来按顺序进入CPU显示模式/画面/交换验证。

## 实现

- 继续使用恢复002已越过SystemOS阻塞的post-SystemOS Data发布路径，保持既有seed/store/固件。
- 原Data mount hook先验证APFS实际backing device、可写状态并到stage4。
- 测试打开 `/private/var` 和 `/private/var/db`，核对目录类型、root所有权及同一文件系统`st_dev`。
  block设备号`mount`单独显示；不错误地要求`st_dev`等于block rdev。
- 持有parent fd，使用 `openat(O_CREAT|O_EXCL|O_NOFOLLOW)`创建新文件，
  验证regular/root-owned/0600/同Data文件系统；不覆盖既有文件。
- 写53B，依次file fsync → parent-directory fsync → file F_FULLFSYNC → native UFS store sync。
  最后一步发真实SYNCHRONIZE CACHE(10)，独立于RamBlock的FUA write-through声明。
  任一步失败均返回失败，不降级成较弱同步或继续报成功。
- 关闭并重开验证全部53B；write轮还要求持久write计数增长、error计数0。
- 第二次启动仅打开/读取/比对该新文件，并再次核对设备身份；不调用上述写入/同步流程。
- 两阶段默认关闭；启用后停在launchd前，内核监视继续。

新增观测行：

```text
DATA DEV mount=... data=... parent=... file=... stage=4 rc=0 ro=0
DATA IO w=before>after fs=after_file_fsync full=after_fullsync runs=before>after err=0
DATA SYNC file=0 dir=0 full=0 ufs=0 present=before>after v=2
DATA CHECK phase=1/2 step=11 rc=0 match=1 bytes=53 token=9d78d0cf store=2
```

前三行固定24–26，结果行38；photo recorder要求完整四行。`runs`是覆盖层完成的写run计数，
不是硬件flush次数；计数是测试区间观测，不能排除文件系统背景元数据活动。
read轮同步结果为-1代表未调用。旧step1–11保留，新step12父目录检查、13目录sync、
14完整sync、15UFS sync、16没有观测到持久写入。

## 新文件与镜像

- 新文件 `/private/var/db/venus-data-check-9d78d0cf5344b52f703930a3241e7e05.bin`。
- 53B SHA `c1795e4164ed347c650fa8dc99ead15bbedef48543d68327f9b162c8b40ef74a`。
- 内核 SHA `4b1ae1c0bc6ea2b7dbb440099ef5c0a0c413d26aab8bfe304f1fbc8b1a2760be`。
- write：`artifacts/venus-data-check-002/write/boot-venus-unixnu.img`，
  SHA `53478a3ffd8799e958327b6a023be576bcaed38f72487fe2db23b353f2707409`。
- read：`artifacts/venus-data-check-002/read/boot-venus-unixnu.img`，
  SHA `eb1da7ff22e6f89a9afd6f98c8a1fb64b20667e71b715bad72a11c82318218e5`。
- 两张均168960000B、1GiB owned、GPU0、保留原8GiB Data seed和绝对store
  `[59299519,61396736)`及1024MiB尾保留区。

## 已完成检查

- 真实C事务核心ASan/UBSan：分别建模文件、目录项、checkpoint提交及介质fence；
  验证所有同步失败阶段、phase2无写、错设备/短I/O/独占创建/旧file-only同启动能读但重启丢失的模型。
- 真实像素writer验证详情行、结果行、pulse与scanout让出；不模拟物理APFS。
- 真实XNU adapter编译和全内核预链接成功。构建中将原误用的用户态名称`fcntl`
  纠正为本版XNU实际系统调用`sys_fcntl`。
- QEMU到真正SystemOS mount完成/owner授权stage6、AKS/HID通过；未执行Data文件事务。
- 新文件/共同kernel/ADT、payload逐项回读、boot roundtrip、已编译源/当前RamBlock双补丁收据通过。

证据：`evidence/data-sync-contract-host.json`、`evidence/data-sync-candidate.json`。
原始产物/收据：`artifacts/venus-data-check-002/linked-inputs/`。

## 上机顺序

先准确授权write镜像及一个新53B文件的创建/同步范围，拍完整四行。
只有write通过后才确认规定重启，并准确授权read镜像；两轮成功才能通过本次受控持久化验收。
这仍不代替全部UFS耐久/故障恢复测试。

用户已具体确认“已回Android，确认write一次”，包含上述新文件创建和完整同步范围。
设备venus/55870427核对后一次RAM boot：Sending3.691s、Booting0.193s OKAY，总3.924s。
记录 `evidence/data-check-002-write-phone.json`；授权 `G:/UniXNU-Port/evidence/data-write-002-authorization.json`；
日志 `logs/venus-data-write-002-phone.txt`。write一次授权已消耗，实际结果见下。
Fastboot返回OKAY不能代替实际文件事务结果。

### write轮实机通过

照片 `G:/20261028_190037.JPG`，SHA
`c75ca31b1cbcda7edf0248c00cedf1c590e939b2c586df2e9917fefef9a44e36`，49s：

```text
DATA DEV mount=1000009 data=1000009 parent=1000009 file=1000009 stage=4 rc=0 ro=0
DATA IO w=0>32 fs=1 full=32 runs=0>23 err=0
DATA SYNC file=0 dir=0 full=0 ufs=0 present=47130>47136 v=2
DATA CHECK phase=1 step=11 rc=0 match=1 bytes=53 token=9d78d0cf store=2
```

确认同卷身份、全部同步返回成功、实际持久写入计数增长且无错误，重开逐字节匹配。
普通文件fsync后的写页计数1、完整sync后的32是本轮关键观测；它仍不足以独立确定旧文件
缺失的全部原因。此write结果与下面独立重启后的read结果共同构成本轮验收。

用户随后确认“已重启回Android，确认read一次”。核对设备后一次RAM启动read eb1da7ff：
Sending3.682s、Booting0.193s OKAY，总3.914s。
`evidence/data-check-002-read-phone.json`记录手动重启确认及下面的四行实机结果。
read没有调用四项写轮同步，`DATA SYNC`返回字段为-1是预期；正常Data挂载仍有原文件系统行为。

### read轮实机通过

照片 `G:/20261028_190612.JPG`，SHA
`2d51833c644dadbec35aaea407940a3634831ea5fca1c17931b30bac41c9c1f8`，63s：

```text
DATA DEV mount=1000009 data=1000009 parent=1000009 file=1000009 stage=4 rc=0 ro=0
DATA IO w=1>1 fs=0 full=0 runs=1>1 err=0
DATA SYNC file=-1 dir=-1 full=-1 ufs=-1 present=47136>47136 v=2
DATA CHECK phase=2 step=11 rc=0 match=1 bytes=53 token=9d78d0cf store=2
```

同一Data文件系统恢复成功，原新文件53B完整匹配；测试区间write/run计数不变，
未调用写轮同步。write轮的presence47136在重启后保留。
`check-data-persistence-result.py`检查两张实际镜像/照片、文件身份、完整四行和重启授权记录，
汇总至 `evidence/data-persistence-qualified.json`。两次一次性授权均已消费。
