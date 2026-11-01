# 重读 star 文档：只抄 power_on/RPMh，不抄 redwood 的 FTS/Goodix（021）

重新读完 `HackiOS-Xiaomi11Ultra/docs/STAR.zh-CN.md` 和
`xnu/files/bsd/dev/redwood_goodix.c` 后，结论是：

- `redwood_goodix.c` 开头写明它是 **POCO X5 Pro（redwood）** 的 Goodix GT9916 /
  FocalTech FT3680 驱动，不是 star 的 STM FTS K2 驱动。它的 `goodix_*`、
  `focaltech_*`、FTS 5.x framing 和 firmware 下载协议不能整套抄给我们的 ST。
- 文档第 89 行真正点名可复用的是 `geni_*` 全套；但它的 `SE_PHYS=0xa94000`、
  `GCC_QUP1_SE5_*`、`PIN_AVDD=12` 都是 redwood 地址，必须换成 Venus 的
  `SE11@0xa8c000`、SE11 GCC、GPIO132/154；不能原样 copy。
- 可直接抄且我们 020 没做对的是 **`power_on()` 顺序**：
  `RESET low -> INT input -> RPMh ldoc2 1.8V -> 3ms -> AVDD/TP enable -> 15ms`。
  020 先开 GPIO132/154 再写 LDO2，顺序与参考实现相反。
- `rpmh_address("ldoc2")` 通过 cmd-db 解析 SM8350 布局；020 硬编码 `0x42500`。
  021 改为 cmd-db 查找（失败时才回退 `0x42500`），并保留 `{1800,1,7}`。

## 021修改

- 先拉低 GPIO22，GPIO23 设为输入上拉；cmd-db 找 ldoc2，写 VDD 1.8V。
- 3ms 后再拉高 GPIO132/GPIO154；15ms 后才开时钟和 SPI pin。
- MCU reset 改为参考实现的高/低 2ms/100ms 节奏，之后等待 100ms。
- GENI 仍是已编译的 `QcomGeniSpi` PIO 实现；额外清零 `SPI_DELAY_COUNTERS`
  和 `TX_WATERMARK`，保留 019 的内部 loopback。
- 接受 `0x3639`；不写触摸固件/NVM、不校准、不重置 Data。

## 候选

`G:/UniXNU-Port/artifacts/venus-touch-021/phone/boot-venus-unixnu.img`
168960000B，SHA256
`d291fc19926640a29c5e522de917814b8843ef9cd1a5c4c0b46b125ac5e0b44e`，
kernel `94f1506b3aa33a7de2b0b70af447f780ef60e66c41298375e28ca31a67da11c0`。

021 未实机启动；因 `OS.raw`/`SystemOS.raw` 缺失，仍没有 QEMU SystemOS 通过声明。
