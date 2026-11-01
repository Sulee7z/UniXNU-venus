# 018仍ID0：加入GENI loopback与输入使能（019）

018只读快照`read-20261030T014937Z`：172832页/91段，含两次metadata共708452352B，
checkpoint1204，metadata稳定/SHA/覆盖通过。`/private/var/db/venus-st-018/startup.jsonl`
392B：`stage5/status-19/chip_id0/messages8/id_attempts8/transfer0/cs0/cs_manual0/
fifo_disabled0/hid_ready1`。控制器管理CS、300ms复位和8次重试后仍读回ID0。
HID匹配/启动仍成功；问题不在HID或UIKit。

## 019诊断

- 增加`GENI_SPI_LOOP`内部MOSI→MISO回环，8字节pattern；报告`loop_status/loop_match`。
  回环通过说明GENI时钟/打包/传输路径正常，失败则先修控制器而不是继续碰芯片。
- SPI pin mux同时设置TLMM IO输入位（pinctrl-msm在mux时启用输入）；报告四个pin的IO值。
  这不是降低检查，而是补上Venus reset态可能缺少的MISO输入路径。
- 保留018的控制器CS、300ms复位、8次ID重试和SALIXP0x4036/FTB0x3936。
- 仍不写触摸固件/NVM、不校准、不重置Data。

## 候选

`G:/UniXNU-Port/artifacts/venus-touch-019/phone/boot-venus-unixnu.img`，168960000B，
SHA256`c7f4e46af15fe8dbc72fd3ea4110c3c564b5a8ba9d2b05645c7f7c279f1873a2`，
kernel`138ec757a3bdc6ac4bed92b4be0ff4cf8f1a73f513502714d1a59d72ef3f8a1d`。
018 QEMU仍因宿主OS.raw/SystemOS.raw缺失不能重跑；019只做了FAT/ADT/trust/FD/EFI/
boot roundtrip/`--check`，没有QEMU通过声明。

若019报告`loop_match=1`仍`chip_id=0`，下一步是PM8350C L2/L3的vdd/avdd供电
（Android`fts_enable_reg`明确启用）；若`loop_match=0`，修GENI/引脚路径。
