# 按官方顺序恢复前置适配主线

2026-10-28：用户要求先补前置适配，再做专门日志工程。当前主线按
[官方驱动适配](https://unixnu.com/zh/porting/drivers)、
[平台](https://unixnu.com/zh/porting/platform)和
[UFS](https://unixnu.com/zh/porting/ufs)的完成条件推进。
已保存的崩溃分析仍是参考资料；反复生成单点崩溃诊断镜像暂后置。

## 阶段与验收

| 顺序 | 当前基础 | 下一项实际验收 |
| --- | --- | --- |
| 1 平台/内存 | 当前启用单核，GIC/PSCI/19.2MHz定时器参数来自实机DT；21个保留区已比对；1GiB owned窗口有既往实机证据 | 重新生成的ADT必须保留正确中断provider和地址转换；更多CPU须逐核入口/IPI验证后启用 |
| 2 UFS/根卷/Data | 已知读取、GPT、根卷/用户态有实机证据；新Data002的53B文件写入、完整同步、规定重启后读回已通过 | 本轮受控持久化门槛通过；保留准确输入和结果，长期/故障恢复另行验收 |
| 3 CPU显示 | GOP与显示服务可用，CPU呈现路径已接入；目前无OS交换/画面 | 正确模式与几何、已知CPU画面、交换及完成通知；之后才继续GPU呈现 |
| 4 真实输入 | 离线HID服务已启动；原厂DT已找到ST SPI触控节点 | 按目标控制器/固件实现芯片识别、帧读取、坐标/触点/HID事件和实体按键 |
| 后续 | 已有A660有界启动/提交结果可保留 | 在前置阶段过关后继续Metal/GPU呈现及其他外设；专门日志工程后置 |

**最新进展：用户返回后完成新Data002写入/重启/读回两轮，实机通过。**
详情 `DATA-SYNC-QUALIFICATION.md`；原失败过程仍见 `DATA-PUBLICATION.md`。
当前下一阶段是CPU显示的正确模式、已知画面和交换完成，再做真实输入。
显示/输入的离线前置检查见 `DISPLAY-INPUT-FOUNDATION.md`。

这里验收当前实际启用的路径。官方允许UFS接管已经由固件初始化的控制器；冷初始化不是
每块板都必须重做的前置条件。额外CPU、传感器和电源状态也不能仅通过打开参数就标成完成。

## 本轮确定的修正

### 配置基线统一

- `board.toml` 默认改为实机使用的 `venus_ufs_root_defconfig`。
- owned memory改为已测的 `0x40000000`（1GiB），不再默认为早期288MiB。
- AKS和离线HID的已验证初始化参数加入板级完整参数数组，避免只存在于临时打包脚本。
- 显式固定 `sheng-log-reserve=1024`，与已使用的Data store位置一致；它不启用日志写入器。
- 板级基线使用 `sheng-gpu-power=0`、`sheng-fb-gpu=0`，优先CPU显示验证。

### ADT生成链修正

实际构建基线 `8d157ee...` 的 `scripts/unixnu/devicetree.py` 原来仍缺少两项已有修正：

1. `AAPL,phandle`及其与FDT句柄的对应、有效性检查。
2. 非零`arm-io`窗口，以及窗口基址加子节点偏移的地址转换。

过去实机镜像沿用另一条生成链的旧ADT，因此根卷能启动不等于当前默认生成器正确。
本轮已将此前验证过的转换实现应用到实际基线。可复现补丁保存在
`patches/tools/adt-handoff.patch`；它是**主机构建工具补丁**，不属于XNU patch series。
在新的干净基线检出中先检查并应用该补丁；现用基线已应用，检查器以反向`--check`验证。

```sh
git -C /root/unixnu-build/UniXNU-sheng-base apply --check /mnt/g/UniXNU-Port/ports/UniXNU-venus/patches/tools/adt-handoff.patch
git -C /root/unixnu-build/UniXNU-sheng-base apply /mnt/g/UniXNU-Port/ports/UniXNU-venus/patches/tools/adt-handoff.patch
```

此外，sRGB从被忽略的`[adt]`移动到`[adt.product.string]`，补齐选定OS的`J120AP`产品身份、
thin-bezel和hold/音量键描述。按键描述不等于物理按键驱动。
使用实际转换器生成的ADT已验证这些属性，以及和旧实测控制一致的GIC/timer/ranges、
root UUID、Data/trust占位符、平台身份和owned窗口。新ADT已用于Data两轮实机，成功进入测试hook；
因为两轮均在launchd前等待，不能宣称修复了显示故障。

## Data阶段的实际进展

当前Data seed是8GiB逻辑磁盘（编码文件SHA `ca732abd...`），其store位于unixnu分区内，
绝对4KiB LBA `[59299519,61396736)`，保留区下方。先在主机运行现有持久覆盖核心测试，
再在已启动的Android中核对设备身份和64GiB分区大小，以root只读取得头部和位图：

- 相对unixnu：`skip=14417855`，`count=65`，共266240字节。
- `SHNGDATA`头、版本、页数、seed身份、CRC、位图边界均匹配。
- generation为1，位图记录 **47130个已存在的持久页**。
- 此读取没有重启手机或写入磁盘，也没有读取用户文件内容页。

这证明现有store元数据可读且一致；仍不能替代受控的“写入已知内容→重启→读回”测试。
该测试应通过XNU的Data文件系统创建独立校验文件、同步并保存预期SHA，再经获准重启读回，
不直接改写原始store块来模拟文件系统成功。对应镜像、校验文件和操作需要在执行前明确。

原文件测试记录见 `DATA-QUALIFICATION.md`，其read轮ENOENT及后续恢复失败保留。
新Data002增加Data/父目录/文件身份、目录/完整/介质同步和写计数观测后，
write49s与独立重启后read63s均step11/rc0/match1/bytes53。此受控持久化门槛已通过，
见 `DATA-SYNC-QUALIFICATION.md` 和 `evidence/data-persistence-qualified.json`。
测试仍停在launchd前；下个CPU显示镜像要去掉逐轮Data测试参数后才会继续用户态。

证据：`evidence/stage-foundation.json`、`evidence/data-metadata-read.json`。
原始板级配置快照与生成ADT：`artifacts/venus-stage-foundation/`。
实际Data读取原始数据和命令：`artifacts/venus-data-foundation/read-*/`。

## 输入资料核对

原厂DT声明 `/soc/spi@a8c000/fts@0`，compatible为 **`st,spi`**，IRQ GPIO23、reset GPIO22。
另有SSC/SLPI节点。它们是目标资料，不是已工作的XNU驱动；不能沿用sheng的Novatek矩阵和固件
就声称Mi 11触控完成。具体芯片/固件仍须对应原厂实现和硬件识别。
清单在 `artifacts/venus-stage-foundation/declared-peripherals.json`。

## 主机检查

```sh
python3 /mnt/g/UniXNU-Port/ports/UniXNU-venus/scripts/check-stage-foundation.py
python3 /mnt/g/UniXNU-Port/sources/UniXNU-guide/scripts/porting-record.py check --device /mnt/g/UniXNU-Port/ports/UniXNU-venus
```

`check-data-foundation.py`默认仅生成读取范围计划；显式`--read-android`才用Windows端ADB读取元数据。
已有特殊实验的`prepare-venus-a660-phone.py`仍用于重现其固定输入，不能把它复制旧ADT的输出
当成本轮板级配置已经应用。后续阶段镜像应使用实际板级配置与修正后的生成器，并再次核对payload。
