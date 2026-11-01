# 020报告：供电和loopback都通过，MISO输入位仍为0（022）

只读采集 `read-20261030T022507Z` 的 `forensics-v3` 已同时提取 019 和 020；
之前只显示到 019 是 `recheck-data-forensics.py` 的硬编码路径列表漏了 020，不是
Data 没写入。

## 020实机

```json
{"build":"touch-020","stage":5,"status":-19,"chip_id":0,
 "messages":8,"id_attempts":8,"loop_status":0,"loop_match":1,
 "pin_io":[0,0,0,1],"power_status":0,"power_base":271616,
 "tp_enable":154,"hid_ready":1}
```

- `power_base=271616=0x42500`，`power_status=0`：RPMh LDO2 写入成功。
- `loop_match=1`：GENI/时钟/打包/内部回环正常。
- 但 `pin_io` 仍为 `[0,0,0,1]`：GPIO48/49/50 的 IO 输入位为 0，只有 GPIO51 为 1。
  这比继续改电源或 GENI 更直接：MISO 输入路径没有按预期使能。

## 022修改

按 `redwood_goodix.c` 的 `gpio_configure/use_engine_pins` 顺序修正：先写 TLMM
CFG（mux/pull/drive），再写 IO 输入位；020 是反过来的，CFG 写入把 48–50 的输入位
清掉了。022 保留 021 的 `power_on` 顺序、cmd-db LDO2、GENI loopback 和 0x3639。

`G:/UniXNU-Port/artifacts/venus-touch-022/phone/boot-venus-unixnu.img`
168960000B，SHA256
`d914b12979331546526f98b6317fd62e62809651529fb3b81a60d46f74029734`，
kernel `8d8f01854ac91811759f674fe71697c809dbe53d901c16740b3e7db15e55bd79`。

022 已实机启动一次；只读采集 `read-20261030T023657Z` 的报告为：

```json
{"build":"touch-022","stage":7,"status":0,"chip_id":14646,"fw":132,
 "messages":6,"id_attempts":1,"opcode":135,"transfer":0,"cs":0,
 "loop_status":0,"loop_match":1,"pin_io":[1,0,0,1],
 "power_status":0,"power_base":271872,"tp_enable":154,
 "irq_polls":72,"irq_low":1,"frames":1,"errors":0,
 "hid_phase":6,"hid_match":0,"hid_meta":0,"hid_start":0,
 "hid_ready":1,"hid_report":-1,"hid_reports":0}
```

`chip_id=14646=0x3936`、`fw=0x84`、`loop_match=1`、`stage=7/status=0`、
`frames=1`、`pin_io` 的 MISO 位已变成 1。**触摸控制器已经应答，GPIO/MISO 修复
生效**；剩余失败是 `hid_reports=0`，不是电源、GENI loopback 或 MISO 输入。

`power_base=271872=0x42600`（cmd-db 找到的 Venus ldoc2 地址），不是文档里的
star `0x42500`，但 RPMh 写入返回 0。

## 下一步

不要整套替换 star 驱动。先做 HID/FIFO 诊断：把 `hid_ticks`、首帧事件字节和
`vst_process_events` 的计数写进下一次 startup report，区分“没有触摸帧”与
“有帧但 HID 未发送”。
