# Data 文件跨重启验证（write轮通过，read轮失败）

## 目的和范围

按官方存储阶段要求，经XNU的已挂载Data文件系统写入已知内容、同步，并在规定重启后重新
读回。已有Android只读检查证明Data存储头/位图有效，但不代替这个完整文件操作。

本次使用修正后的板级配置和实际ADT生成器，1GiB owned、CPU显示基线、GPU探测关闭。
Data seed、存储位置、root/trust输入和固件保持原测试身份；不重建部署。

## 校验对象

文件路径：

```text
/private/var/db/venus-data-check-dbb03eb98bbf038f530a9621710ec0b7.bin
```

53字节内容的SHA-256：
`c984c893af1973c9ba2a5bac0e5173cdf2b6b8c26ca4c378023163a7e960058e`

实际路径与内容由内核共享的C核心生成后保存到
`artifacts/venus-data-check-001/plan.json`和`expected-marker.bin`。

## 两个阶段

1. **write**：在Data挂载成功后、launchd启动前，用`O_CREAT|O_EXCL|O_NOFOLLOW`创建文件。
   核对root所有权、普通文件及0600权限，写53字节、`fsync`、关闭、重新只读打开、检查长度并逐字节比对。
   文件已存在时拒绝覆盖。完成或失败后停留在结果页，不自动重试、重启或继续launchd。
2. **read**：经用户手动重启后，以相同seed和token启动第二张镜像。要求存储状态为resumed，
   只读打开既有文件，核对所有权/权限/长度和全部内容，随后停留结果页。此阶段不创建、重写或删除校验文件。

开始前同时核对现有8GiB Data页数、绝对store起点59299519、mode2、GPT检查和存储错误状态。
范围不符时在文件操作前拒绝。文件系统自身的挂载/元数据行为仍属于正常Data存储操作。

固定第38行显示：

```text
DATA CHECK phase=1 step=11 rc=0 match=1 bytes=53 token=dbb03eb9 store=2
```

第一轮也可从fresh状态3开始；第二轮必须是resumed状态2。
`step=11 rc=0 match=1 bytes=53`表示该轮文件操作通过。只有两轮均通过，且中间明确重启，
才完成本次跨重启验证。`rc!=0`或停在其他step都不能记作通过。

## 镜像

共同kernel SHA-256：`f168dff086f800a8b77fb2da5965be989ea4321721b1b2f4a347d362c4ee1501`

| 阶段 | 镜像路径（相对G:/UniXNU-Port） | SHA-256 |
| --- | --- | --- |
| write | `artifacts/venus-data-check-001/write/boot-venus-unixnu.img` | `eddb17c4c37129650811fb5d11107ec92a6ba7309a381c61464a3739ac49337d` |
| read | `artifacts/venus-data-check-001/read/boot-venus-unixnu.img` | `da4d54ff47e7ff38aabbeb41e221689614490169a429d49270f04110757eb626` |

两个镜像均168960000字节。每次上机须绑定具体镜像和操作授权；read阶段等待write结果和手动恢复确认。

## 主机验证

- 实际C核心通过ASan/UBSan：独占创建、同步后重新打开、模拟掉电/重启读回、phase2不写入、
  token/内容/长度/权限错误、短读写、失败清理和存储范围门控。
- 固定结果行通过实际像素写入器检查，保留pulse/yield/边界规则。
- 当前内核成功构建；QEMU到owner-root检查点、AKS/HID初始化成功。这个QEMU控制尚未执行Data文件测试。
- 两阶段payload逐项读回、镜像roundtrip、共同ADT和marker身份通过。
- 证据：`evidence/data-check-candidate.json`；验证器：`scripts/check-data-check-candidate.py`。

write轮已执行一次具体授权RAM boot，Sending3.702s、Booting0.193s OKAY，总3.937s。
照片 `G:/20261028_135005.JPG` 在263s显示：

```text
DATA CHECK phase=1 step=11 rc=0 match=1 bytes=53 token=dbb03eb9 store=2
```

因此独占创建、写入、同步、关闭后重新打开并逐字节比对通过。诊断时钟继续运行是预期行为：
`IOSleep`只让测试流程在launchd之前等待，不冻结内核，结果行保持稳定。照片也显示`procs=1`。
记录和照片哈希保存在 `evidence/data-check-write-phone.json`。
用户随后确认已手动回Android并授权read轮。已核对设备并一次RAM启动read镜像，
Sending3.706s、Booting0.193s OKAY，总3.940s。照片 `G:/20261028_141312.JPG`
（SHA `a0bf38dd60307cdd307d7370b9fb5ceab86c757c191a43643b33d247a8bdb3de`）在88s显示：

```text
DATA CHECK phase=2 step=6 rc=2 match=0 bytes=0 token=dbb03eb9 store=2
```

`VdcOpenRead`返回`ENOENT`，即同一路径未找到文件。store2仅证明覆盖层恢复状态，
并不证明APFS选择了最新的持久视图。跨重启测试失败，记录在
`evidence/data-check-read-phone.json`。用户要求其回来前仅做主机检查；两次启动授权均已消耗。
