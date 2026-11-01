# HackiOS star 参考：补 LDO2/GPIO154/0x3639（020）

`HackiOS-Xiaomi11Ultra` 已 clone 到 `sources/HackiOS-Xiaomi11Ultra`（HEAD
`e97863f8722ca3a8b7c12f24c899fa90c048b509`），但仓库没有可启动镜像：
`prebuilt/` 被排除，GitHub releases/tags 为空，只有 redwood（SM7325）的 UEFI/DTB，
没有 star 或 venus boot image，也没有 star 构建 profile。不能直接拿 redwood 镜像启动
venus；star 与 venus 的 DT/面板/供电/分区也不同。

它的 `docs/STAR.zh-CN.md` 给出与 Venus 触摸直接相关的硬件事实：

- STM FTS K2，chip ID `0x3639`；
- VDD 1.8V 来自 PM8350C LDO2，RPMh 地址 `0x42500`，写 `{1800,1,7}`；
- AVDD 3.3V 由 GPIO132 控制，GPIO154 为 TP power enable；
- star 同样在 MISO 恒高时 probe 失败，作者也怀疑 bit-bang/GENI 物理层。

## 020修改

- 保留 019 的 GENI 内部 loopback、SPI pin 输入使能和 300ms MCU reset。
- 增加 GPIO154 高电平，与 GPIO132 一起在复位前上电。
- 增加 RPMh DRV2（`0x18220000`）写 LDO2：`0x42500/1800, +4/1, +8/7`，
  报告 `power_status/power_base/tp_enable`；RSC 映射失败或写超时只记录，不阻塞后续 ID。
- 识别接受 K2 chip ID `0x3639`，同时保留 `0x4036/0x3936`。
- 仍不写触摸固件/NVM、不校准、不重置 Data。

## 候选

`G:/UniXNU-Port/artifacts/venus-touch-020/phone/boot-venus-unixnu.img`
168960000B，SHA256
`badd052e29544601a9a28b1097477627d035c699753d1e3f646b82c20d1c91ff`，
kernel `04a790f2be68be792190cfb65a6d19d56007b626301467aec9930b732de8b659`。

因宿主 `OS.raw`/`SystemOS.raw` 缺失，020 没有 QEMU SystemOS 通过声明；只完成
真实源码编译、link/prelink、`--check`、FAT/ADT/trust/FD/EFI/roundtrip。020 尚未
实机启动。

## 判定

一次 020 启动后看 `/private/var/db/venus-st-020/startup.jsonl`：

- `power_status=0` 且 `power_base=0x42500`：RPMh LDO2 写入完成；
- `loop_match=1`：GENI/时钟/打包路径正常；
- `chip_id=0x3639`：供电+ID 修复生效，进入 scan；
- 仍 `chip_id=0` 且 `power_status=0`：问题更可能在 MISO/物理层或芯片 boot，而不是 HID。
